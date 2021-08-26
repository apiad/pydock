#!/usr/bin/python3

import sys
import os
import shutil
import inspect
import getpass
from configparser import ConfigParser
import subprocess
from pathlib import Path
from typing import Callable


__version__ = "0.0.1"


args = sys.argv[1:]

pydock_path = Path.cwd() / ".pydock"

if not pydock_path.exists():
    pydock_path = Path.home() / ".pydock"

if args and args[0] == "--local":
    pydock_path = Path.cwd() / ".pydock"
    args.pop(0)
elif args and args[0] == "--global":
    pydock_path = Path.home() / ".pydock"
    args.pop(0)

pydock_path = pydock_path.resolve()

envs_path = pydock_path / "envs"
config_file = pydock_path / "pydock.conf"


def init():
    pydock_path.mkdir(exist_ok=True)
    envs_path.mkdir(exist_ok=True)
    config = ConfigParser()
    config.add_section('docker')
    config.set("docker", "repository", "")
    config.set("docker", "sudo", "False")
    config.add_section('environment')
    config.set("environment", "username", getpass.getuser())

    config.read(config_file)

    with config_file.open("w") as fp:
        config.write(fp)

    return config


COMMANDS = {}


class Command:
    def __init__(self, func: Callable) -> None:
        self.func = func
        self.name = func.__name__
        self.doc = func.__doc__.strip()
        self.doc_short = self.doc.split("\n")[0]
        self.signature = inspect.signature(self.func)
        self.args = list(self.signature.parameters.keys())[1:]
        self.args_help = " ".join(f"<{arg}>" for arg in self.args)

    def __call__(self, config, *args):
        if len(args) != len(self.args):
            print(f"Usage: pydock {self.name} {self.args_help}")
            print("")
            print(self.doc)
            return

        return self.func(config, *args)

    def __str__(self):
        return f"{self.name:16}{self.doc_short.strip()}"


def command(func):
    COMMANDS[func.__name__] = Command(func)
    return func


@command
def envs(config: ConfigParser):
    """List all existing environments
    """
    for fname in envs_path.iterdir():
        print(fname.stem)


@command
def config(config: ConfigParser):
    """Prints current configuration
    """
    print(f"Running from folder: {str(pydock_path)}\n")

    for section in config.sections():
        print(f"[{section}]")

        for name, value in config.items(section):
            print(name, "=", value)

        print("")


DOCKER_TEMPLATE = """
FROM {repository}python:{version}

RUN apt update && apt install sudo

RUN adduser --gecos '' --disabled-password {user} && \
  echo "{user} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/nopasswd

COPY requirements.txt /src/requirements.txt
USER {user}
RUN pip install -r /src/requirements.txt

"""


@command
def create(config: ConfigParser, name:str, version:str):
    """Create a new environment

<name>      A suitable name for the environment (e.g., a project name)
<version>   A Python version (e.g., 3.8 or 3.8.7)
    """
    env_dir = envs_path / name
    
    try:
        env_dir.mkdir()
    except FileExistsError:
        print(f"🔴 Environment '{name}' already exists!")
        return

    dockerfile = env_dir / f"dockerfile"
    requirements = env_dir / f"requirements.txt"

    with dockerfile.open("w") as fp:
        fp.write(DOCKER_TEMPLATE.format(repository=config.get('docker', 'repository'), version=version, user=config.get("environment", "username")).strip())

    with requirements.open("w") as fp:
        pass

    build(config, name)


@command
def build(config: ConfigParser, name:str):
    """(re)Builds an environment Docker image

<name>      The name of the environment (must already exist)

NOTE: This is usually not necessary, unless you want to manually
rebuild the image associated with an environment.
The call to `create` automatically calls `build`.
    """
    env_dir = envs_path / name
    dockerfile = env_dir / f"dockerfile"

    if not env_dir.exists():
        print(f"🔴 Environment '{name}' doesn't exist!")
        return

    print(f"⏳ Building image for environment '{name}'")
    command = ["docker", "build", "-t", f"pydock-{name}:latest", "-f", str(dockerfile), str(env_dir)]

    if config.getboolean("docker", "sudo"):
        command.insert(0, "sudo")

    subprocess.run(command)
    print(f"🟢 Environment '{name}' created successfully!")


@command
def delete(config: ConfigParser, name:str):
    """Deletes an environment

<name>      The name of the environment
    """
    env_dir = envs_path / name

    if not env_dir.exists():
        print(f"🔴 Environment '{name}' doesn't exist!")
        return

    shutil.rmtree(env_dir)

    # TODO: Decide whether to delete the Docker image makes sense
    # command = ["docker", "rmi", "--force", f"pydock-{name}:latest"]

    # if config.getboolean("docker", "sudo"):
    #     command.insert(0, "sudo")

    # subprocess.run(command)

    print(f"🟢 Environment '{name}' succesfully deleted!")


@command
def shell(config: ConfigParser, name:str):
    """Open a shell inside an environment

<name>      The name of the environment

The current working directory is mounted inside the environment.
    """
    env_dir = envs_path / name

    if not env_dir.exists():
        print(f"🔴 Environment '{name}' doesn't exist!")
        return

    print(f"🚀 Creating shell for '{name}'")

    username = config.get("environment", "username")
    cwd = Path.cwd().resolve()

    command = ["docker", "run", "--rm", "-it", "--user", str(os.geteuid()), "--hostname", name, "-v", f"{cwd}:/home/{username}/{cwd.stem}", "-w", f"/home/{username}/{cwd.stem}", f"pydock-{name}:latest", "bash"]

    if config.getboolean("docker", "sudo"):
        command.insert(0, "sudo")

    subprocess.run(command)

    print(f"🏁 Shell instance for '{name}' ended.")


def main():
    config: ConfigParser = init()

    if not args:
        print("Usage: pydock [--local/--global] <command> [args...]")
        print("")
        for command in COMMANDS.values():
            print(command)

        return

    command = COMMANDS[args.pop(0)]
    command(config, *args)
    

if __name__ == "__main__":
    main()
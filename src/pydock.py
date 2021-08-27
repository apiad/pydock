#!/usr/bin/env python3

# MIT License
#
# Copyright (c) 2021 Alejandro Piad Morffis
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import sys
import os
import shutil
import inspect
import getpass
from configparser import ConfigParser
import subprocess
from pathlib import Path
from typing import Callable


__version__ = "0.0.3"


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
            print(f"ℹ️  Usage: pydock {self.name} {self.args_help}")
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
    docker_images_cmd = ["docker", "images"]

    if config.get("docker", "sudo"):
        docker_images_cmd.insert(0, "sudo")

    docker_images = [line.split() for line in subprocess.run(docker_images_cmd, stdout=subprocess.PIPE).stdout.decode('utf8').split("\n")[1:]]
    docker_images = { line[0]: line[1:] for line in docker_images if line }
    env_names = list(envs_path.iterdir())

    print(f"ENVIRONMENT     VERSION     IMAGE HASH    UPDATED         SIZE")

    for fname in env_names:
        env_name = fname.stem
        version, hash, *time, size  = docker_images[f"pydock-{env_name}"]

        print(f"{env_name:16}{version:12}{hash:14}{' '.join(time):16}{size}")


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

RUN adduser --gecos '' --disabled-password {user} && echo "{user} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/nopasswd

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

    try:
        result = subprocess.run(command)
        assert result.returncode == 0
        print(f"🟢 Environment '{name}' created successfully!")
    except:
        print(f"🔴 Environment '{name}' failed!")
        delete(config, name)



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
    command = ["docker", "rmi", "--force", f"pydock-{name}:latest"]

    if config.getboolean("docker", "sudo"):
        command.insert(0, "sudo")

    subprocess.run(command)

    print(f"💣 Environment '{name}' succesfully deleted.")


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


@command
def install(config: ConfigParser, env:str, package:str):
    """Install a package in an environment and update requirements

<env>       The environment where to install.
<package>   A package name in pip format (e.g., can have a pinned version)

After installation, the image for the environment will be updated,
and the installed packages will be commited to the requirements, using `pip freeze`.
    """
    env_dir = envs_path / env
    requirements = env_dir / "requirements.txt"
    username = config.get("environment", "username")

    if not env_dir.exists():
        print(f"🔴 Environment '{env}' doesn't exist!")
        return

    print(f"💾 Installing {package} in environment '{env}'")

    # Run pip install and freeze requirements
    command = ["docker", "run", "--name", f"pydock-{env}-tmp", "-v", f"{requirements.resolve()}:/home/{username}/requirements.txt", "--user", str(os.geteuid()), f"pydock-{env}", "bash", "-c", f"pip install {package} && pip freeze > ~/requirements.txt"]

    if config.getboolean("docker", "sudo"):
        command.insert(0, "sudo")

    subprocess.run(command)

    print(f"🎁 Updating image for environment '{env}'")

    # Commit the container and update the image in-place
    command = ["docker", "commit", f"pydock-{env}-tmp"]

    if config.getboolean("docker", "sudo"):
        command.insert(0, "sudo")

    new_image_id = subprocess.run(command, stdout=subprocess.PIPE).stdout.decode("utf8").strip().split(":")[1]

    # Delete the old image
    command = ["docker", "rmi", "--force", f"pydock-{env}:latest"]

    if config.getboolean("docker", "sudo"):
        command.insert(0, "sudo")

    subprocess.run(command, stdout=subprocess.PIPE)

    # Tag the new image
    command = ["docker", "tag", new_image_id, f"pydock-{env}:latest"]

    if config.getboolean("docker", "sudo"):
        command.insert(0, "sudo")

    subprocess.run(command)

    # Remove the dangling container
    command = ["docker", "rm", f"pydock-{env}-tmp"]

    if config.getboolean("docker", "sudo"):
        command.insert(0, "sudo")

    subprocess.run(command, stdout=subprocess.PIPE)


def main():
    config: ConfigParser = init()

    if not args:
        print("ℹ️  Usage: pydock [--local/--global] <command> [args...]")
        print("")
        for command in COMMANDS.values():
            print(command)

        return

    command = COMMANDS[args.pop(0)]
    command(config, *args)


if __name__ == "__main__":
    main()

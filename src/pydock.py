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
import textwrap


__version__ = "0.0.6"

# Templates

DOCKER_TEMPLATE = """
FROM {prefix}{base}:{version}

RUN apt update && apt install sudo

RUN adduser --gecos '' --disabled-password {user} && echo "{user} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/nopasswd

WORKDIR /home/{user}/
USER {user}

RUN echo 'export PATH=/home/{user}/.local/bin:$PATH' >> ~/.bashrc

COPY requirements.txt /src/requirements.txt
RUN pip --disable-pip-version-check install -r /src/requirements.txt
""".strip()

# Determining the current working directory

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
config_file = pydock_path / "pydock.conf"
docker_template = pydock_path / "template.dockerfile"


def init():
    pydock_path.mkdir(exist_ok=True)
    config = ConfigParser()
    config.add_section("docker")
    config.set("docker", "prefix", "")
    config.set("docker", "base", "python")
    config.set("docker", "sudo", "False")
    config.set("docker", "user", getpass.getuser())

    config.read(config_file)

    with config_file.open("w") as fp:
        config.write(fp)

    if not docker_template.exists():
        with docker_template.open("w") as fp:
            fp.write(DOCKER_TEMPLATE)

    with docker_template.open() as fp:
        config.docker_template = fp.read()

    return config


COMMANDS = {}


class Command:
    def __init__(self, func: Callable) -> None:
        self.func = func
        self.name = func.__name__
        self.doc = textwrap.dedent(func.__doc__).strip()
        self.doc_short = self.doc.split("\n")[0]
        self.signature = inspect.signature(self.func)
        self.args = list(self.signature.parameters.keys())[1:]
        self.args_help = " ".join(f"<{arg}>" for arg in self.args)

    def __call__(self, config, *args):
        try:
            binding = self.signature.bind(config, *args)
        except TypeError:
            print(f"✨ Usage: pydock {self.name} {self.args_help}")
            print("")
            print(self.doc)
            return

        return self.func(*binding.args)


    def __str__(self):
        return f"{self.name:16}{self.doc_short.strip()}"


def command(func):
    COMMANDS[func.__name__] = Command(func)
    return func


@command
def envs(config: ConfigParser):
    """
    List all existing environments
    """
    docker_images_result = docker("images", config=config, stdout=subprocess.PIPE)
    docker_images = [
        line.split()
        for line in docker_images_result.stdout.decode("utf8").split("\n")[1:]
    ]
    docker_images = {line[0]: line[1:] for line in docker_images if line}
    env_names = [path for path in pydock_path.iterdir() if path.is_dir()]

    print(f"ENVIRONMENT         IMAGE HASH          UPDATED             SIZE")

    for fname in env_names:
        env_name = fname.stem
        version, hash, *time, size = docker_images[f"pydock-{env_name}"]

        print(f"{env_name:20}{hash:20}{' '.join(time):20}{size}")


@command
def config(config: ConfigParser):
    """
    Prints current configuration
    """
    print(f"Running from folder: {str(pydock_path)}\n")

    for section in config.sections():
        print(f"[{section}]")

        for name, value in config.items(section):
            print(name, "=", value)

        print("")


@command
def create(config: ConfigParser, name: str, version: str):
    """
    Create a new environment

    <name>      A suitable name for the environment (e.g., a project name)
    <version>   A Python version (e.g., 3.8 or 3.8.7)
    """
    env_dir = pydock_path / name

    try:
        env_dir.mkdir()
    except FileExistsError:
        print(f"🔴 Environment '{name}' already exists!")
        return

    dockerfile = env_dir / f"dockerfile"
    requirements = env_dir / f"requirements.txt"

    with dockerfile.open("w") as fp:
        fp.write(
            config.docker_template.format(
                prefix=config.get("docker", "prefix"),
                base=config.get("docker", "base"),
                version=version,
                user=config.get("docker", "user"),
            ).strip()
        )

    with requirements.open("w") as fp:
        pass

    if not build(config, name):
        delete(config, name)


@command
def build(config: ConfigParser, name: str):
    """
    (re)Builds an environment Docker image

    <name>      The name of the environment (must already exist)

    NOTE: This is usually not necessary, unless you want to manually
    rebuild the image associated with an environment.
    The call to `create` automatically calls `build`.
    """
    env_dir = pydock_path / name
    dockerfile = env_dir / f"dockerfile"

    if not env_dir.exists():
        print(f"🔴 Environment '{name}' doesn't exist!")
        return

    print(f"⏳ Building image for environment '{name}'")

    try:
        docker(
            "build",
            "-t",
            f"pydock-{name}:latest",
            "-f",
            str(dockerfile),
            str(env_dir),
            config=config,
        )
        print(f"🟢 Environment '{name}' built successfully!")
        return True
    except:
        print(f"🔴 Building environment '{name}' failed!")
        return False


@command
def delete(config: ConfigParser, name: str):
    """
    Deletes an environment

    <name>      The name of the environment
    """
    env_dir = pydock_path / name

    if not env_dir.exists():
        print(f"🔴 Environment '{name}' doesn't exist!")
        return

    shutil.rmtree(env_dir)

    # TODO: Decide whether to delete the Docker image makes sense
    docker("rmi", "--force", f"pydock-{name}:latest", config=config, throw=False)

    print(f"💣 Environment '{name}' succesfully deleted.")


@command
def run(config: ConfigParser, name: str, *command):
    """
    Open a shell inside an environment and run a command

    <name>        The name of the environment
    [command...]  Optional command to run (defaults to 'bash')

    The current working directory is mounted inside the environment.
    """
    env_dir = pydock_path / name

    if not env_dir.exists():
        print(f"🔴 Environment '{name}' doesn't exist!", file=sys.stderr)
        return

    print(f"🚀 Creating shell for '{name}'", file=sys.stderr)

    user = config.get("docker", "user")
    cwd = Path.cwd().resolve()

    command = list(command)

    if not command:
        command = ["bash"]

    if sys.stdin.isatty():
        terminal = "-it"
    else:
        terminal = ""

    docker(
        "run",
        "--rm",
        terminal,
        "--user",
        str(os.geteuid()),
        "--hostname",
        name,
        "-v",
        f"{cwd}:/home/{user}/{cwd.stem}",
        "-w",
        f"/home/{user}/{cwd.stem}",
        f"pydock-{name}:latest",
        *command,
        config=config,
        throw=False,
    )

    print(f"🏁 Shell instance for '{name}' ended.", file=sys.stderr)


@command
def install(config: ConfigParser, env: str, package: str):
    """
    Install a package in an environment and update requirements

    <env>       The environment where to install.
    <package>   A package name in pip format (e.g., can have a pinned version)

    After installation, the image for the environment will be updated,
    and the installed packages will be commited to the requirements, using `pip freeze`.
    """
    env_dir = pydock_path / env
    requirements = env_dir / "requirements.txt"
    user = config.get("docker", "user")

    if not env_dir.exists():
        print(f"🔴 Environment '{env}' doesn't exist!", file=sys.stderr)
        return

    print(f"💾 Installing {package} in environment '{env}'", file=sys.stderr)

    try:
        # Run pip install and freeze requirements
        docker(
            "run",
            "--name",
            f"pydock-{env}-tmp",
            "-v",
            f"{requirements.resolve()}:/home/{user}/requirements.txt",
            "--user",
            str(os.geteuid()),
            f"pydock-{env}",
            "bash",
            "-c",
            f"pip install {package} && pip freeze > ~/requirements.txt",
            config=config,
        )

        print(f"🎁 Updating image for environment '{env}'", file=sys.stderr)

        # Commit the container and update the image in-place
        new_image_id = (
            docker("commit", f"pydock-{env}-tmp", config=config, stdout=subprocess.PIPE)
            .stdout.decode("utf8")
            .strip()
            .split(":")[1]
        )
        # Delete the old image
        docker(
            "rmi", "--force", f"pydock-{env}:latest", config=config, stdout=subprocess.PIPE
        )
        # Tag the new image
        docker("tag", new_image_id, f"pydock-{env}:latest", config=config)
    except:
        print(f"🔴 Install command failed!", file=sys.stderr)
    finally:
        # Remove the dangling container
        docker(
            "rm", "--force", f"pydock-{env}-tmp",
            config=config,
            throw=False,
            stdout=subprocess.PIPE,
        )


@command
def update(config: ConfigParser, env: str, package: str):
    """
    Update a package in an environment and update requirements

    <env>       The environment where to update.
    <package>   A package name to update

    After installation, the image for the environment will be updated,
    and the installed packages will be commited to the requirements, using `pip freeze`.
    """
    env_dir = pydock_path / env
    requirements = env_dir / "requirements.txt"
    user = config.get("docker", "user")

    if not env_dir.exists():
        print(f"🔴 Environment '{env}' doesn't exist!", file=sys.stderr)
        return

    print(f"💾 Updating {package} in environment '{env}'", file=sys.stderr)

    # Run pip install and freeze requirements
    try:
        docker(
            "run",
            "--name",
            f"pydock-{env}-tmp",
            "-v",
            f"{requirements.resolve()}:/home/{user}/requirements.txt",
            "--user",
            str(os.geteuid()),
            f"pydock-{env}",
            "bash",
            "-c",
            f"pip install -U {package} && pip freeze > ~/requirements.txt",
            config=config,
        )

        print(f"🎁 Updating image for environment '{env}'", file=sys.stderr)

        # Commit the container and update the image in-place
        new_image_id = (
            docker("commit", f"pydock-{env}-tmp", config=config, stdout=subprocess.PIPE)
            .stdout.decode("utf8")
            .strip()
            .split(":")[1]
        )
        # Delete the old image
        docker(
            "rmi", "--force", f"pydock-{env}:latest", config=config, stdout=subprocess.PIPE
        )
        # Tag the new image
        docker("tag", new_image_id, f"pydock-{env}:latest", config=config)
    except:
        print(f"🔴 Update command failed!", file=sys.stderr)
    finally:
        # Remove the dangling container
        docker(
            "rm", "--force", f"pydock-{env}-tmp",
            config=config,
            throw=False,
            stdout=subprocess.PIPE,
        )


@command
def uninstall(config: ConfigParser, env: str, package: str):
    """
    Uninstall a package in an environment and update requirements

    <env>       The environment where to update.
    <package>   A package name to uninstall

    After installation, the image for the environment will be updated,
    and the installed packages will be commited to the requirements, using `pip freeze`.
    """
    env_dir = pydock_path / env
    requirements = env_dir / "requirements.txt"
    user = config.get("docker", "user")

    if not env_dir.exists():
        print(f"🔴 Environment '{env}' doesn't exist!", file=sys.stderr)
        return

    print(f"💾 Uninstalling {package} in environment '{env}'", file=sys.stderr)

    try:
        # Run pip install and freeze requirements
        docker(
            "run",
            "--name",
            f"pydock-{env}-tmp",
            "-v",
            f"{requirements.resolve()}:/home/{user}/requirements.txt",
            "--user",
            str(os.geteuid()),
            f"pydock-{env}",
            "bash",
            "-c",
            f"pip uninstall -y {package} && pip freeze > ~/requirements.txt",
            config=config,
        )

        print(f"🎁 Updating image for environment '{env}'", file=sys.stderr)

        # Commit the container and update the image in-place
        new_image_id = (
            docker("commit", f"pydock-{env}-tmp", config=config, stdout=subprocess.PIPE)
            .stdout.decode("utf8")
            .strip()
            .split(":")[1]
        )
        # Delete the old image
        docker(
            "rmi", "--force", f"pydock-{env}:latest", config=config, stdout=subprocess.PIPE
        )
        # Tag the new image
        docker("tag", new_image_id, f"pydock-{env}:latest", config=config)
    except:
        print(f"🔴 Delete command failed!", file=sys.stderr)
    finally:
        # Remove the dangling container
        docker(
            "rm", "--force", f"pydock-{env}-tmp",
            config=config,
            throw=False,
            stdout=subprocess.PIPE,
        )


def docker(*command, config, throw=True, **kwargs):
    command = list(command)
    command.insert(0, "docker")

    if config.getboolean("docker", "sudo"):
        command.insert(0, "sudo")

    result = subprocess.run(command, **kwargs)

    if throw and result.returncode != 0:
        raise Exception("Error return code in subprocess")

    return result


def main():
    config: ConfigParser = init()

    if not args:
        print("✨ Usage: pydock [--local/--global] <command> [args...]")
        print("")
        for command in COMMANDS.values():
            print(command)

        return

    command = COMMANDS[args.pop(0)]
    command(config, *args)


if __name__ == "__main__":
    main()

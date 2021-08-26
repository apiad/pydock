# pydock - Docker-based environment manager for Python

> ⚠️ `pydock` is still in beta mode, and very unstable. It is not recommended for anything serious.

`pydock` is a poor man's Python environment manager fully based on Docker.
You can think of it as a replacement for `virtualenv`.

The purpose of `pydock` is to avoid having to install *anything at all* in your system, and instead manage everything using Docker.
In short, `pydock` gives you an interface similar to most Python environment managers, but uses Docker under the hood, creating dockerfiles, images, and containers as necessary.
This creates a bunch of additional headaches, that's for sure, but it has some nice conveniences.

With `pydock` you can create "virtual" environments, which are actually Docker images, and manage them similarly as with `virtualenv` and any other Python environment manager.
Every environment you create has associated `dockerfile` and `requirements.txt` files which provide a completely platform-independent description of that environment.
Thus, if at any point you want to migrate those environments to another computer, you just need to copy these files, and run `pydock build` there.

## Instalation

`pydock` is a single Python file with no dependencies outside the Python standard library (and Docker, that is), so you can just download it, give it execution permision, and add it to your path. In Linux one way to do this is:

```bash
sudo curl https://raw.githubusercontent.com/apiad/pydock/main/pydock.py > /usr/bin/pydock
sudo chmod +x /usr/bin/pydock
``` 

The only requirements are a working version of Python (the standard that comes with your distro should work) and having [Docker](https://docs.docker.com/engine/install/) installed.

## Usage

Run `pydock` to see all available commands, and run `pydock <command>` to see a small help for that command.

## License and Contribution

Code is MIT, and all contributions are appreciated 👋!

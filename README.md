# pydock - Docker-based environment manager for Python

> ⚠️ `pydock` is still in beta mode, and very unstable. It is not recommended for anything serious.

`pydock` is a poor man's Python environment manager fully based on Docker.
You can think of it as a replacement for `virtualenv`.
In reality, `pydock` is just a very thing wrapper around Docker, so everything you can do with `pydock` you can also do it yourself just with Docker.

The purpose of `pydock` is to avoid having to install *anything at all* in your system, and instead manage everything using Docker.
In short, `pydock` gives you an interface similar to most Python environment managers, but uses Docker under the hood, creating dockerfiles, images, and containers as necessary.
This creates a bunch of additional headaches, that's for sure, but it has some nice conveniences.

With `pydock` you can create "virtual" environments, which are actually Docker images, and manage them similarly as with `virtualenv` and any other Python environment manager.
Every environment you create has associated `dockerfile` and `requirements.txt` files which provide a completely platform-independent description of that environment.
Thus, if at any point you want to migrate those environments to another computer, you just need to copy these files, and run `pydock build` there.

## Design 

`pydock`'s mantra is zero-dependencies and absolute freedom.
This means it will never create an environment that requires you to install anything to use, not even `pydock` (outside of Docker, that is, but everyone is already using Docker, right?)
In particular, these are some principles we abide to:

- **Use of open standards for decribing environments:** Right now the definition of an environment is just a `dockerfile` and a `requirement.txt`. 
There is not and will never be any pydock-specific file there. 
This means you completely control what goes into an environment, and will never be locked into using `pydock` for runing or modifying an environment.

## Instalation

`pydock` is a single Python file with no dependencies outside the Python standard library (and [Docker](https://docs.docker.com/engine/install/))., so you can just download it, give it execution permision, and add it to your path. In Linux one way to do this is:

```bash
sudo curl https://raw.githubusercontent.com/apiad/pydock/main/pydock.py > /usr/bin/pydock
sudo chmod +x /usr/bin/pydock
``` 

If you only want to use `pydock` inside a specific project, then you can just download the [pydock.py](https://raw.githubusercontent.com/apiad/pydock/main/pydock.py) file into your codebase and add commit it to your repository. Then you can use it localy as:

```
./pydock --local <command> [args...]
```

## Usage

Run `pydock` to see all available commands, and run `pydock <command>` to see a small help for that command.

## License and Contribution

Code is MIT, and all contributions are appreciated 👋!

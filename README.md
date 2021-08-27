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

- **Depend only on the standard library:** Since `pydock` is supposed to remove your need to install things in your system's Python, it cannot depend on anything that is not bundled in the standard Python distribution that comes with most operating systems (we're talking *real* operating systems here 😛).

## Installation (sort of...)

`pydock` is a single Python file with no dependencies outside the Python standard library and [Docker](https://docs.docker.com/engine/install/).
So you can just download it, give it execution permisions, and add it to your path.

In Linux one way to do this is with this convenience script:

```bash
curl https://raw.githubusercontent.com/apiad/pydock/main/install/linux.sh | sudo bash
```

If you only want to use `pydock` inside a specific project, then you can just download the [pydock.py](https://raw.githubusercontent.com/apiad/pydock/main/src/pydock.py) file into your codebase and commit it to your repository.
Then you can use it locally as (provided you gave it execution permisions):

```
./pydock.py --local <command> [args...]
```

## Usage

Run `pydock` to see all available commands, and run `pydock <command>` to see a small help for that command.

`pydock` can run in *global* or *local* mode, the difference being where it will store the environments configuration.
In *global* mode, everything will be stored in `~/.pydock`, at the `/home` of the current user.
In *local* mode, everything is stored inside a `.pydock` folder at the current working directory.
The rules to decide whether to run in global or local mode are:

* If you explicitely type `pydock --local` it will be local. Likewise, if you explicitely type `pydock --global` it will be global.
* If no explicit flag is used, then if there is a `.pydock` folder already created in the current folder (i.e., you ran `pydock --local` sometime before), it will default to *local* mode.
* Otherwise, it will run in *global* mode.

We recommend global mode when you're creating an environment for interactive coding, e.g., for notebooks, one-off scripts, etc.
They are stored in your home folder and can be accessed from anywhere.

Use local mode when you're creating one or more environments for a specific project.
Store them with the project source code and probably even commit them to version control, so that all developers share the same environments.

> In any moment, you can type `pydock config` and it will tell you whether it is running in local or global mode.

### Creating an environment

Run `pydock [--local/--global] create <name> <version>` to create a new environment with a given name and Python version. For example:

```bash
pydock create datascience 3.8
```

This command will do the following:

* Create a new folder `datascience` inside `.pydock/envs` (wherever that folder is depends on the *local* vs *global* mode).
* Create a `dockerfile` and `requirements.txt` files inside that folder.
* Run `docker build` in that context, effectively creating a new image with your desired Python version.

By default, that image will have a user named like the user who run `pydock create` (this can be customized via configuration).

### Executing a shell in an environment

After creating an environment, if you run `docker images` you'll see a `pydock-<name>:latest` image, which corresponds to your environment.
You can easily start it with (continuing with the previous example):

```bash
pydock shell datascience
```

This will execute a `docker run ... datascience bash` command tailored to that environment with some additional tidbits.
One is that your current working directory will be mounted inside the newly created container's `/home/<user>`, which will be the starting working directory.
Thus, inside the container, whatever you do will be reflected back in your host filesystem, hopefully with the right permissions.

### Installing dependencies in an environment

In any existing environment `pydock` can help you install new dependencies while keeping updated the Docker image and tracking all packages.
For example:

```
pydock install datascience pandas
```

This will launch a fresh container in the `datascience` environment and install `pandas`.
`pydock` will commit the container and re-tag the new image such that it replaces the existing one for this environment, effectively saving the changes you did to the environment.
Additionally, the `requirements.txt` will be updated with the contents of `pip freeze`, such that next time you call `build` you'll have the same environment.

### Rebuilding an environment

At any moment, the `pydock-<name>` images that correspond to each environment should be up-to-date but, if you manually modify the `dockerfile` or `requirements.txt` (which you are absolutely free to do), you can run this command to rebuild and tag the corresponding image.

```bash
pydock build <name>
```

This command is also useful if you want to move environments around.
For example, by commiting your local `.pydock` folder into source control for a given project, other developers can easily run `pydock build ...` after checkout and the corresponding environment(s) will be created.

If you run `build` manually, `pydock` will not delete the old image for that container, which will appear labelled `<none>`. Make sure to either delete it manually with `docker rmi` or run `docker system prune` periodically to remove any accumulated waste.

## Roadmap

### Planned

- Add a `docker-compose.yml` file to environments to handle port bindings, volumes, etc.
- Change `dockerfile` template such that `user` and `repository` are args, inserted during `build` instead of when generating the file.
- Automatically delete untagged images when installing new dependencies.
- Add commands to remove and update dependencies.
- Improve install script to make it robust to different paths for the `python` command.

### v0.0.2

- Add a command to install dependencies inside the environment and commit/rebuild the image.

### v0.0.1

- Basic layout
- Commands to create, list, and run a shell inside of environments.

## License and Contribution

Code is MIT, and all contributions are appreciated 👋!

To use `pydock` in development mode, after you fork and clone, run:

```bash
sudo make dev
```

This will create a soft link in `/usr/bin/pydock` to your working `src/pydock.py` file, so that when you type `pydock` you'll be using your development version.

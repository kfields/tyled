# Tyled :butterfly:

CLI utility for generating [Tiled](https://www.mapeditor.org/) Tilesets

:notebook: [Documentation](https://tyled.readthedocs.io/en/latest/)

:package: [Package](https://pypi.org/project/tyled/)

## Installation

### From PyPI

#### TLDR - do this at your own risk

        pip install tyled

#### Recommended - pipX

If you don't already have it installed go to https://pypi.org/project/pipx/ for instructions

        pipx install tyled


### From GitHub

Clone the repository

        git clone https://github.com/kfields/tyled.git
        
Navigate to the new directory which contains the repository

        cd tyled

Create a Python 3 virtual environment called `env`

        python3 -m venv env
        
Activate the environment

        source env/bin/activate
        
Install required packages

        pip install -r requirements.txt

## Commands

### Bake

        tyled bake mytileset.toml [--save/--no-save][--show/--no-show][--rotation/--no-rotation]

#### Options

Default options are --save, --no-show, --no-rotation

## Projects

Tyled Projects are defined using TOML files.

All Projects must at least have a name and type

```toml
name = 'mytileset'
type = 'collection'
```

### Options

Options may be defined within the project file.  Any options defined here will override the command line options

```toml
[options]
rotation = true
```

## Tilesets

Tyled currently supports three different kinds of Tilesets:

### Collection Tileset

A Collection Tileset is composed of tiles with images stored in separate files

```toml
name = 'mytileset'
type = 'collection'

firstgid = 1
source = 'sticker-knight/map'
```

This example will generate mytileset.tsx in the current working directory

### Orthogonal Tileset

An Orthogonal Tileset is composed of tiles that have the same dimensions in one image file

```toml
name = 'mytileset'
type = 'orthogonal'

firstgid = 1
source = 'platformer/tiles'
tilewidth = 128
tileheight = 128
spacing = 0
margin = 0
columns = 12
```

This example will generate mytileset.tsx and mytileset.png in the current working directory

### Atlas Tileset

An Atlas Tileset is composed of tiles that do not have the same dimensions in one image file

```toml
name = 'mytileset'
type = 'atlas'

firstgid = 0
source = 'sticker-knight/map'
width = 1024
height = 1024
spacing = 0
margin = 0
```

This example will generate mytileset.tsx and mytileset.png in the current working directory

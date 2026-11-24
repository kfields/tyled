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

Tyled needs Python 3.12 or newer. Create a virtual environment called `.venv`

        python3 -m venv .venv

Activate the environment

        source .venv/bin/activate

Install tyled, editable, with what the tests need

        pip install -e ".[test]"

Run the tests

        python -m pytest

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

Tyled supports these kinds of Tilesets:

### Collection Tileset

A Collection Tileset is composed of tiles with images stored in separate files

```toml
name = 'mytileset'
type = 'collection'
source = 'sticker-knight/map'
```

This example will generate mytileset.tsx in the current working directory

### Orthogonal Tileset

An Orthogonal Tileset is composed of tiles that have the same dimensions in one image file

```toml
name = 'mytileset'
type = 'orthogonal'
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

The source is a folder that contains multiple images

```toml
name = 'mytileset'
type = 'atlas'
source = 'sticker-knight/map'
width = 1024
height = 1024
spacing = 0
margin = 0
```

This example will generate mytileset.tsx and mytileset.png in the current working directory


### Sheet Tileset

A Sheet Tileset is composed of tiles that do not have the same dimensions in one image file

The source is an image

```toml
name = 'mytileset'
type = 'atlas'
source = 'sticker-knight/map'
width = 1024
height = 1024
spacing = 0
margin = 0
```

This example will generate mytileset.tsx and mytileset.png in the current working directory

### Grid Tileset

A Grid Tileset is an image that is already a grid of equal tiles (Kenney's tilemaps, say). The image is used
as it is: nothing is repacked or copied, and the `.tsx` refers to it by a path relative to where the `.tsx`
is written (the folder you run `tyled bake` in). Tile size is required; columns are read from the image,
and so are spacing and margin when the project gives neither and only one grid fits the image.

```toml
name = 'tiny-town'
type = 'grid'
source = 'kenney/tiny-town/Tilemap/tilemap.png'
tilewidth = 16
tileheight = 16
spacing = 1
```

This example will generate tiny-town.tsx in the current working directory, and no image.

#### Names and properties

Tiles are named by `[column, row]` (counted from 0 at the top left) or by `id`. Each name is unique in the
tileset and is written into the `.tsx` as the tile property `name`, which Tiled shows. Any tile may carry
properties (strings, integers, floats and booleans, written with Tiled's types), and `[defaults]` gives
every tile a starting set. A `region = [column, row, width, height]` entry, without a name, sets
properties on a block of tiles. Later entries win over earlier ones.

```toml
[defaults]
walkable = true

[[tiles]]
at = [8, 8]
name = 'well'
properties = { walkable = false, kind = 'well' }

[[tiles]]
region = [6, 0, 3, 3]
properties = { walkable = false }
```

#### Pieces

A piece is a named rectangle of tiles, given as a `region` of the image or as `rows` of tile names (an id
works for a tile without a name, `''` leaves a gap). Its `anchor = [column, row]`, inside the piece, is the
tile a layout's character stands for (the door of a house); it defaults to the top left. A piece can't
have the name of a tile.

```toml
[[pieces]]
name = 'house_wood_grey'
rows = [[48, 49, 50], [60, 'gable_grey', 62], [72, 'door_wood', 75]]
anchor = [1, 2]
```

Pieces are kept in the `.tsx` as tileset properties (`piece:<name>`, the ids row by row, and
`anchor:<name>`), so Tiled shows them and tyled reads them back.

A **nine-slice** is a piece with `kind = 'nine_slice'`: exactly three rows of three tiles (corners, edges
and a centre, no gaps), which a map can stretch to any size from 2 × 2 up by repeating the edges and the
centre. Its anchor defaults to the centre. Tiny Town's castle courtyard and dirt patch are nine-slices.
It is kept as one more tileset property, `kind:<name>` = `nine_slice`.

```toml
[[pieces]]
name = 'dirt_patch'
kind = 'nine_slice'
region = [0, 1, 3, 3]
```

#### Reading names from a program

```python
from tyled.tileset.names import read_tsx

named = read_tsx("tiny-town.tsx")        # or GridTileset.create(config).named
named.tile("well")                        # NamedTile(id=104, name='well', properties={...})
named.piece("house_wood_grey").ids        # ((48, 49, 50), (60, 63, 62), (72, 85, 75))
named.nine_slice("dirt_patch").stretch(4, 3)  # ((12, 13, 13, 14), (24, 25, 25, 26), (36, 37, 37, 38))
named.tile("wel")                         # UnknownNameError: no tile named 'wel'; did you mean 'well'?
```

`examples/tiny-town.toml` names Kenney's Tiny Town this way; run it from `examples/`:

        cd examples
        tyled bake tiny-town.toml

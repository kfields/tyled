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

## Maps

`tyled map` turns a text layout into a Tiled map: a character a tile, a legend from characters to named
tiles (see [Names and properties](#names-and-properties)), and a `.tmj` that opens in Tiled and can be
regenerated, enlarged and rearranged by editing the text.

        tyled map town.toml [--output town.tmj] [--merged]

It writes `<name>.tmj` in the current folder, or the file given with `--output`. (A layout that is a grid of
areas writes a Tiled world and a map for each area instead: see [Areas and a world](#areas-and-a-world).)
From a program:

```python
from tyled.map import build, build_all, MapProject

build("town.toml")                       # writes town.tmj, returns its path
build_all("town.toml")                   # the same, returning every path written (a list)
MapProject(config, base=".").to_dict()   # or the map as Tiled's JSON structure, without a file
```

### The map project

A map project is a TOML file. Its paths are relative to the file's own folder.

```toml
name = 'town'                  # the map is written as town.tmj
tilewidth = 16
tileheight = 16
layout = 'town.txt'
tilesets = ['tiny-town.toml']  # tileset projects (grid kind) or .tsx files, firstgids in this order
fill = 'grass'                 # a tile under everything on the ground layer (optional)

[layers]                       # these are the defaults; Neighbots reads exactly these
ground = 'ground'
obstacles = 'obstacles'
objects = 'objects'
extra = []                     # more tile layers, between ground and obstacles, bottom first
```

A tileset given as a `.toml` must have been baked (`tyled bake`): the map refers to the `.tsx` beside the
project, and says where it is relative to the `.tmj`.

### The layout

One character a tile, every line the same length (a ragged line is an error naming it). `.` is a cell
with nothing on it but the fill, and the filler inside a piece. A character the legend doesn't know is an
error naming it, its line and its column. For a large map the layout can be a grid of smaller files:
see [Areas and a world](#areas-and-a-world).

### The legend

```toml
[legend]
r = 'road_dirt'                                     # a name: a tile, a piece or a nine-slice
Y = { tile = 'pine', flip = 'h' }                   # turned or mirrored
H = { piece = 'house_wood_grey' }
C = { nine_slice = 'castle_courtyard' }
w = { tile = 'well', layer = 'objects' }            # a tile object
S = { tile = 'cart', layer = 'objects', name = 'food_stall', type = 'food_stall' }
```

* **A tile** is placed where its character is. `rotate` is a clockwise `0`, `90`, `180` or `270`; `flip` is
  `'h'`, `'v'` or `'hv'`, done after the rotation. They are written as Tiled's flip flags on the gid, so
  one fence or road-edge tile serves every direction. A piece or nine-slice can be turned too: it is turned
  as one picture.
* **A piece** is placed so that its anchor lands on the character (a house's door where `H` is). The
  piece's other cells in the layout must hold the same character or `.`; a piece that runs off the map,
  or lies over another piece or a nine-slice, is an error naming both (except on a nine-slice's edge,
  below). When a piece's other cells are
  drawn with its own character, put the anchor first in reading order (a piece whose anchor is at the
  top left, say); otherwise draw those cells as `.`.
* **A nine-slice** takes the cells of its character, which must make one full rectangle (anything else
  is an error), and is stretched to it, at least 2 × 2. Nothing else may stand inside the rectangle,
  except that **a piece may stand on its edge** (not at a corner): draw the piece's character in the
  edge's cells and the piece replaces the edge's tiles there, so a gate or doorway opens in a walled
  courtyard. The edge may not be left open with nothing in it, and a piece in the centre is an error.
  A piece may also lie partly outside the rectangle and reach in to its edge (its cells inside may be
  drawn as the nine-slice's own character).
* A name that two tilesets share needs `tileset = '<tileset name>'` in the entry.

**Layers.** A placed tile goes on the layer the entry's `layer` names, else the one in the tile's own
`layer` property, else `obstacles` if the tile has `walkable = false` and `ground` if not. A piece's tiles
are each placed by their own properties, so a house's walls block and its door is ground. A walkable tile
that is partly see-through (a gate's arch) can go above the ground with `walkable_layer = 'decor'` (a layer
named in `layers.extra`), so that the fill shows through it. A layer that the project doesn't name is an
error.

**Objects.** A tile whose layer is the objects layer becomes a tile object: positioned as Tiled positions
tile objects (`x` at the tile's left, `y` at its bottom), named by the entry's `name` (else the tile's
name) and typed by the entry's `type` (else the tile's `kind` property). The type is written as both
`type` and `class` (Tiled 1.9 renamed one to the other). Objects are numbered in reading order. Only a
tile can be an object, and it can be flipped or turned 180 degrees but not by a quarter.

The output is deterministic: the same project, layout and tilesets give the same bytes.

### Areas and a world

A big map is easier to draw, read and redo in pieces. The layout may be a **grid of layout files**, one
per area, all the same size (a 3 × 3 town as nine files of 30 × 20 characters):

```toml
layout = [
    ['forest.txt', 'castle.txt', 'farm.txt'],
    ['meadow.txt', 'square.txt', 'houses.txt'],
    ['river.txt', 'lane.txt', 'orchard.txt'],
]
```

The areas are laid side by side and built as one map, so a legend, a fill and the tilesets are shared. Then

        tyled map town.toml [--output town.world] [--merged]

writes each area as a map of its own, named after its layout file (`forest.tmj`, ...), and a Tiled
**world** `town.world` (or the `--output` file, which must end in `.world`) that places them side by
side, so Tiled shows and edits the whole town together (load the `.world` from Tiled's World menu). With `--merged` it also writes `town.tmj`, the whole town as one map, for programs that load
a single map; it is exactly the areas side by side. In a program: `build_all("town.toml", merged=True)`.

A piece or nine-slice may not cross an area's edge: that is an error naming both areas, and a
nine-slice's rectangle that touches the edge of two areas is one too (leave a `.` between them). Errors
count lines and columns in the area's own file and name it. Every area needs a layout file with a name
of its own, which gives its map's name.

### Example: a town on Tiny Town

`examples/town.toml` and `examples/town.txt` draw a 30 × 20 town: grass, dirt roads, a dirt patch (a
nine-slice) inside a fence, houses with their doors on the road, trees, a castle courtyard (a nine-slice)
with a gateway standing in its south wall, and four objects: a food stall (`S`), a bench (`b`), the well
(`w`) and the target (`x`).

The fence is built from two of Tiny Town's tiles, turned: `1` to `4` are the corner tile turned 0, 90,
180 and 270 degrees, `-` is the horizontal run and `|` the same tile turned 90 degrees, and `g` is
the gap that serves as the yard's gate. Roads are plain dirt (`road_dirt`) until terrains give them
edges.

```
.....,....*...................
T1-----2*............CCCCCCCC.
Y|DDDDD|.............CCCCCCCC.
.|DDDDD|.T..F........CCCCCCCC.
.|DDDDD|.........f...CCCCCCCC.
.|DDDDD|.Y...........CCCCCCCC.
.4--g--3...,.........CCCGGCCC.
...,..x.Y.*.............rr....
.T...t......P..,...T..*.rr..Y.
.......*..............,.rr....
.,............w.........rr....
....H....h..S...b..A....rr....
rrrrrrrrrrrrrrrrrrrrrrrrrrrrrr
rrrrrrrrrrrrrrrrrrrrrrrrrrrrrr
..*....,......rr..............
.T...........,rr..t....T.t....
......*.....Y.rr..............
....H....h....rr.....B.....H..
rrrrrrrrrrrrrrrrrrrrrrrrrrrrrr
rrrrrrrrrrrrrrrrrrrrrrrrrrrrrr
```

Build it from `examples/`:

        cd examples
        tyled bake tiny-town.toml
        tyled map town.toml

The legend is in [`examples/town.toml`](examples/town.toml).

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

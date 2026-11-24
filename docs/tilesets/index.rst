********
Tilesets
********

Tyled supports these kinds of Tilesets:

Collection Tileset
==================

A Collection Tileset is composed of tiles with images stored in separate files

.. code-block:: toml

    name = 'mytileset'
    type = 'collection'
    source = 'sticker-knight/map'

This example will generate mytileset.tsx in the current working directory

Orthogonal Tileset
==================

An Orthogonal Tileset is composed of tiles that have the same dimensions in one image file

.. code-block:: toml

    name = 'mytileset'
    type = 'orthogonal'
    source = 'platformer/tiles'
    tilewidth = 128
    tileheight = 128
    spacing = 0
    margin = 0
    columns = 12

This example will generate mytileset.tsx and mytileset.png in the current working directory

Atlas Tileset
=============

An Atlas Tileset is composed of tiles that do not have the same dimensions in one image file

.. code-block:: toml

    name = 'mytileset'
    type = 'atlas'
    source = 'sticker-knight/map'
    width = 1024
    height = 1024
    spacing = 0
    margin = 0

This example will generate mytileset.tsx and mytileset.png in the current working directory

Options
-------

If you want a more compact spritesheet and your game engine supports it use the following:

.. code-block:: toml

    [options]
    rotation = true

Grid Tileset
============

A Grid Tileset is an image that is already a grid of equal tiles (Kenney's tilemaps, say). The image is
used as it is: nothing is repacked or copied, and the tileset refers to it by a path relative to where it
is written. Columns are read from the image, and so are spacing and margin when the project gives neither
and only one grid fits.

.. code-block:: toml

    name = 'tiny-town'
    type = 'grid'
    source = 'kenney/tiny-town/Tilemap/tilemap.png'
    tilewidth = 16
    tileheight = 16
    spacing = 1

    [defaults]
    walkable = true

    [[tiles]]
    at = [8, 8]
    name = 'well'
    properties = { walkable = false, kind = 'well' }

    [[pieces]]
    name = 'roofed_well'
    rows = [['well_roof'], ['well']]
    anchor = [0, 1]

Tiles are named by ``at = [column, row]`` or ``id``; the name is written as the tile property ``name``.
Properties are written as Tiled custom properties with Tiled's types. Pieces are kept as tileset
properties (``piece:<name>`` and ``anchor:<name>``). See the README for the details, and
``tyled.tileset.names.read_tsx`` for reading them back.

********
Tilesets
********

Tyled currently supports three different kinds of Tilesets:

Collection Tileset
==================

A Collection Tileset is composed of tiles with images stored in separate files

.. code-block:: toml

    name = 'mytileset'
    type = 'collection'

    firstgid = 1
    source = 'sticker-knight/map'

This example will generate mytileset.tsx in the current working directory

Orthogonal Tileset
==================

An Orthogonal Tileset is composed of tiles that have the same dimensions in one image file

.. code-block:: toml

    name = 'mytileset'
    type = 'orthogonal'

    firstgid = 1
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

    firstgid = 0
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


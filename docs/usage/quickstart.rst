**********
Quickstart
**********

Create a Tyled Project File
===========================

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

Generate the Tileset
====================

.. code:: bash

        tyled bake mytileset.toml

This example will generate mytileset.tsx and mytileset.png in the current working directory

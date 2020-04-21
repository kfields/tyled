********
Projects
********

Tyled Projects are defined using TOML files.

All Projects must at least have a name and type

.. code-block:: toml

    name = 'mytileset'
    type = 'collection'


Options
=======

Options may be defined within the project file.  Any options defined here will override the command line options

.. code-block:: toml

    [options]
    rotation = true

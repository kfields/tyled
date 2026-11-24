import tomllib

import click
from loguru import logger

from tyled.map import MapError, build_all as build_map_files
from tyled.tileset.factory import TilesetFactory
from tyled.tileset.names import NamedTilesError

def create_tileset(filename, **options):
    # tomllib insists on binary mode: it decodes the file as UTF-8 itself.
    with open(filename, "rb") as fh:
        config = tomllib.load(fh)
    tileset = TilesetFactory().produce(config, options=options)
    logger.debug(f"options: {vars(tileset.options)}")
    return tileset

@click.group()
@click.pass_context
def cli(ctx):
    ctx.ensure_object(dict)

@cli.command()
@click.pass_context
@click.option('--save/--no-save', default=True)
@click.option('--show/--no-show', default=False)
@click.option('--rotation/--no-rotation', default=False)
@click.argument('filename')
def bake(ctx, filename, **options):
    tileset = create_tileset(filename, **options)
    tileset.bake()

@cli.command()
@click.pass_context
@click.argument('filename')
def export(ctx, filename):
    tileset = create_tileset(filename)
    tileset.export()

@cli.command("map")
@click.option('--output', '-o', type=click.Path(dir_okay=False), default=None,
              help='The .tmj to write; default <name>.tmj in the current folder. '
                   'For a grid of areas, the .world to write (default <name>.world), with the areas beside it.')
@click.option('--merged/--no-merged', default=False,
              help='For a grid of areas, also write the whole town as one map, <name>.tmj beside the world.')
@click.argument('filename')
def map_command(filename, output, merged):
    """Build a Tiled map (.tmj) from a map project file and its text layout.

    A layout that is a grid of area files makes a map for each area and a Tiled world (.world)
    that places them side by side.
    """
    try:
        paths = build_map_files(filename, output, merged)
    except (MapError, NamedTilesError) as error:
        raise click.ClickException(str(error))
    for path in paths:
        logger.info(f"wrote {path}")

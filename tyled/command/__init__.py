import tomllib

import click
from loguru import logger

from tyled.tileset.factory import TilesetFactory

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

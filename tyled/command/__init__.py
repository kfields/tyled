import os
import click

import toml

from tyled.tileset import Tileset
from tyled.bake import main as _bake
from tyled.export import main as _export

config = toml.load('tyled.toml')

@click.group()
@click.pass_context
def cli(ctx):
    ctx.ensure_object(dict)

@cli.command()
@click.pass_context
def bake(ctx):
    ts = Tileset(config)
    _bake(ts)
    _export(ts)

import os
import click

import toml

from tyled.tileset import Tileset
from tyled.bake import main as _bake
from tyled.export import main as _export

config = toml.load('tyled.toml')
tileset = Tileset.create(config)

@click.group()
@click.pass_context
def cli(ctx):
    ctx.ensure_object(dict)

@cli.command()
@click.pass_context
def bake(ctx):
    _bake(tileset)
    _export(tileset)

@cli.command()
@click.pass_context
def export(ctx):
    _export(tileset)

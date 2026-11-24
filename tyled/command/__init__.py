import json
import sys
import tomllib
from pathlib import Path

import click
from loguru import logger

from tyled.check import CheckError, check_map
from tyled.map import MapError, build_all as build_map_files
from tyled.mapfile import MapFileError
from tyled.render import RenderError, render_map, render_sheet, save_png
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


class UsageProblem(click.ClickException):
    """A problem with how the command was used (as opposed to a map's problems), which exits with 2: 1 means 'the map has problems'."""

    exit_code = 2


def _tiles(text: str, count: int, what: str) -> tuple[int, ...]:
    try:
        numbers = tuple(int(part) for part in text.split(","))
    except ValueError:
        numbers = ()
    if len(numbers) != count:
        raise UsageProblem(f"{what} is {count} whole numbers with commas between them, not {text!r}")
    return numbers


def _region(text: str) -> tuple[int, int, int, int]:
    x, y, w, h = _tiles(text, 4, "--region")
    return x, y, w, h


@cli.command("render")
@click.option('--output', '-o', type=click.Path(dir_okay=False), default=None,
              help='The PNG to write; default <map name>.png in the current folder.')
@click.option('--scale', '-s', type=click.IntRange(min=1), default=2, show_default=True,
              help='Enlarge by this whole number, nearest-neighbour.')
@click.option('--region', default=None, metavar='X,Y,W,H', help='Draw only this part of the map, in tiles.')
@click.option('--layers', default=None, metavar='NAME,NAME',
              help='Draw only these layers (hidden ones too); default every visible layer.')
@click.option('--labels/--no-labels', default=False, help='Outline objects and write their names.')
@click.option('--grid/--no-grid', default=False, help='Draw the tile grid.')
@click.argument('filename', type=click.Path(dir_okay=False))
def render_command(filename, output, scale, region, layers, labels, grid):
    """Draw a map (.tmj, or a .world as one map) to a PNG, so you can look at it."""
    try:
        image = render_map(
            filename, scale=scale,
            region=_region(region) if region is not None else None,
            layers=[n for n in layers.split(",") if n] if layers is not None else None,
            labels=labels, grid=grid,
        )
    except (RenderError, MapFileError) as error:
        raise UsageProblem(str(error))
    path = save_png(image, output if output is not None else f"{Path(filename).stem}.png")
    logger.info(f"wrote {path}")


@cli.command("sheet")
@click.option('--output', '-o', type=click.Path(dir_okay=False), default=None,
              help='The PNG to write; default <tileset name>-sheet.png in the current folder.')
@click.option('--scale', '-s', type=click.IntRange(min=1), default=4, show_default=True,
              help='Enlarge each tile by this whole number, nearest-neighbour.')
@click.option('--columns', type=click.IntRange(min=1), default=None,
              help="Tiles to a row; default the tileset's own columns, or 8.")
@click.option('--mark', default='walkable=false', show_default=True, metavar='PROPERTY=VALUE',
              help="Border the tiles with this property in red; 'none' marks nothing.")
@click.argument('filename', type=click.Path(dir_okay=False))
def sheet_command(filename, output, scale, columns, mark):
    """Draw a tileset (.tsx) as a contact sheet: each tile with its id and name, pieces outlined."""
    marked = None
    if mark.lower() != 'none':
        key, separator, value = mark.partition('=')
        if not separator or not key:
            raise UsageProblem(f"--mark is PROPERTY=VALUE (or 'none'), not {mark!r}")
        marked = (key, _typed(value))
    try:
        image = render_sheet(filename, scale=scale, columns=columns, mark=marked)
    except (RenderError, MapFileError) as error:
        raise UsageProblem(str(error))
    path = save_png(image, output if output is not None else f"{Path(filename).stem}-sheet.png")
    logger.info(f"wrote {path}")


def _typed(text: str):
    """A property value as typed on the command line: true and false, whole numbers and numbers, else text."""
    if text in ('true', 'false'):
        return text == 'true'
    for kind in (int, float):
        try:
            return kind(text)
        except ValueError:
            pass
    return text


@cli.command("check")
@click.option('--project', type=click.Path(dir_okay=False), default=None,
              help="The map project (.toml): layers it doesn't declare are reported. Given as the map, it is its own.")
@click.option('--start', default=None, metavar='X,Y|NAME',
              help="Where people come from, a tile or an object's name; default the largest walkable area.")
@click.option('--json', 'as_json', is_flag=True, help='Print the findings as JSON, for programs.')
@click.argument('filename', type=click.Path(dir_okay=False))
def check_command(filename, project, start, as_json):
    """Check a map as a place: objects on walkable tiles, everything reachable, doors with room in front.

    FILENAME is a .tmj, a .world, or a map project (.toml). Exits with 1 when anything is wrong.
    """
    if start is not None and ',' in start:
        start = _tiles(start, 2, "--start")
    try:
        findings = check_map(filename, project=project, start=start)
    except (CheckError, MapFileError, MapError, NamedTilesError) as error:
        raise UsageProblem(str(error))
    if as_json:
        click.echo(json.dumps({"ok": not findings, "findings": [f.to_dict() for f in findings]}, indent=2))
    elif findings:
        for finding in findings:
            click.echo(str(finding))
        click.echo(f"{len(findings)} problem{'s' if len(findings) != 1 else ''}")
    else:
        click.echo("ok: no problems")
    if findings:
        sys.exit(1)

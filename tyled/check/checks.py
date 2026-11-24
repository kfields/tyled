"""The checks themselves. Each looks at the map through its tiles' properties and reports where it is wrong.

What a tile says about itself, as properties on the tileset:

* ``walkable`` (boolean): ``false`` blocks the cell. A tile without it is walkable, which is how step 2's
  map builder reads it too.
* ``kind = 'door'``: a door. ``opens`` names the side it opens to (``north``, ``south``, ``east`` or
  ``west`` as the tile's picture is drawn; ``south``, the tile below, if it says nothing). A door placed
  turned or flipped opens to the turned side.

A cell is **walkable** when some layer has a tile on it and no tile there says ``walkable = false``. An
object that blocks (its tile says ``walkable = false``, or it has a ``walkable = false`` property of its
own) also takes its cells away from walking.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tyled.mapfile import LoadedMap, MapObject, load_map

SIDES = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}


class CheckError(ValueError):
    """A check that can't be run as asked: a start that isn't on the map, a project that doesn't match."""


@dataclass(frozen=True)
class Finding:
    """One problem: what kind, what it is, and where.

    `x` and `y` are the tile (column and row, from 0 at the top left) where the problem is, or None for
    a problem with the map as a whole (a layer). `layer` and `object` say which layer's tile or which
    object, when it matters; `details` holds the rest in plain data.
    """

    kind: str
    message: str
    x: int | None = None
    y: int | None = None
    layer: str | None = None
    object: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "message": self.message,
            "x": self.x,
            "y": self.y,
            "layer": self.layer,
            "object": self.object,
            "details": self.details,
        }

    def __str__(self) -> str:
        where = f"{self.x},{self.y}: " if self.x is not None and self.y is not None else ""
        return f"{where}{self.message} [{self.kind}]"


def check_map(map, project=None, start=None) -> list[Finding]:
    """Check a map as a place and return what is wrong with it, in a fixed order; empty if it is fine.

    `map` is anything `load_map` takes (the path of a ``.tmj`` or ``.world``, a `MapProject`), or the path
    of a map project ``.toml``. `project` is the map's project (a `MapProject`, or its path): the layers
    it declares are the only ones the map should have. When `map` is a project, it is its own.

    `start` is where people come from: a tile ``(x, y)`` or the name of an object. Everything walkable
    should be reachable from there; without it, from the largest connected area.

    The checks, in this order: layers the project doesn't declare, tiles the tileset doesn't know or
    doesn't name, objects standing where they can't, doors with nothing in front, and walkable places cut off.
    """
    from tyled.map import MapProject

    if isinstance(map, (str, Path)) and Path(map).suffix == ".toml":
        map = _project(map)
    if isinstance(map, MapProject) and project is None:
        project = map
    if project is not None and not isinstance(project, MapProject):
        project = _project(project)
    loaded = load_map(map)

    findings: list[Finding] = []
    if project is not None:
        declared = [project.ground, *project.extra, project.obstacles, project.objects]
        for layer in loaded.layers:
            if layer.name not in declared:
                findings.append(Finding(
                    "undeclared_layer",
                    f"layer {layer.name!r} isn't declared by the project (its layers are {', '.join(repr(n) for n in declared)})",
                    layer=layer.name,
                ))
    findings += _tile_findings(loaded)
    grid = _Grid(loaded)
    findings += _object_findings(loaded, grid)
    findings += _door_findings(loaded, grid)
    findings += _reach_findings(loaded, grid, start)
    return findings


def _project(path):
    import tomllib

    from tyled.map import MapError, MapProject

    path = Path(path)
    try:
        with open(path, "rb") as fh:
            config = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise CheckError(f"project {str(path)!r}: {error}") from None
    try:
        return MapProject(config, base=path.parent)
    except MapError as error:
        raise CheckError(f"project {str(path)!r}: {error}") from None


# ---- tiles

def _tile_findings(loaded: LoadedMap) -> list[Finding]:
    """Tiles the tileset doesn't know and tiles it doesn't name, one finding for each kind of tile on a layer."""
    in_piece = {}
    for tileset in loaded.tilesets:
        in_piece[tileset.key] = {i for piece in tileset.named.pieces() for row in piece.ids for i in row if i is not None}

    groups: dict[tuple[str, str, int], list[tuple[int, int]]] = {}  # (kind, layer, gid) -> cells, reading order
    for layer in loaded.tile_layers():
        for index, raw in enumerate(layer.data):
            if raw:
                column, row = index % loaded.width, index // loaded.width
                _classify(loaded, in_piece, layer.name, raw, (column, row), groups)
    for layer in loaded.object_layers():
        for obj in layer.objects:
            if obj.gid:
                column, row = _cell_of(loaded, obj)[:2]
                _classify(loaded, in_piece, layer.name, obj.gid, (column, row), groups)

    findings = []
    order = loaded.layer_names()
    ranked = sorted(
        groups.items(),
        key=lambda item: (item[0][0] != "unknown_tile", order.index(item[0][1]), item[1][0][::-1], item[0][2]),
    )
    for (kind, layer, gid), cells in ranked:
        x, y = cells[0]
        more = f" and {len(cells) - 1} more" if len(cells) > 1 else ""
        what = "isn't in any tileset" if kind == "unknown_tile" else "has no name (and isn't in a piece)"
        found = loaded.resolve(gid)
        tile = f"tile {found[1]} of {found[0].name!r}" if found else f"gid {gid}"
        findings.append(Finding(
            kind, f"{tile} {what}: on layer {layer!r} at {x},{y}{more}", x, y, layer,
            details={"gid": gid, "count": len(cells), "positions": [list(c) for c in cells]},
        ))
    return findings


def _classify(loaded, in_piece, layer, raw, cell, groups) -> None:
    from tyled.map.transform import FLAGS

    gid = raw & ~(FLAGS | 0x10000000)
    found = loaded.resolve(gid)
    if found is None:
        groups.setdefault(("unknown_tile", layer, gid), []).append(cell)
        return
    tileset, id = found
    if tileset.tile_name(id) is None and id not in in_piece[tileset.key]:
        groups.setdefault(("unnamed_tile", layer, gid), []).append(cell)


# ---- walking

def _cell_of(loaded: LoadedMap, obj: MapObject) -> tuple[int, int, int, int]:
    """The cells an object covers as (first column, first row, last column, last row).

    A tile object's origin is its bottom left corner, so it stands on the cells above and to the right of
    (x, y); other objects (a point, a rectangle) from (x, y) down and right.
    """
    tw, th = loaded.tilewidth, loaded.tileheight
    width, height = obj.width, obj.height
    if obj.gid and not (width and height):
        found = loaded.resolve(obj.gid)
        width, height = (found[0].tilewidth, found[0].tileheight) if found else (tw, th)
    top = obj.y - height if obj.gid else obj.y
    first_column, first_row = int(obj.x // tw), int(top // th)
    last_column = max(first_column, int(-(-(obj.x + width) // tw)) - 1)
    last_row = max(first_row, int(-(-(top + height) // th)) - 1)
    return first_column, first_row, last_column, last_row


def _blocks(loaded: LoadedMap, obj: MapObject) -> bool:
    if "walkable" in obj.properties:
        return obj.properties["walkable"] is False
    return bool(obj.gid) and loaded.properties_of(obj.gid).get("walkable") is False


def _label(obj: MapObject) -> str:
    return obj.name or obj.type or f"#{obj.id}"


class _Grid:
    """Which cells can be walked on: the terrain by itself (`terrain`) and with blocking objects in the way (`walk`)."""

    def __init__(self, loaded: LoadedMap):
        self.width, self.height = loaded.width, loaded.height
        covered = [False] * (self.width * self.height)
        blocked = [False] * (self.width * self.height)
        for layer in loaded.tile_layers():
            for index, gid in enumerate(layer.data):
                if gid:
                    covered[index] = True
                    if loaded.properties_of(gid).get("walkable") is False:
                        blocked[index] = True
        self.terrain = [c and not b for c, b in zip(covered, blocked)]
        self.walk = list(self.terrain)
        self.objects: list[tuple[MapObject, tuple[int, int, int, int], bool]] = []
        for layer in loaded.object_layers():
            for obj in layer.objects:
                self.objects.append((obj, _cell_of(loaded, obj), _blocks(loaded, obj)))
        for _, (c0, r0, c1, r1), blocking in self.objects:
            if blocking:
                for cell in self.cells(c0, r0, c1, r1):
                    self.walk[cell[1] * self.width + cell[0]] = False

    def inside(self, column: int, row: int) -> bool:
        return 0 <= column < self.width and 0 <= row < self.height

    def cells(self, c0, r0, c1, r1):
        return [(c, r) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1) if self.inside(c, r)]

    def can_walk(self, column: int, row: int, terrain: bool = False) -> bool:
        return self.inside(column, row) and (self.terrain if terrain else self.walk)[row * self.width + column]

    def around(self, c0, r0, c1, r1):
        """The cells that touch a rectangle of cells along its sides, in reading order."""
        found = [(c, r0 - 1) for c in range(c0, c1 + 1)]
        found += [(c0 - 1, r) for r in range(r0, r1 + 1)] + [(c1 + 1, r) for r in range(r0, r1 + 1)]
        found += [(c, r1 + 1) for c in range(c0, c1 + 1)]
        return [c for c in found if self.inside(*c)]


def _object_findings(loaded: LoadedMap, grid: _Grid) -> list[Finding]:
    findings = []
    for obj, rect, blocking in grid.objects:
        c0, r0, c1, r1 = rect
        footprint = [(c, r) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)]
        standing = all(grid.can_walk(c, r, terrain=True) for c, r in footprint)
        label = _label(obj)
        details = {"id": obj.id, "blocks": blocking}
        if standing:
            continue
        if not blocking:
            findings.append(Finding(
                "object_on_blocked_tile", f"object {label!r} stands on a tile that can't be walked on (layer {obj.layer!r})",
                c0, r0, obj.layer, label, details,
            ))
        elif not any(grid.can_walk(c, r) for c, r in grid.around(c0, r0, c1, r1)):
            findings.append(Finding(
                "object_enclosed", f"object {label!r} blocks and has no walkable tile beside it (layer {obj.layer!r})",
                c0, r0, obj.layer, label, details,
            ))
    return findings


# ---- doors

def _door_findings(loaded: LoadedMap, grid: _Grid) -> list[Finding]:
    findings = []
    seen = []  # (gid, column, row, layer, label)
    for layer in loaded.tile_layers():
        for index, gid in enumerate(layer.data):
            if gid:
                seen.append((gid, index % loaded.width, index // loaded.width, layer.name, None))
    for obj, rect, _ in grid.objects:
        if obj.gid:
            seen.append((obj.gid, rect[0], rect[1], obj.layer, _label(obj)))
    for gid, column, row, layer, label in seen:
        props = loaded.properties_of(gid)
        if props.get("kind") != "door":
            continue
        side = str(props.get("opens", "south"))
        what = f"door {label!r}" if label else "door"
        if side not in SIDES:
            findings.append(Finding(
                "door_bad_side", f"{what} opens to {side!r}, which isn't north, south, east or west (layer {layer!r})",
                column, row, layer, label, {"opens": side},
            ))
            continue
        # The side is as the tile's picture is drawn: turn it as the placed tile is turned.
        (a, b), (c, d) = loaded.transform_of(gid).matrix
        dx, dy = SIDES[side]
        dx, dy = a * dx + b * dy, c * dx + d * dy
        facing = next(name for name, vector in SIDES.items() if vector == (dx, dy))
        in_front = (column + dx, row + dy)
        if not grid.can_walk(*in_front):
            findings.append(Finding(
                "door_blocked",
                f"{what} opens {facing} onto {in_front[0]},{in_front[1]}, which can't be walked on (layer {layer!r})",
                column, row, layer, label, {"opens": facing, "front": list(in_front)},
            ))
    return findings


# ---- reaching

def _start_cells(loaded: LoadedMap, grid: _Grid, start) -> set[tuple[int, int]]:
    if isinstance(start, str):
        found = [(rect, blocking) for obj, rect, blocking in grid.objects if obj.name == start]
        if not found:
            raise CheckError(f"start: the map has no object named {start!r}")
        cells = set()
        for rect, blocking in found:
            options = grid.cells(*rect) if not blocking else grid.around(*rect)
            cells |= {c for c in options if grid.can_walk(*c)}
        if not cells:
            raise CheckError(f"start: nothing walkable at or beside the object {start!r}")
        return cells
    try:
        x, y = start
    except (TypeError, ValueError):
        raise CheckError(f"start is a tile (x, y) or an object's name, not {start!r}") from None
    if not grid.inside(x, y):
        raise CheckError(f"start {x},{y} is not on the map ({grid.width} × {grid.height} tiles)")
    if not grid.can_walk(x, y):
        raise CheckError(f"start {x},{y} can't be walked on")
    return {(x, y)}


def _regions(grid: _Grid) -> list[list[tuple[int, int]]]:
    """The connected groups of walkable cells (up, down, left, right), each in reading order, first group first."""
    seen = [False] * (grid.width * grid.height)
    regions = []
    for row in range(grid.height):
        for column in range(grid.width):
            if seen[row * grid.width + column] or not grid.can_walk(column, row):
                continue
            seen[row * grid.width + column] = True
            queue = deque([(column, row)])
            cells = []
            while queue:
                c, r = queue.popleft()
                cells.append((c, r))
                for n in ((c, r - 1), (c - 1, r), (c + 1, r), (c, r + 1)):
                    if grid.can_walk(*n) and not seen[n[1] * grid.width + n[0]]:
                        seen[n[1] * grid.width + n[0]] = True
                        queue.append(n)
            regions.append(sorted(cells, key=lambda cell: (cell[1], cell[0])))
    return regions


def _reach_findings(loaded: LoadedMap, grid: _Grid, start) -> list[Finding]:
    regions = _regions(grid)
    if not regions:
        return [Finding("nothing_walkable", "no tile on the map can be walked on")]
    where = {cell: n for n, cells in enumerate(regions) for cell in cells}
    if start is None:
        main = {max(range(len(regions)), key=lambda n: (len(regions[n]), -n))}  # the largest; the first of equals
        origin = "the largest walkable area"
    else:
        main = {where[c] for c in _start_cells(loaded, grid, start)}
        origin = f"the start ({start if isinstance(start, str) else '%d,%d' % tuple(start)})"

    # Which objects each cut-off region holds: those that can be reached only from it.
    held: dict[int, list[str]] = {}
    for obj, rect, blocking in grid.objects:
        options = grid.around(*rect) if blocking else grid.cells(*rect)
        touching = [where[c] for c in options if c in where]
        if touching and not set(touching) & main:
            held.setdefault(touching[0], []).append(_label(obj))

    findings = []
    for n, cells in enumerate(regions):
        if n in main:
            continue
        columns, rows = [c for c, _ in cells], [r for _, r in cells]
        x, y = cells[0]
        bounds = [min(columns), min(rows), max(columns) - min(columns) + 1, max(rows) - min(rows) + 1]
        objects = held.get(n, [])
        extra = f"; it holds {', '.join(repr(o) for o in objects)}" if objects else ""
        findings.append(Finding(
            "region_cut_off",
            f"{len(cells)} walkable tile{'s' if len(cells) != 1 else ''} starting at {x},{y} "
            f"(within x {bounds[0]}..{bounds[0] + bounds[2] - 1}, y {bounds[1]}..{bounds[1] + bounds[3] - 1}) "
            f"can't be reached from {origin}{extra}",
            x, y, details={"cells": len(cells), "bounds": bounds, "objects": objects, "positions": [list(c) for c in cells]},
        ))
    return findings

"""A map project: tilesets, a layout, a legend; and the ``.tmj`` they make.

A map project file (TOML) says::

    name = 'town'                     # the map is written as town.tmj
    tilewidth = 16
    tileheight = 16
    layout = 'town.txt'               # one character a tile
    tilesets = ['tiny-town.toml']     # step 1's projects, or .tsx files; firstgids follow their order
    fill = 'grass'                    # a tile laid on the whole ground layer first (optional)
    # layout = [['forest.txt', 'castle.txt'], ['farm.txt', 'square.txt']]   # or a grid of areas, below

    [layers]                          # the names Neighbots reads; each one is optional
    ground = 'ground'
    obstacles = 'obstacles'
    objects = 'objects'
    extra = []                        # more tile layers, stacked between ground and obstacles

    [legend]
    r = 'road_cobble'                         # a character is a tile, a piece or a nine-slice by name
    T = { tile = 'pine', flip = 'h' }
    H = { piece = 'house_wood_grey' }
    C = { nine_slice = 'castle_courtyard' }
    W = { tile = 'well', layer = 'objects' }  # a tile object, not a tile

Paths are relative to the project file's folder. In the layout, ``.`` is a cell with nothing on it but
the fill, and the filler inside a piece's footprint.

How a character is placed:

* a **tile** goes in its cell;
* a **piece** is put down so that its anchor is on the character; the other cells it covers must hold
  the same character or ``.`` and lie on the map, and not on another piece or nine-slice (except on a
  nine-slice's edge, below);
* a **nine-slice** takes the rectangle of cells that hold its character, in one block, and is stretched
  to it. A piece may stand on an edge of the rectangle (not a corner), drawn there as the piece's own
  character, and replaces the edge's tiles: a gate or doorway in a wall. A piece may not stand in the
  centre, and nothing else may be inside the rectangle.

**Areas.** The layout may be a grid of layout files, one per area, all the same size. The areas are laid
side by side and placed as one map, so a piece or nine-slice may not cross from one area into another (an
error naming both areas); then each area is written as a map of its own (``<layout file's name>.tmj``) with a
Tiled world (``<name>.world``) that places them, and, if asked (``merged``), the whole town as one map
``<name>.tmj``, which is exactly the areas side by side.

Which layer a tile goes on: the legend entry's ``layer``, else the tile's ``layer`` property, else
``obstacles`` for a tile with ``walkable = false`` and ``ground`` for any other (or the entry's
``walkable_layer``, for walkable tiles you want above the ground, such as a gate's arch). A piece's tiles are
each placed by their own properties, so a house's door is on the ground and its walls block. A tile on the
objects layer becomes a tile object, named by the entry's ``name`` (else the tile's name) and typed by
the entry's ``type`` (else the tile's ``kind`` property).

The output is deterministic: layers, objects and keys come out in a fixed order and nothing is read
from the clock or the file system's order, so the same inputs give the same bytes.
"""

from __future__ import annotations

import json
import os
import tomllib
import xml.etree.ElementTree as ET
from contextlib import chdir
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from tyled.map.transform import FLAGS, FLIP_DIAGONAL, Transform
from tyled.tileset.factory import TilesetFactory
from tyled.tileset.grid import GridTileset
from tyled.tileset.names import NamedTiles, NamedTilesError, NineSlice, Piece, UnknownNameError, _unknown, read_tsx

BLANK = "."
TILED_VERSION = "1.10.2"
FORMAT_VERSION = "1.10"

PROJECT_KEYS = {"name", "type", "tilewidth", "tileheight", "layout", "tilesets", "fill", "legend", "layers"}
LAYER_KEYS = {"ground", "obstacles", "objects", "extra"}
ENTRY_KEYS = {"tile", "piece", "nine_slice", "rotate", "flip", "layer", "tileset", "name", "type", "walkable_layer"}
KINDS = ("tile", "piece", "nine_slice")


class MapError(ValueError):
    """A map project, layout or legend that can't be turned into a map; the message says where."""


@dataclass
class TilesetRef:
    """A tileset of the map: where its ``.tsx`` is, its first gid, and what it names."""

    name: str
    tsx: Path
    tilewidth: int
    tileheight: int
    span: int  # how many gids it takes
    named: NamedTiles
    firstgid: int = 1


@dataclass
class Entry:
    """A legend entry, resolved against the tilesets."""

    char: str
    kind: str  # 'tile', 'piece' or 'nine_slice'
    label: str  # for messages: "tile 'pine'"
    tileset: TilesetRef
    transform: Transform
    layer: str | None = None
    walkable_layer: str | None = None
    object_name: str | None = None
    object_type: str | None = None
    tile_id: int | None = None
    piece: Piece | None = None


@dataclass
class Area:
    """One layout file of a grid of areas: where it sits in the grid and in the whole map's cells."""

    name: str  # the layout file's name without folder or extension; the area's map is written as <name>.tmj
    file: str  # the layout file as the project gives it, for messages
    grid_row: int
    grid_column: int
    row: int  # the first row and column of the area, in cells of the whole map
    column: int
    width: int
    height: int


@dataclass
class Slice:
    """A nine-slice's rectangle in the layout: its entry, where it lies and which of its cells pieces stand on."""

    entry: Entry
    here: str  # for messages
    top: int
    left: int
    bottom: int
    right: int
    holes: list[tuple[int, int]]

    @property
    def width(self) -> int:
        return self.right - self.left + 1

    @property
    def height(self) -> int:
        return self.bottom - self.top + 1

    def on_edge(self, row: int, column: int) -> bool:
        """Whether a cell is on the rectangle's border but not at a corner, which is where a piece may stand."""
        on_row = row in (self.top, self.bottom) and self.left < column < self.right
        on_column = column in (self.left, self.right) and self.top < row < self.bottom
        return on_row or on_column


def _at(line: int, column: int) -> str:
    return f"line {line}, column {column}"


def _tsx_ref(path: Path, named: NamedTiles | None = None) -> TilesetRef:
    root = ET.parse(path).getroot()
    if root.tag != "tileset":
        raise MapError(f"{path} is not a tileset")
    ids = [int(t.get("id", "0")) for t in root.findall("tile")]
    span = max(int(root.get("tilecount", "0")), max(ids) + 1 if ids else 0)
    return TilesetRef(
        name=root.get("name", path.stem),
        tsx=path,
        tilewidth=int(root.get("tilewidth", "0")),
        tileheight=int(root.get("tileheight", "0")),
        span=span,
        named=named if named is not None else read_tsx(path),
    )


def _load_tileset(entry, base: Path) -> TilesetRef:
    if not isinstance(entry, str) or not entry:
        raise MapError(f"tilesets: each is a path to a tileset project (.toml) or a .tsx, not {entry!r}")
    path = (base / entry).resolve()
    if not path.exists():
        raise MapError(f"tilesets: {entry!r} doesn't exist (looked for {path})")
    if path.suffix == ".tsx":
        return _tsx_ref(path)
    if path.suffix != ".toml":
        raise MapError(f"tilesets: {entry!r} is neither a .toml project nor a .tsx")
    with open(path, "rb") as fh:
        config = tomllib.load(fh)
    if config.get("type") != "grid":
        raise MapError(
            f"tilesets: {entry!r} is a {config.get('type')!r} project; only grid projects name their tiles. "
            f"Bake it and give its .tsx instead"
        )
    # A project's paths are relative to the folder it is baked in, which is where its .tsx is written.
    with chdir(path.parent):
        tileset = TilesetFactory().produce(config, options={"save": False, "show": False, "rotation": False})
    assert isinstance(tileset, GridTileset)
    tsx = path.parent / f"{tileset.name}.tsx"
    if not tsx.exists():
        raise MapError(f"tilesets: {entry!r} has not been baked: {tsx} is missing (run `tyled bake {path.name}` first)")
    ref = _tsx_ref(tsx, named=tileset.named)
    ref.span = max(ref.span, tileset.tilecount)
    return ref


class MapProject:
    """What a map project file says, checked; `to_dict`, `to_json` and `write` make the ``.tmj``."""

    def __init__(self, config: Mapping, base: Path | str = ".", layout_text: str | None = None):
        base = Path(base)
        self.base = base
        unknown = set(config) - PROJECT_KEYS
        if unknown:
            raise MapError(f"unknown keys in the project: {sorted(unknown)}")
        if config.get("type", "map") != "map":
            raise MapError(f"type is {config['type']!r}, not 'map'")
        self.name = self._text(config, "name")
        self.tilewidth = self._size(config, "tilewidth", None)
        self.tileheight = self._size(config, "tileheight", self.tilewidth)

        layers = dict(config.get("layers", {}))
        if set(layers) - LAYER_KEYS:
            raise MapError(f"unknown keys in layers: {sorted(set(layers) - LAYER_KEYS)}")
        self.ground = layers.get("ground", "ground")
        self.obstacles = layers.get("obstacles", "obstacles")
        self.objects = layers.get("objects", "objects")
        self.extra = list(layers.get("extra", []))
        names = [self.ground, *self.extra, self.obstacles, self.objects]
        if not all(isinstance(n, str) and n for n in names):
            raise MapError("layers: every layer name is a non-empty string")
        if len(set(names)) != len(names):
            raise MapError(f"layers: the layer names must differ, but they are {names}")

        tilesets = config.get("tilesets")
        if not isinstance(tilesets, list) or not tilesets:
            raise MapError("tilesets: name at least one tileset")
        self.tilesets = [_load_tileset(entry, base) for entry in tilesets]
        firstgid = 1
        for ref in self.tilesets:
            ref.firstgid = firstgid
            firstgid += ref.span

        self.areas: list[Area] = []  # empty for a single layout; else the areas in reading order
        self.rows = self._read_layouts(config, base, layout_text)

        self.legend = {
            char: self._entry(char, value) for char, value in dict(config.get("legend", {})).items()
        }
        self.fill_gid = 0
        if "fill" in config:
            ref, found = self._find("tile", self._text(config, "fill"), None, "fill")
            self.fill_gid = ref.firstgid + found.id

    # -- the project file

    @staticmethod
    def _text(config, key):
        value = config.get(key)
        if not isinstance(value, str) or not value:
            raise MapError(f"{key}: give a non-empty string")
        return value

    @staticmethod
    def _size(config, key, default):
        value = config.get(key, default)
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise MapError(f"{key}: give a whole number of pixels, at least 1")
        return value

    # -- the layout

    def _read_layouts(self, config, base: Path, layout_text: str | None) -> list[str]:
        """The layout's rows: one file's, or the files of a grid of areas laid side by side."""
        layout = config.get("layout")
        if layout_text is not None or isinstance(layout, str):
            if layout_text is None:
                layout_text = self._read(base, self._text(config, "layout"))
            return self._parse_layout(layout_text)
        if not isinstance(layout, list) or not layout:
            raise MapError("layout: give the path of a layout file, or a grid of them: [['a.txt', 'b.txt'], ...]")
        grid = [list(row) if isinstance(row, list) else row for row in layout]
        for number, row in enumerate(grid, 1):
            if not isinstance(row, list) or not row or not all(isinstance(f, str) and f for f in row):
                raise MapError(
                    f"layout: row {number} of the grid of areas must be a list of layout file paths, not {row!r}"
                )
            if len(row) != len(grid[0]):
                raise MapError(
                    f"layout: row {number} of the grid of areas has {len(row)} areas, but row 1 has {len(grid[0])}"
                )
        seen: dict[str, str] = {}
        parsed = []
        for grid_row, files in enumerate(grid):
            parsed_row = []
            for grid_column, file in enumerate(files):
                stem = Path(file).stem
                if stem in seen:
                    raise MapError(
                        f"layout: the areas {seen[stem]!r} and {file!r} would both be written as {stem}.tmj; "
                        f"each area needs a layout file of its own with a different name"
                    )
                seen[stem] = file
                parsed_row.append(self._parse_layout(self._read(base, file), source=file))
            parsed.append(parsed_row)
        first = parsed[0][0]
        size = (len(first[0]), len(first))
        rows: list[str] = []
        for grid_row, files in enumerate(grid):
            for grid_column, file in enumerate(files):
                found = parsed[grid_row][grid_column]
                if (len(found[0]), len(found)) != size:
                    raise MapError(
                        f"layout: every area must be the same size, but {file!r} is {len(found[0])} × {len(found)} "
                        f"and {grid[0][0]!r} is {size[0]} × {size[1]}"
                    )
                self.areas.append(Area(
                    name=Path(file).stem, file=file, grid_row=grid_row, grid_column=grid_column,
                    row=grid_row * size[1], column=grid_column * size[0], width=size[0], height=size[1],
                ))
            for line in range(size[1]):
                rows.append("".join(parsed[grid_row][c][line] for c in range(len(files))))
        return rows

    @staticmethod
    def _read(base: Path, layout: str) -> str:
        path = base / layout
        if not path.exists():
            raise MapError(f"layout: {layout!r} doesn't exist (looked for {path.resolve()})")
        return path.read_text(encoding="utf-8-sig")

    @staticmethod
    def _parse_layout(text: str, source: str | None = None) -> list[str]:
        where = "layout" if source is None else f"layout {source!r}"
        rows = text.splitlines()
        while rows and rows[-1] == "":
            rows.pop()  # blank lines at the end are not a ragged line
        if not rows:
            raise MapError(f"{where}: the layout is empty")
        for number, row in enumerate(rows, 1):
            if len(row) != len(rows[0]):
                raise MapError(
                    f"{where}: line {number} has {len(row)} characters, but line 1 has {len(rows[0])}; "
                    f"every line must be the same length"
                )
        if not rows[0]:
            raise MapError(f"{where}: line 1 is empty")
        return rows

    def area_at(self, row: int, column: int) -> Area | None:
        """The area that holds the cell (row, column), counted from 0 over the whole map; None for a single layout."""
        for area in self.areas:
            if area.row <= row < area.row + area.height and area.column <= column < area.column + area.width:
                return area
        return None

    def _at(self, row: int, column: int, home: Area | None = None) -> str:
        """Where a cell (counted from 0 over the whole map) is, as a person counts: line and column, from 1.

        With areas it is the line and column in the area's own layout file, and the area is named, because
        that is the file a person edits. `home` says to count from that area even for a cell outside it.
        """
        area = home if home is not None else self.area_at(row, column)
        if area is None:
            return _at(row + 1, column + 1)
        return f"{_at(row - area.row + 1, column - area.column + 1)} of area {area.file!r}"

    @property
    def width(self) -> int:
        return len(self.rows[0])

    @property
    def height(self) -> int:
        return len(self.rows)

    # -- the legend

    def _find(self, kind: str | None, name: str, tileset: str | None, where: str):
        """Look a name up in the tilesets: `kind` is 'tile', 'piece', 'nine_slice' or None (any)."""
        pool = self.tilesets
        if tileset is not None:
            pool = [t for t in pool if t.name == tileset]
            if not pool:
                raise MapError(f"{where}: no tileset named {tileset!r} (the tilesets are {[t.name for t in self.tilesets]})")
        found = []
        for ref in pool:
            if kind in (None, "tile"):
                try:
                    found.append((ref, ref.named.tile(name)))
                except UnknownNameError:
                    pass
            if kind in (None, "piece", "nine_slice"):
                try:
                    piece = ref.named.piece(name)
                except UnknownNameError:
                    continue
                if kind != "nine_slice" or isinstance(piece, NineSlice):
                    found.append((ref, piece))
        if len(found) > 1:
            raise MapError(
                f"{where}: {name!r} is in more than one tileset ({', '.join(r.name for r, _ in found)}); "
                f"add tileset = '...' to say which"
            )
        if found:
            return found[0]
        known: list[str] = []
        for ref in pool:
            if kind in (None, "tile"):
                known += ref.named.names()
            if kind in (None, "piece"):
                known += ref.named.piece_names()
            if kind == "nine_slice":
                known += [p.name for p in ref.named.pieces() if isinstance(p, NineSlice)]
                if name in [p.name for r in pool for p in r.named.pieces()]:
                    raise MapError(f"{where}: {name!r} is a piece, not a nine-slice")
        label = {"nine_slice": "nine-slice", None: "tile or piece"}.get(kind, kind)
        raise MapError(f"{where}: {_unknown(label, name, known)}")

    def _entry(self, char: str, value) -> Entry:
        where = f"legend {char!r}"
        if not isinstance(char, str) or len(char) != 1:
            raise MapError(f"legend: {char!r} isn't a single character")
        if char == BLANK:
            raise MapError(f"legend: {BLANK!r} is the blank of the layout and can't be given a meaning")
        if isinstance(value, str):
            value = {"": value}
        if not isinstance(value, Mapping):
            raise MapError(f"{where}: give a name, or a table such as {{ tile = 'grass' }}")
        value = dict(value)
        unknown = set(value) - ENTRY_KEYS - {""}
        if unknown:
            raise MapError(f"{where}: unknown keys {sorted(unknown)}")
        given = [k for k in (*KINDS, "") if k in value]
        if len(given) != 1:
            raise MapError(f"{where}: give exactly one of tile, piece, nine_slice")
        kind = given[0]
        name = value[kind]
        if not isinstance(name, str) or not name:
            raise MapError(f"{where}: the name of the {kind or 'thing'} is a non-empty string")
        tileset_name = value.get("tileset")
        ref, thing = self._find(kind or None, name, tileset_name, where)
        if not kind:
            kind = "tile" if not isinstance(thing, Piece) else ("nine_slice" if isinstance(thing, NineSlice) else "piece")
        try:
            transform = Transform.of(value.get("rotate", 0), value.get("flip", ""))  # type: ignore[arg-type]
        except ValueError as error:
            raise MapError(f"{where}: {error}") from None
        layer = value.get("layer")
        walkable_layer = value.get("walkable_layer")
        for chosen in (layer, walkable_layer):
            if chosen is not None:
                self._check_layer(chosen, where)
        if walkable_layer == self.objects:
            raise MapError(f"{where}: walkable_layer can't be the objects layer")
        entry = Entry(
            char=char,
            kind=kind,
            label=f"{kind.replace('_', '-')} {name!r}",
            tileset=ref,
            transform=transform,
            layer=layer,
            walkable_layer=walkable_layer,
            object_name=value.get("name"),
            object_type=value.get("type"),
        )
        if kind == "tile":
            entry.tile_id = thing.id
        else:
            entry.piece = thing
        for key in ("name", "type"):
            if key in value and not isinstance(value[key], str):
                raise MapError(f"{where}: {key} is a string")
        if (entry.object_name is not None or entry.object_type is not None) and layer != self.objects:
            raise MapError(f"{where}: name and type are for objects; add layer = {self.objects!r}")
        if layer == self.objects:
            self._check_object(entry, where)
        return entry

    def _check_layer(self, layer, where):
        known = [self.ground, *self.extra, self.obstacles, self.objects]
        if layer not in known:
            raise MapError(f"{where}: there is no layer {layer!r}; the layers are {known} (more go in layers.extra)")

    def _check_object(self, entry: Entry, where: str):
        if entry.kind != "tile":
            raise MapError(f"{where}: only a tile can be an object, not a {entry.kind.replace('_', '-')}")
        if entry.transform.diagonal:
            raise MapError(f"{where}: an object can be flipped or turned 180 degrees, but not turned by 90 or 270")

    # -- the map

    def _tile_layer(self, entry: Entry, tile_id: int, where: str) -> str:
        """The layer for a tile: the entry's `layer`, else the tile's own, else by `walkable`.

        By `walkable` a blocking tile goes on the obstacles layer and any other on the entry's
        `walkable_layer`, which is the ground layer unless the entry says otherwise. A walkable tile
        with see-through parts (a gate's arch) is better on a layer above the ground, so that the
        ground's fill shows through instead of being replaced.
        """
        if entry.layer is not None:
            return entry.layer
        properties = {}
        named = entry.tileset.named.tile_by_id(tile_id)
        if named is not None:
            properties = named.properties
        layer = properties.get("layer")
        if layer is not None:
            self._check_layer(layer, f"{where}, tile {tile_id}'s layer property")
            return str(layer)
        if properties.get("walkable", True) is False:
            return self.obstacles
        return entry.walkable_layer if entry.walkable_layer is not None else self.ground

    def _compose(self):
        """Lay the whole map out: the data of every tile layer, and the tile objects with their cells.

        Returns ``(data, objects)``: `data` maps a layer name to its gids, row by row over the whole map,
        and `objects` lists ``(row, column, object)`` in reading order. Areas are cut from this, so that
        the merged map is the areas side by side by construction.
        """
        width, height = self.width, self.height
        tile_layers = [self.ground, *self.extra, self.obstacles]
        data = {name: [0] * (width * height) for name in tile_layers}
        if self.fill_gid:
            data[self.ground] = [self.fill_gid] * (width * height)
        objects: list[tuple[int, int, dict]] = []
        claimed: dict[tuple[int, int], tuple[str, str]] = {}  # cell -> (label, character) of the piece on it

        def put(entry: Entry, gid: int, row: int, column: int, where: str):
            tile_id = (gid & ~FLAGS) - entry.tileset.firstgid
            layer = self._tile_layer(entry, tile_id, where)
            if layer == self.objects:
                raise MapError(f"{where}: a piece or nine-slice can't put tiles on the objects layer")
            data[layer][row * width + column] = gid

        known = set(self.legend) | {BLANK}
        for row, text in enumerate(self.rows):
            for column, char in enumerate(text):
                if char not in known:
                    raise MapError(f"layout: {char!r} at {self._at(row, column)} is not in the legend")

        slices = self._slices()
        edges = {
            (r, c): found
            for found in slices
            for r in range(found.top, found.bottom + 1)
            for c in range(found.left, found.right + 1)
            if found.on_edge(r, c)
        }
        for row, text in enumerate(self.rows):
            for column, char in enumerate(text):
                if char == BLANK:
                    continue
                entry = self.legend[char]
                if entry.kind == "nine_slice":
                    continue  # placed below, once the pieces that stand on its edges are known
                here = f"{entry.label} ({char!r} at {self._at(row, column)})"
                if claimed.get((row, column), (None, None))[1] == char:
                    continue  # the anchor's footprint already took this one
                if entry.kind == "tile":
                    self._place_tile(entry, row, column, here, put, objects)
                else:
                    self._place_piece(entry, row, column, here, put, claimed, edges)
        for found in slices:
            self._place_nine_slice(found, put, claimed)
        return data, objects

    def _frame(self, width, height, data, objects, folder) -> dict:
        """A map as Tiled's JSON structure, from the tile layers' data and the objects `(row, column, object)`."""
        layers = []
        layer_id = 0
        for name in [self.ground, *self.extra, self.obstacles]:
            layer_id += 1
            layers.append({
                "data": data[name], "height": height, "id": layer_id, "name": name, "opacity": 1,
                "type": "tilelayer", "visible": True, "width": width, "x": 0, "y": 0,
            })
        layer_id += 1
        listed = []
        for index, (_, _, obj) in enumerate(objects, 1):
            listed.append(dict(sorted({**obj, "id": index}.items())))
        layers.append({
            "draworder": "topdown", "id": layer_id, "name": self.objects,
            "objects": listed, "opacity": 1,
            "type": "objectgroup", "visible": True, "x": 0, "y": 0,
        })
        return {
            "compressionlevel": -1,
            "height": height,
            "infinite": False,
            "layers": layers,
            "nextlayerid": layer_id + 1,
            "nextobjectid": len(objects) + 1,
            "orientation": "orthogonal",
            "renderorder": "right-down",
            "tiledversion": TILED_VERSION,
            "tileheight": self.tileheight,
            "tilesets": [{"firstgid": t.firstgid, "source": self._source(t, folder)} for t in self.tilesets],
            "tilewidth": self.tilewidth,
            "type": "map",
            "version": FORMAT_VERSION,
            "width": width,
        }

    def to_dict(self, folder: Path | str | None = None) -> dict:
        """The map as Tiled's JSON structure, with every key in the order Tiled writes it.

        Tileset sources are written relative to `folder` (where the ``.tmj`` will be), as Tiled reads them.
        With areas this is the merged map of the whole town; `area_dicts` has the areas.
        """
        data, objects = self._compose()
        return self._frame(self.width, self.height, data, objects, folder)

    def area_dicts(self, folder: Path | str | None = None) -> list[tuple[Area, dict]]:
        """Each area as a map of its own, in the grid's reading order; empty for a single layout."""
        data, objects = self._compose()
        found = []
        for area in self.areas:
            cut = {}
            for name, cells in data.items():
                cut[name] = [
                    gid
                    for r in range(area.row, area.row + area.height)
                    for gid in cells[r * self.width + area.column:r * self.width + area.column + area.width]
                ]
            inside = []
            for row, column, obj in objects:
                if area.row <= row < area.row + area.height and area.column <= column < area.column + area.width:
                    moved = {**obj, "x": obj["x"] - area.column * self.tilewidth,
                             "y": obj["y"] - area.row * self.tileheight}
                    inside.append((row, column, moved))
            found.append((area, self._frame(area.width, area.height, cut, inside, folder)))
        return found

    def world_dict(self) -> dict:
        """The Tiled world that places the areas' maps side by side, as Tiled's JSON structure.

        Each map is named by its file beside the ``.world``, and placed and sized in pixels.
        """
        if not self.areas:
            raise MapError("a world is made of areas: give the layout as a grid of layout files")
        return {
            "maps": [
                {
                    "fileName": f"{area.name}.tmj",
                    "height": area.height * self.tileheight,
                    "width": area.width * self.tilewidth,
                    "x": area.column * self.tilewidth,
                    "y": area.row * self.tileheight,
                }
                for area in self.areas
            ],
            "onlyShowAdjacentMaps": False,
            "type": "world",
        }

    @staticmethod
    def _source(ref: TilesetRef, folder) -> str:
        path = os.path.relpath(ref.tsx, Path(folder).resolve()) if folder is not None else str(ref.tsx)
        return Path(path).as_posix()

    def _place_tile(self, entry, row, column, here, put, objects):
        gid = entry.transform.apply_to_gid(entry.tileset.firstgid + entry.tile_id)
        layer = self._tile_layer(entry, entry.tile_id, here)
        if layer != self.objects:
            put(entry, gid, row, column, here)
            return
        if gid & FLIP_DIAGONAL:
            raise MapError(f"{here}: an object can be flipped or turned 180 degrees, but not turned by 90 or 270")
        named = entry.tileset.named.tile_by_id(entry.tile_id)
        properties = named.properties if named is not None else {}
        kind = properties.get("kind", "")
        tile_name = named.name if named is not None and named.name is not None else ""
        objects.append((row, column, {
            "class": entry.object_type if entry.object_type is not None else str(kind),
            "gid": gid,
            "height": entry.tileset.tileheight,
            "name": entry.object_name if entry.object_name is not None else tile_name,
            "rotation": 0,
            "type": entry.object_type if entry.object_type is not None else str(kind),
            "visible": True,
            "width": entry.tileset.tilewidth,
            "x": column * self.tilewidth,
            "y": (row + 1) * self.tileheight,  # Tiled puts a tile object's position at its bottom left
        }))

    def _gids(self, entry: Entry, grid):
        first = entry.tileset.firstgid
        return tuple(tuple(None if i is None else first + i for i in r) for r in grid)

    def _claim(self, entry, grid, anchor, row, column, here, claimed, edges):
        """Check where a grid of cells would lie and claim it; returns the cells as (row, column, gid).

        A cell may hold the piece's own character or the blank; or, on the edge of a nine-slice, the
        nine-slice's character, which the piece then replaces.
        """
        top, left = row - anchor[1], column - anchor[0]
        home = self.area_at(row, column)
        cells = []
        for r, cells_row in enumerate(grid):
            for c, gid in enumerate(cells_row):
                if gid is None:
                    continue
                line, col = top + r, left + c
                if not (0 <= line < self.height and 0 <= col < self.width):
                    size = f"{self.width} × {self.height}"
                    raise MapError(
                        f"{here} runs off the map: its cell for {self._at(line, col, home)} is outside "
                        f"the {size} map" if home is None else
                        f"{here} runs off the map: its cell for {self._at(line, col, home)} is outside "
                        f"the {size} cells of all the areas together"
                    )
                there = self.area_at(line, col)
                if there is not home:
                    assert home is not None and there is not None
                    raise MapError(
                        f"{here} crosses the edge of its area: it reaches {self._at(line, col)}, outside "
                        f"area {home.file!r}, where its anchor is; a piece must lie in one area"
                    )
                found = self.rows[line][col]
                on_slice = edges.get((line, col))
                if found != entry.char and found != BLANK and not (
                    on_slice is not None and on_slice.entry.char == found
                ):
                    other = self.legend[found].label if found in self.legend else repr(found)
                    raise MapError(
                        f"{here} covers {self._at(line, col)}, where the layout has {found!r} "
                        f"({other}); a piece's other cells must be {entry.char!r} or {BLANK!r}"
                    )
                if (line, col) in claimed:
                    raise MapError(f"{here} overlaps {claimed[(line, col)][0]} at {self._at(line, col)}")
                cells.append((line, col, gid))
        for line, col, _ in cells:
            claimed[(line, col)] = (here, entry.char)
        return cells

    def _place_piece(self, entry, row, column, here, put, claimed, edges):
        grid, anchor = entry.transform.apply_to_grid(self._gids_of(entry), entry.piece.anchor)
        for line, col, gid in self._claim(entry, grid, anchor, row, column, here, claimed, edges):
            put(entry, gid, line, col, here)

    def _gids_of(self, entry):
        return self._gids(entry, entry.piece.ids)

    def _slices(self) -> list[Slice]:
        """The nine-slices of the layout: each rectangle of a nine-slice's character, checked.

        A rectangle is the cells of one character that touch, and must be full, except that a piece may
        stand on an edge of it (not at a corner): a gate or doorway in a wall. Those cells hold the
        piece's character or the blank, and are the "holes" that a piece must fill. Nothing may be in the
        rectangle's centre.
        """
        found: list[Slice] = []
        taken: set[tuple[int, int]] = set()
        for row, text in enumerate(self.rows):
            for column, char in enumerate(text):
                entry = self.legend.get(char)
                if entry is None or entry.kind != "nine_slice" or (row, column) in taken:
                    continue
                found.append(self._slice(entry, row, column, taken))
        return found

    def _slice(self, entry: Entry, row: int, column: int, taken: set) -> Slice:
        char = entry.char
        here = f"{entry.label} ({char!r} at {self._at(row, column)})"
        # The first cell met, in reading order, is the top left of the rectangle if there is one.
        seen = {(row, column)}
        todo = [(row, column)]
        while todo:
            r, c = todo.pop()
            for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                if 0 <= nr < self.height and 0 <= nc < self.width and (nr, nc) not in seen \
                        and self.rows[nr][nc] == char:
                    seen.add((nr, nc))
                    todo.append((nr, nc))
        taken |= seen
        top, bottom = min(r for r, _ in seen), max(r for r, _ in seen)
        left, right = min(c for _, c in seen), max(c for _, c in seen)
        corners = [(top, left), (top, right), (bottom, left), (bottom, right)]
        if self.areas:
            areas = []
            for cell in sorted(seen | set(corners)):
                area = self.area_at(*cell)
                if area not in areas:
                    areas.append(area)
            if len(areas) > 1:
                raise MapError(
                    f"{here} crosses the edge of its area: its cells are in areas "
                    f"{', '.join(repr(a.file) for a in areas)}; a nine-slice must lie in one area "
                    f"(leave a {BLANK!r} between two rectangles that touch at an area's edge)"
                )
        result = Slice(entry, here, top, left, bottom, right, [])
        outside = [
            (r, c) for r in range(top, bottom + 1) for c in range(left, right + 1) if (r, c) not in seen
        ]
        for r, c in outside:
            found = self.rows[r][c]
            other = self.legend.get(found)
            if not result.on_edge(r, c):
                if other is not None and other.kind == "piece":
                    raise MapError(
                        f"{here} has {other.label} ({found!r} at {self._at(r, c)}) inside it; a piece may stand "
                        f"on a nine-slice's edge, but not in its centre or a corner"
                    )
                break
            if found != BLANK and (other is None or other.kind != "piece"):
                break
            result.holes.append((r, c))
        else:
            return result
        raise MapError(
            f"{here} isn't a rectangle: the {char!r} cells joined to it cover "
            f"{self._at(top, left)} to {self._at(bottom, right)} but only {len(seen)} of the "
            f"{result.width * result.height} cells there; a nine-slice needs a full rectangle "
            f"(only a piece may stand on its edge)"
        )

    def _place_nine_slice(self, found: Slice, put, claimed):
        entry, here = found.entry, found.here
        grid, anchor = entry.transform.apply_to_grid(self._gids_of(entry), entry.piece.anchor)
        stretched = NineSlice(entry.piece.name, grid, anchor)
        try:
            cells = stretched.stretch(found.width, found.height)
        except NamedTilesError as error:
            raise MapError(f"{here}: {error}") from None
        for r, cells_row in enumerate(cells):
            for c, gid in enumerate(cells_row):
                line, col = found.top + r, found.left + c
                if (line, col) in claimed:
                    # A piece stands here, on the edge: it replaces the edge's tile.
                    continue
                if (line, col) in found.holes:
                    raise MapError(
                        f"{here} has a hole at {self._at(line, col)} that no piece fills; "
                        f"its edge is open there"
                    )
                put(entry, gid, line, col, here)

    # -- the files

    @staticmethod
    def _json(tree: dict) -> str:
        """``.tmj`` text: indented JSON with each row of a layer's tiles on a line of its own."""
        rows = {}
        for layer in tree["layers"]:
            if layer["type"] == "tilelayer":
                placeholder = f"@@{layer['id']}@@"
                width = layer["width"]
                lines = [",".join(str(g) for g in layer["data"][i:i + width]) for i in range(0, len(layer["data"]), width)]
                rows[placeholder] = "[\n" + ",\n".join("    " + ln for ln in lines) + "\n   ]"
                layer["data"] = placeholder
        text = json.dumps(tree, indent=1, ensure_ascii=False)
        for placeholder, replacement in rows.items():
            text = text.replace(json.dumps(placeholder), replacement)
        return text + "\n"

    def to_json(self, folder: Path | str | None = None) -> str:
        """The ``.tmj`` text of the map (the merged map, with areas)."""
        return self._json(self.to_dict(folder))

    def to_world_json(self) -> str:
        """The ``.world`` text: indented JSON, as Tiled writes one."""
        return json.dumps(self.world_dict(), indent=4, sort_keys=True) + "\n"

    def write(self, output: Path | str | None = None, merged: bool = False) -> Path:
        """Write the map and return the path of the main file; `write_files` has all of them."""
        return self.write_files(output, merged)[0]

    def write_files(self, output: Path | str | None = None, merged: bool = False) -> list[Path]:
        """Write what the project makes and return the paths written, the main file first.

        A single layout is one ``.tmj``: `output` if given, else ``<name>.tmj`` here.

        A grid of areas is a ``.world`` (`output` if given, else ``<name>.world`` here) and a ``<area>.tmj``
        beside it for each area, named after its layout file. With `merged` there is also ``<name>.tmj``
        beside them: the whole town as one map, for programs that load a single map.
        """
        if not self.areas:
            path = Path(output) if output is not None else Path(f"{self.name}.tmj")
            files = {path: self.to_json(path.parent)}  # first, so that a bad layout leaves no half-written file
        else:
            path = Path(output) if output is not None else Path(f"{self.name}.world")
            if path.suffix != ".world":
                raise MapError(f"output: a grid of areas is written as a Tiled world, so {str(path)!r} should end in .world")
            folder = path.parent
            files = {path: self.to_world_json()}
            for area, tree in self.area_dicts(folder):
                files[folder / f"{area.name}.tmj"] = self._json(tree)
            if merged:
                whole = folder / f"{self.name}.tmj"
                if whole in files:
                    raise MapError(
                        f"the merged map would be written over the area {self.name!r}'s: "
                        f"rename the project or that area's layout file"
                    )
                files[whole] = self.to_json(folder)
        for target, text in files.items():
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
        return list(files)


def _project(project) -> MapProject:
    if isinstance(project, (str, Path)):
        path = Path(project)
        with open(path, "rb") as fh:
            config = tomllib.load(fh)
        return MapProject(config, base=path.parent)
    if isinstance(project, MapProject):
        return project
    return MapProject(project)


def build_all(project, output: Path | str | None = None, merged: bool = False) -> list[Path]:
    """Build a map and write it; returns every path written, the main file first.

    `project` is the path of a map project file (TOML), a dict of what such a file holds (its paths then
    count from the current folder), or a `MapProject`. `output` is the file to write; by default it is
    ``<name>.tmj`` in the current folder, the way a bake writes its ``.tsx`` there.

    For a layout that is a grid of areas the main file is the Tiled world (``<name>.world`` by default,
    or `output`), and each area's map is written beside it; with `merged` the whole town as one map
    (``<name>.tmj``) is written too.
    """
    return _project(project).write_files(output, merged)


def build(project, output: Path | str | None = None, merged: bool = False) -> Path:
    """Build a map and write it as a ``.tmj`` (a grid of areas: the ``.world``); returns the main path written.

    See `build_all` for the arguments, and for the paths of the other files an area layout writes.
    """
    return build_all(project, output, merged)[0]

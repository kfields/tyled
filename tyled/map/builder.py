"""A map project: tilesets, a layout, a legend; and the ``.tmj`` they make.

A map project file (TOML) says::

    name = 'town'                     # the map is written as town.tmj
    tilewidth = 16
    tileheight = 16
    layout = 'town.txt'               # one character a tile
    tilesets = ['tiny-town.toml']     # step 1's projects, or .tsx files; firstgids follow their order
    fill = 'grass'                    # a tile laid on the whole ground layer first (optional)

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
  the same character or ``.`` and lie on the map, and not on another piece or nine-slice;
* a **nine-slice** takes the rectangle of cells that hold its character, in one block, and is stretched
  to it.

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

        if layout_text is None:
            layout = self._text(config, "layout")
            path = base / layout
            if not path.exists():
                raise MapError(f"layout: {layout!r} doesn't exist (looked for {path.resolve()})")
            layout_text = path.read_text(encoding="utf-8-sig")
        self.rows = self._parse_layout(layout_text)

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

    @staticmethod
    def _parse_layout(text: str) -> list[str]:
        rows = text.splitlines()
        while rows and rows[-1] == "":
            rows.pop()  # blank lines at the end are not a ragged line
        if not rows:
            raise MapError("layout: the layout is empty")
        for number, row in enumerate(rows, 1):
            if len(row) != len(rows[0]):
                raise MapError(
                    f"layout: line {number} has {len(row)} characters, but line 1 has {len(rows[0])}; "
                    f"every line must be the same length"
                )
        if not rows[0]:
            raise MapError("layout: line 1 is empty")
        return rows

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

    def to_dict(self, folder: Path | str | None = None) -> dict:
        """The map as Tiled's JSON structure, with every key in the order Tiled writes it.

        Tileset sources are written relative to `folder` (where the ``.tmj`` will be), as Tiled reads them.
        """
        width, height = self.width, self.height
        tile_layers = [self.ground, *self.extra, self.obstacles]
        data = {name: [0] * (width * height) for name in tile_layers}
        if self.fill_gid:
            data[self.ground] = [self.fill_gid] * (width * height)
        objects: list[dict] = []
        claimed: dict[tuple[int, int], tuple[str, str]] = {}  # cell -> (label, character) of what covers it

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
                    raise MapError(f"layout: {char!r} at {_at(row + 1, column + 1)} is not in the legend")

        for row, text in enumerate(self.rows):
            for column, char in enumerate(text):
                if char == BLANK:
                    continue
                entry = self.legend[char]
                here = f"{entry.label} ({char!r} at {_at(row + 1, column + 1)})"
                if claimed.get((row, column), (None, None))[1] == char:
                    continue  # the anchor's footprint already took this one
                if entry.kind == "tile":
                    self._place_tile(entry, row, column, here, put, objects)
                elif entry.kind == "piece":
                    self._place_piece(entry, row, column, here, put, claimed)
                else:
                    self._place_nine_slice(entry, row, column, here, put, claimed)

        layers = []
        layer_id = 0
        for name in tile_layers:
            layer_id += 1
            layers.append({
                "data": data[name], "height": height, "id": layer_id, "name": name, "opacity": 1,
                "type": "tilelayer", "visible": True, "width": width, "x": 0, "y": 0,
            })
        layer_id += 1
        for index, obj in enumerate(objects, 1):
            obj["id"] = index
        layers.append({
            "draworder": "topdown", "id": layer_id, "name": self.objects,
            "objects": [dict(sorted(o.items())) for o in objects], "opacity": 1,
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
        objects.append({
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
        })

    def _gids(self, entry: Entry, grid):
        first = entry.tileset.firstgid
        return tuple(tuple(None if i is None else first + i for i in r) for r in grid)

    def _claim(self, entry, grid, anchor, row, column, here, claimed):
        """Check where a grid of cells would lie and claim it; returns the cells as (row, column, gid)."""
        top, left = row - anchor[1], column - anchor[0]
        cells = []
        for r, cells_row in enumerate(grid):
            for c, gid in enumerate(cells_row):
                if gid is None:
                    continue
                line, col = top + r, left + c
                if not (0 <= line < self.height and 0 <= col < self.width):
                    raise MapError(
                        f"{here} runs off the map: its cell for {_at(line + 1, col + 1)} is outside "
                        f"the {self.width} × {self.height} map"
                    )
                found = self.rows[line][col]
                if found != entry.char and found != BLANK:
                    other = self.legend[found].label if found in self.legend else repr(found)
                    raise MapError(
                        f"{here} covers {_at(line + 1, col + 1)}, where the layout has {found!r} "
                        f"({other}); a piece's other cells must be {entry.char!r} or {BLANK!r}"
                    )
                if (line, col) in claimed:
                    raise MapError(f"{here} overlaps {claimed[(line, col)][0]} at {_at(line + 1, col + 1)}")
                cells.append((line, col, gid))
        for line, col, _ in cells:
            claimed[(line, col)] = (here, entry.char)
        return cells

    def _place_piece(self, entry, row, column, here, put, claimed):
        grid, anchor = entry.transform.apply_to_grid(self._gids_of(entry), entry.piece.anchor)
        for line, col, gid in self._claim(entry, grid, anchor, row, column, here, claimed):
            put(entry, gid, line, col, here)

    def _gids_of(self, entry):
        return self._gids(entry, entry.piece.ids)

    def _place_nine_slice(self, entry, row, column, here, put, claimed):
        # The first cell met, in reading order, is the top left of the rectangle if there is one.
        seen = {(row, column)}
        todo = [(row, column)]
        while todo:
            r, c = todo.pop()
            for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                if 0 <= nr < self.height and 0 <= nc < self.width and (nr, nc) not in seen \
                        and self.rows[nr][nc] == entry.char:
                    seen.add((nr, nc))
                    todo.append((nr, nc))
        rows = [r for r, _ in seen]
        columns = [c for _, c in seen]
        top, bottom, left, right = min(rows), max(rows), min(columns), max(columns)
        width, height = right - left + 1, bottom - top + 1
        if width * height != len(seen):
            raise MapError(
                f"{here} isn't a rectangle: the {entry.char!r} cells joined to it cover "
                f"{_at(top + 1, left + 1)} to {_at(bottom + 1, right + 1)} but only {len(seen)} of the "
                f"{width * height} cells there; a nine-slice needs a full rectangle"
            )
        grid, anchor = entry.transform.apply_to_grid(self._gids_of(entry), entry.piece.anchor)
        stretched = NineSlice(entry.piece.name, grid, anchor)
        try:
            cells = stretched.stretch(width, height)
        except NamedTilesError as error:
            raise MapError(f"{here}: {error}") from None
        placed = [(top + r, left + c, gid) for r, cells_row in enumerate(cells) for c, gid in enumerate(cells_row)]
        for line, col, gid in placed:
            if (line, col) in claimed:
                raise MapError(f"{here} overlaps {claimed[(line, col)][0]} at {_at(line + 1, col + 1)}")
        for line, col, gid in placed:
            claimed[(line, col)] = (here, entry.char)
            put(entry, gid, line, col, here)

    # -- the file

    def to_json(self, folder: Path | str | None = None) -> str:
        """The ``.tmj`` text: indented JSON with each row of a layer's tiles on a line of its own."""
        tree = self.to_dict(folder)
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

    def write(self, output: Path | str | None = None) -> Path:
        """Write the ``.tmj`` (to `output`, else ``<name>.tmj`` here) and return its path."""
        path = Path(output) if output is not None else Path(f"{self.name}.tmj")
        text = self.to_json(path.parent)  # first, so that a bad layout leaves no half-written file
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        return path


def build(project, output: Path | str | None = None) -> Path:
    """Build a map and write it as a ``.tmj``; returns the path written.

    `project` is the path of a map project file (TOML), a dict of what such a file holds (its paths then
    count from the current folder), or a `MapProject`. `output` is the file to write; by default it is
    ``<name>.tmj`` in the current folder, the way a bake writes its ``.tsx`` there.
    """
    if isinstance(project, (str, Path)):
        path = Path(project)
        with open(path, "rb") as fh:
            config = tomllib.load(fh)
        project = MapProject(config, base=path.parent)
    elif not isinstance(project, MapProject):
        project = MapProject(project)
    return project.write(output)

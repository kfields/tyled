"""Names, properties and pieces for the tiles of a tileset.

Everything that uses a tileset (a text layout, a generator, an agent) should say "well", not "tile
104". This module holds what a tileset knows about its tiles by name:

* the tiles that have a name, and the typed properties of every tile (``walkable = false``);
* the pieces: named rectangles of tiles (a house, a tower), each with an anchor;
* the nine-slices: a kind of piece, three by three tiles (corners, edges, centre), that a map can
  stretch to any size by repeating the edges and the centre (a walled courtyard, a patch of dirt).

It is plain data with no image in it, so it can come from two places and give the same answer:
from a project file (`NamedTiles.from_spec`) while a tileset is built, and from a ``.tsx`` that tyled
wrote earlier (`read_tsx`). The ``.tsx`` is where Tiled and tyled both see the names, so reading it back
is the check that what was written means what was meant.

How the ``.tsx`` holds it:

* a tile's name is its custom property ``name``, which Tiled shows in its Properties panel;
* the other properties are Tiled custom properties with Tiled's types (string, int, float, bool);
* a piece is two custom properties on the *tileset* (Tiled shows those too): ``piece:<name>``, the grid
  of tile ids, rows separated by ``;`` and ids by ``,`` (``-`` for an empty cell), and
  ``anchor:<name>``, the ``column,row`` of the anchor tile inside the piece. A nine-slice is a piece
  with a third property, ``kind:<name>`` = ``nine_slice``; a piece without one is a plain piece, so
  files written before nine-slices existed read as they always did.

Tiled's stamps were passed over because Tiled keeps them in its own preferences, not in the tileset
or the project, so tyled could not see them and they would not travel with the ``.tsx``. A file of
tyled's own beside the ``.tsx`` would be invisible to Tiled and could drift from it.
"""

from __future__ import annotations

import difflib
import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Iterable, Mapping

NAME_PROPERTY = "name"
PIECE_PREFIX = "piece:"
ANCHOR_PREFIX = "anchor:"
KIND_PREFIX = "kind:"
NINE_SLICE = "nine_slice"

# How many near misses an error offers when a name is misspelled.
SUGGESTIONS = 3


class NamedTilesError(ValueError):
    """A project file or a lookup asked for something the tileset's names don't allow."""


class UnknownNameError(NamedTilesError, KeyError):
    """A name that no tile (or piece) has; the message suggests the nearest names."""

    def __str__(self):
        # KeyError would show the message in quotes, repr-style.
        return str(self.args[0])


def _unknown(kind: str, name: str, known: Iterable[str]) -> UnknownNameError:
    known = sorted(known)
    near = difflib.get_close_matches(name, known, n=SUGGESTIONS, cutoff=0.5)
    message = f"no {kind} named {name!r}"
    if near:
        message += "; did you mean " + " or ".join(repr(n) for n in near) + "?"
    elif not known:
        message += f" (this tileset has no {kind}s)"
    return UnknownNameError(message)


@dataclass(frozen=True)
class NamedTile:
    """One tile: its id, its name (None if it has none) and its properties, defaults included."""

    id: int
    name: str | None
    properties: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class Piece:
    """A named rectangle of tiles.

    `ids` is the grid of tile ids, row by row from the top; a cell is None where the piece has a gap.
    `anchor` is the (column, row) inside the piece of the tile that a layout's character stands for.
    """

    name: str
    ids: tuple[tuple[int | None, ...], ...]
    anchor: tuple[int, int] = (0, 0)

    @property
    def width(self) -> int:
        return len(self.ids[0])

    @property
    def height(self) -> int:
        return len(self.ids)

    @property
    def anchor_id(self) -> int | None:
        column, row = self.anchor
        return self.ids[row][column]


@dataclass(frozen=True)
class NineSlice(Piece):
    """A piece of three by three tiles that can be stretched: corners, edges and a centre.

    It is for things that have a border and an inside, seen from above: a walled courtyard, a patch of
    dirt in grass. A map asks for the size it needs and gets the corners once each, the edges repeated
    along the sides and the centre repeated in between (`stretch`). The anchor is the centre tile unless
    the project file says otherwise.
    """

    anchor: tuple[int, int] = (1, 1)

    def __post_init__(self):
        if len(self.ids) != 3 or any(len(row) != 3 for row in self.ids):
            raise NamedTilesError(f"nine-slice {self.name!r} must be three rows of three tiles")
        if any(cell is None for row in self.ids for cell in row):
            raise NamedTilesError(f"nine-slice {self.name!r} can't have gaps")

    def stretch(self, width: int, height: int) -> tuple[tuple[int, ...], ...]:
        """The grid of tile ids for a `width` by `height` area, row by row from the top.

        The smallest size is 2 by 2, the four corners; each tile beyond that repeats the edge or the
        centre tile of its row and column. Sizes of 3 by 3 give the piece itself.
        """
        if width < 2 or height < 2:
            raise NamedTilesError(
                f"nine-slice {self.name!r} can't be {width} × {height}: the smallest size is 2 × 2 (the corners)"
            )
        columns = [0] + [1] * (width - 2) + [2]
        rows = [0] + [1] * (height - 2) + [2]
        return tuple(tuple(self.ids[r][c] for c in columns) for r in rows)  # type: ignore[misc]


class NamedTiles:
    """Lookup of tiles by name and by id, and of pieces by name."""

    def __init__(self, tiles: Iterable[NamedTile] = (), pieces: Iterable[Piece] = ()):
        self._by_id: dict[int, NamedTile] = {}
        self._by_name: dict[str, NamedTile] = {}
        self._pieces: dict[str, Piece] = {}
        for tile in sorted(tiles, key=lambda t: t.id):
            if tile.id in self._by_id:
                raise NamedTilesError(f"tile {tile.id} is listed twice")
            self._by_id[tile.id] = tile
            if tile.name is not None:
                if tile.name in self._by_name:
                    raise NamedTilesError(
                        f"the name {tile.name!r} is used for tiles {self._by_name[tile.name].id} and {tile.id}"
                    )
                self._by_name[tile.name] = tile
        for piece in pieces:
            if piece.name in self._pieces:
                raise NamedTilesError(f"there are two pieces named {piece.name!r}")
            if piece.name in self._by_name:
                # A layout's legend says one word for one thing; a tile and a piece may not share it.
                raise NamedTilesError(f"{piece.name!r} names both a tile and a piece")
            self._pieces[piece.name] = piece

    # -- tiles

    def tile(self, name: str) -> NamedTile:
        """The tile called `name`; a misspelled name raises UnknownNameError with the nearest names."""
        try:
            return self._by_name[name]
        except KeyError:
            raise _unknown("tile", name, self._by_name) from None

    def tile_by_id(self, id: int) -> NamedTile | None:
        """The tile with this id if it has a name or properties, else None."""
        return self._by_id.get(id)

    def names(self) -> list[str]:
        """Every tile name, in the order of the tile ids."""
        return [t.name for t in self._by_id.values() if t.name is not None]

    def tiles(self) -> list[NamedTile]:
        """Every tile that has a name or properties, in the order of their ids."""
        return list(self._by_id.values())

    # -- pieces

    def piece(self, name: str) -> Piece:
        """The piece called `name`; a misspelled name raises UnknownNameError with the nearest names.

        A nine-slice is a piece too, so it is found here (as a `NineSlice`).
        """
        try:
            return self._pieces[name]
        except KeyError:
            raise _unknown("piece", name, self._pieces) from None

    def nine_slice(self, name: str) -> NineSlice:
        """The nine-slice called `name`; a piece that is not a nine-slice is an error saying so."""
        piece = self.piece(name)
        if not isinstance(piece, NineSlice):
            raise NamedTilesError(f"{name!r} is a piece, not a nine-slice")
        return piece

    def piece_names(self) -> list[str]:
        return list(self._pieces)

    def pieces(self) -> list[Piece]:
        return list(self._pieces.values())

    # -- from a project file

    @classmethod
    def from_spec(
        cls,
        *,
        columns: int,
        tilecount: int,
        tiles: Iterable[Mapping] = (),
        pieces: Iterable[Mapping] = (),
        defaults: Mapping[str, object] | None = None,
    ) -> "NamedTiles":
        """Build from the tables of a project file.

        `tiles` are ``[[tiles]]`` entries: one of ``id``, ``at = [column, row]`` or (for properties
        only, no name) ``region = [column, row, width, height]``, plus an optional ``name`` and an
        optional ``properties`` table. `defaults` are the properties every tile starts with.
        `pieces` are ``[[pieces]]`` entries: a ``name``, a ``region`` or ``rows`` of tile names (or ids),
        an optional ``anchor = [column, row]`` and an optional ``kind`` (``'nine_slice'`` for a piece of
        three by three tiles that stretches; the anchor then defaults to the centre).
        """
        defaults = dict(defaults or {})
        for key, value in defaults.items():
            _check_property(key, value, "defaults")

        names: dict[int, str] = {}
        props: dict[int, dict[str, object]] = {}
        for index, entry in enumerate(tiles, 1):
            where = f"tiles entry {index}"
            entry = dict(entry)
            unknown = set(entry) - {"name", "id", "at", "region", "properties"}
            if unknown:
                raise NamedTilesError(f"{where}: unknown keys {sorted(unknown)}")
            found = [k for k in ("id", "at", "region") if k in entry]
            if len(found) != 1:
                raise NamedTilesError(f"{where}: give exactly one of id, at, region")
            if found[0] == "id":
                ids = [_tile_id(entry["id"], tilecount, where)]
            elif found[0] == "at":
                column, row = _pair(entry["at"], "at", where)
                ids = [_cell(column, row, columns, tilecount, where)]
            else:
                ids = [i for r in _region(entry["region"], columns, tilecount, where) for i in r]
            name = entry.get("name")
            if name is not None:
                _check_name(name, where)
                if len(ids) != 1:
                    raise NamedTilesError(f"{where}: a name goes with one tile, not a region")
                if ids[0] in names and names[ids[0]] != name:
                    raise NamedTilesError(f"{where}: tile {ids[0]} is already named {names[ids[0]]!r}")
                names[ids[0]] = name
            properties = entry.get("properties", {})
            if not isinstance(properties, Mapping):
                raise NamedTilesError(f"{where}: properties must be a table")
            for key, value in properties.items():
                _check_property(key, value, where)
            for id in ids:
                props.setdefault(id, {}).update(properties)

        made = []
        for id in sorted(set(names) | set(props)):
            made.append(NamedTile(id, names.get(id), {**defaults, **props.get(id, {})}))
        if defaults:
            # Every tile carries the defaults, so an unmentioned tile still has `walkable = true`.
            have = {t.id for t in made}
            made.extend(NamedTile(i, None, dict(defaults)) for i in range(tilecount) if i not in have)
        by_name = {t.name: t.id for t in made if t.name is not None}  # for the pieces below

        built = []
        for index, entry in enumerate(pieces, 1):
            built.append(_piece_from_spec(entry, index, by_name, columns, tilecount))
        # Duplicate names are reported by the constructor, in one place for both ways in.
        return cls(made, built)


def _check_name(name, where) -> str:
    if not isinstance(name, str) or not name or name != name.strip():
        raise NamedTilesError(f"{where}: a name is a non-empty string with no spaces around it")
    return name


def _check_property(key, value, where):
    if not isinstance(key, str) or not key:
        raise NamedTilesError(f"{where}: a property name is a non-empty string")
    if key == NAME_PROPERTY:
        raise NamedTilesError(f"{where}: 'name' is the tile's name; give it as name, not as a property")
    if isinstance(value, float) and not math.isfinite(value):
        raise NamedTilesError(f"{where}: property {key!r} is not a finite number")
    if not isinstance(value, (str, bool, int, float)):
        raise NamedTilesError(
            f"{where}: property {key!r} must be a string, integer, float or boolean, not {type(value).__name__}"
        )


def _int(value, what, where):
    if isinstance(value, bool) or not isinstance(value, int):
        raise NamedTilesError(f"{where}: {what} must be a whole number, not {value!r}")
    return value


def _pair(value, what, where):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise NamedTilesError(f"{where}: {what} must be [column, row]")
    return _int(value[0], what, where), _int(value[1], what, where)


def _tile_id(value, tilecount, where):
    id = _int(value, "id", where)
    if not 0 <= id < tilecount:
        raise NamedTilesError(f"{where}: tile id {id} is outside the tileset (0 to {tilecount - 1})")
    return id


def _cell(column, row, columns, tilecount, where):
    rows = tilecount // columns
    if not (0 <= column < columns and 0 <= row < rows):
        raise NamedTilesError(
            f"{where}: column {column}, row {row} is outside the image ({columns} columns, {rows} rows)"
        )
    return row * columns + column


def _region(value, columns, tilecount, where):
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise NamedTilesError(f"{where}: region must be [column, row, width, height]")
    column, row, width, height = (_int(v, "region", where) for v in value)
    if width < 1 or height < 1:
        raise NamedTilesError(f"{where}: a region needs a width and a height of at least 1")
    _cell(column, row, columns, tilecount, where)
    _cell(column + width - 1, row + height - 1, columns, tilecount, where)
    return [[_cell(column + c, row + r, columns, tilecount, where) for c in range(width)] for r in range(height)]


def _piece_from_spec(entry, index, by_name, columns, tilecount) -> Piece:
    entry = dict(entry)
    name = entry.get("name")
    where = f"pieces entry {index}" + (f" ({name!r})" if isinstance(name, str) else "")
    name = _check_name(name, where)
    unknown = set(entry) - {"name", "region", "rows", "anchor", "kind"}
    if unknown:
        raise NamedTilesError(f"{where}: unknown keys {sorted(unknown)}")
    if ("region" in entry) == ("rows" in entry):
        raise NamedTilesError(f"{where}: give exactly one of region, rows")
    if "region" in entry:
        grid = _region(entry["region"], columns, tilecount, where)
    else:
        rows = entry["rows"]
        if not isinstance(rows, (list, tuple)) or not rows or not all(isinstance(r, (list, tuple)) for r in rows):
            raise NamedTilesError(f"{where}: rows must be a list of rows, each a list of tile names")
        if len({len(r) for r in rows}) != 1 or not rows[0]:
            raise NamedTilesError(f"{where}: every row of a piece must have the same, non-zero, length")
        grid = [[_resolve_cell(c, by_name, tilecount, where) for c in r] for r in rows]
    kind = entry.get("kind", "piece")
    if kind not in ("piece", NINE_SLICE):
        raise NamedTilesError(f"{where}: kind must be 'piece' or {NINE_SLICE!r}, not {kind!r}")
    if kind == NINE_SLICE:
        _check_nine_slice_grid(grid, where)
    anchor = _pair(entry.get("anchor", [1, 1] if kind == NINE_SLICE else [0, 0]), "anchor", where)
    height, width = len(grid), len(grid[0])
    if not (0 <= anchor[0] < width and 0 <= anchor[1] < height):
        raise NamedTilesError(f"{where}: anchor {list(anchor)} is outside the piece ({width} × {height} tiles)")
    if grid[anchor[1]][anchor[0]] is None:
        raise NamedTilesError(f"{where}: the anchor is on an empty cell")
    cls = NineSlice if kind == NINE_SLICE else Piece
    return cls(name, tuple(tuple(r) for r in grid), anchor)


def _check_nine_slice_grid(grid, where):
    if len(grid) != 3 or len(grid[0]) != 3:
        raise NamedTilesError(f"{where}: a nine-slice is three rows of three tiles, not {len(grid[0])} × {len(grid)}")
    if any(cell is None for row in grid for cell in row):
        raise NamedTilesError(f"{where}: a nine-slice can't have gaps")


def _resolve_cell(cell, by_name, tilecount, where):
    if isinstance(cell, str):
        if cell == "":
            return None  # a gap in the piece
        if cell not in by_name:
            raise _unknown_in(where, cell, by_name)
        return by_name[cell]
    return _tile_id(cell, tilecount, where)


def _unknown_in(where, name, known):
    error = _unknown("tile", name, known)
    return UnknownNameError(f"{where}: {error}")


# -- the .tsx side

def encode_property(value) -> tuple[str | None, str]:
    """A Python value as Tiled's (type, text); the type is None for a string, which Tiled leaves out."""
    if isinstance(value, bool):
        return "bool", "true" if value else "false"
    if isinstance(value, int):
        return "int", str(value)
    if isinstance(value, float):
        return "float", repr(value)
    return None, value


def decode_property(type_: str | None, text: str):
    """Tiled's (type, text) as a Python value; types tyled does not write (color, file, ...) stay text."""
    if type_ == "bool":
        return text == "true"
    if type_ == "int":
        return int(text)
    if type_ == "float":
        return float(text)
    return text


def encode_ids(ids) -> str:
    return ";".join(",".join("-" if i is None else str(i) for i in row) for row in ids)


def decode_ids(text: str):
    return tuple(tuple(None if c == "-" else int(c) for c in row.split(",")) for row in text.split(";"))


def named_from_properties(tile_properties: Mapping[int, Mapping], own: Mapping, where="tileset") -> NamedTiles:
    """The names, properties and pieces of a tileset, from the custom properties Tiled keeps.

    `tile_properties` maps a tile id to its properties (the name among them, as Tiled shows it) and `own`
    is the tileset's own properties, where the pieces are. `read_tsx` reads these from a ``.tsx``; a
    ``.tsj`` or a tileset inside a map carries the same properties as JSON, which comes through here too.
    """
    tiles = []
    for id, props in tile_properties.items():
        found = dict(props)
        name = found.pop(NAME_PROPERTY, None)
        if found or name is not None:
            tiles.append(NamedTile(int(id), None if name is None else str(name), found))

    pieces = []
    for key, value in own.items():
        if key.startswith(PIECE_PREFIX):
            name = key[len(PIECE_PREFIX):]
            anchor = str(own.get(ANCHOR_PREFIX + name, "0,0"))
            column, row = (int(n) for n in anchor.split(","))
            kind = str(own.get(KIND_PREFIX + name, "piece"))
            if kind == NINE_SLICE:
                pieces.append(NineSlice(name, decode_ids(str(value)), (column, row)))
            elif kind == "piece":
                pieces.append(Piece(name, decode_ids(str(value)), (column, row)))
            else:
                raise NamedTilesError(f"{where}: piece {name!r} has an unknown kind {kind!r}")
    return NamedTiles(tiles, pieces)


def read_tsx(path) -> NamedTiles:
    """Read the names, properties and pieces of a ``.tsx`` back, as tyled writes them."""
    root = ET.parse(path).getroot()
    if root.tag != "tileset":
        raise NamedTilesError(f"{path} is not a tileset")

    def properties(element):
        found = {}
        for prop in element.findall("properties/property"):
            text = prop.get("value")
            if text is None:
                text = prop.text or ""
            found[prop.get("name")] = decode_property(prop.get("type"), text)
        return found

    tiles = {}
    for element in root.findall("tile"):
        tiles[int(element.get("id", "0"))] = properties(element)
    return named_from_properties(tiles, properties(root), where=str(path))

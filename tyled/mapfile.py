"""Reading Tiled maps and tilesets back, for the programs that look at a map: `render` and `check`.

The map builder writes a ``.tmj``; this module reads one (or a ``.world``, as one map) into plain
objects with everything a viewer needs: layers, tile objects, and for every tileset its picture, its
geometry and what its tiles are called and carry as properties. Tilesets may be ``.tsx`` (as tyled
writes them), ``.tsj`` or embedded in the map.

Only what tyled and Tiled's defaults write is read: finite orthogonal maps whose tile layers are
lists of gids. Anything else is an error that says so, rather than a wrong picture.
"""

from __future__ import annotations

import copy
import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image

from tyled.map.transform import FLAGS, Transform
from tyled.tileset.names import NamedTiles, NamedTilesError, named_from_properties, read_tsx, decode_property

# Tiled keeps a fourth flag (hexagonal rotation) in the bit below the three that tyled uses.
_HEX_FLAG = 0x10000000


class MapFileError(ValueError):
    """A map or tileset file that can't be read, or that holds something tyled doesn't draw or check."""


@dataclass
class TileSource:
    """Where one tile's picture is when it isn't a cell of the tileset's grid image.

    A collection tileset gives each tile a file (`source`); tyled's atlas gives a rectangle of the packed
    image (`rect`, with the `angle` the packer turned it by, which is undone when it is read back; a turned
    tile's rectangle is written with the tile's own width and height, not the turned ones).
    """

    source: Path | None = None
    rect: tuple[int, int, int, int] | None = None
    angle: int = 0


@dataclass
class LoadedTileset:
    """A tileset of a map: geometry, pictures and names. `firstgid` says where its tiles start in the map."""

    name: str
    tilewidth: int
    tileheight: int
    spacing: int = 0
    margin: int = 0
    columns: int = 0
    tilecount: int = 0
    offset: tuple[int, int] = (0, 0)
    image: Path | None = None
    sources: dict[int, TileSource] = field(default_factory=dict)
    named: NamedTiles = field(default_factory=NamedTiles)
    firstgid: int = 1
    key: str = ""  # tells two maps' references to the same tileset apart from different tilesets

    def __post_init__(self):
        self._images: dict[Path, Image.Image] = {}
        self._tiles: dict[int, Image.Image | None] = {}

    @property
    def span(self) -> int:
        """How many gids the tileset takes in a map."""
        return max(self.tilecount, max(self.sources, default=-1) + 1)

    def ids(self) -> list[int]:
        """Every tile id that has a picture, in order."""
        grid = range(self.tilecount) if self.columns > 0 and self.image is not None else ()
        return sorted(set(grid) | set(self.sources))

    def tile_properties(self, id: int) -> dict[str, Any]:
        found = self.named.tile_by_id(id)
        return dict(found.properties) if found is not None else {}

    def tile_name(self, id: int) -> str | None:
        found = self.named.tile_by_id(id)
        return found.name if found is not None else None

    def _load(self, path: Path) -> Image.Image:
        if path not in self._images:
            try:
                with Image.open(path) as opened:
                    self._images[path] = opened.convert("RGBA")
            except FileNotFoundError:
                raise MapFileError(
                    f"tileset {self.name!r}: the image {path} is missing (a tileset made by `tyled bake` "
                    f"has to be baked first, and its image kept where the .tsx says)"
                ) from None
        return self._images[path]

    def tile_image(self, id: int) -> Image.Image | None:
        """The picture of tile `id` as RGBA, or None if the tileset has no picture for it."""
        if id not in self._tiles:
            self._tiles[id] = self._cut(id)
        return self._tiles[id]

    def _cut(self, id: int) -> Image.Image | None:
        source = self.sources.get(id)
        if source is not None:
            if source.source is not None:
                picture = self._load(source.source)
            elif self.image is not None:
                picture = self._load(self.image)
            else:
                return None
            if source.rect is not None:
                x, y, w, h = source.rect
                if source.angle % 180 == 90:
                    w, h = h, w  # tyled writes the tile's own size; turned a quarter, it takes the other way round
                picture = picture.crop((x, y, x + w, y + h))
            if source.angle:
                picture = picture.rotate(-source.angle, expand=True)  # the packer turned it; turn it back
            return picture
        if self.columns > 0 and self.image is not None and 0 <= id < self.tilecount:
            column, row = id % self.columns, id // self.columns
            x = self.margin + column * (self.tilewidth + self.spacing)
            y = self.margin + row * (self.tileheight + self.spacing)
            return self._load(self.image).crop((x, y, x + self.tilewidth, y + self.tileheight))
        return None


@dataclass
class MapObject:
    """An object of an object layer. Tile objects (`gid` not 0) have their origin at the bottom left."""

    id: int
    name: str
    type: str
    x: float
    y: float
    width: float = 0
    height: float = 0
    gid: int = 0
    rotation: float = 0
    visible: bool = True
    properties: dict[str, Any] = field(default_factory=dict)
    layer: str = ""


@dataclass
class Layer:
    """A tile layer (`data`, row by row) or an object layer (`objects`)."""

    name: str
    kind: str  # 'tile' or 'object'
    visible: bool = True
    opacity: float = 1.0
    offsetx: int = 0
    offsety: int = 0
    data: list[int] = field(default_factory=list)
    objects: list[MapObject] = field(default_factory=list)
    draworder: str = "topdown"


@dataclass
class LoadedMap:
    """A map: its size in tiles, tile size in pixels, tilesets and layers (bottom to top)."""

    width: int
    height: int
    tilewidth: int
    tileheight: int
    tilesets: list[LoadedTileset]
    layers: list[Layer]
    source: Path | None = None

    def tile_layers(self) -> list[Layer]:
        return [layer for layer in self.layers if layer.kind == "tile"]

    def object_layers(self) -> list[Layer]:
        return [layer for layer in self.layers if layer.kind == "object"]

    def layer_names(self) -> list[str]:
        return [layer.name for layer in self.layers]

    def resolve(self, gid: int) -> tuple[LoadedTileset, int] | None:
        """The tileset and tile id of a gid (flag bits are ignored), or None for 0 and for a gid no tileset has."""
        gid &= ~(FLAGS | _HEX_FLAG)
        if gid <= 0:
            return None
        found = None
        for tileset in self.tilesets:
            if tileset.firstgid <= gid and (found is None or tileset.firstgid > found.firstgid):
                found = tileset
        if found is None or gid - found.firstgid >= found.span:
            return None
        return found, gid - found.firstgid

    def properties_of(self, gid: int) -> dict[str, Any]:
        found = self.resolve(gid)
        return found[0].tile_properties(found[1]) if found else {}

    @staticmethod
    def transform_of(gid: int) -> Transform:
        return Transform.from_gid(gid)


# ---- tilesets

def _int(value, default=0) -> int:
    return int(value) if value not in (None, "") else default


def _tileset_from_xml(path: Path) -> LoadedTileset:
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as error:
        raise MapFileError(f"{path}: can't read the tileset ({error})") from None
    if root.tag != "tileset":
        raise MapFileError(f"{path} is not a tileset")
    base = path.parent
    image = root.find("image")
    sources = {}
    for tile in root.findall("tile"):
        picture = tile.find("image")
        if picture is None:
            continue
        rect = None
        if picture.get("x") is not None and picture.get("y") is not None:
            rect = (_int(picture.get("x")), _int(picture.get("y")), _int(picture.get("width")), _int(picture.get("height")))
        source = picture.get("source")
        sources[_int(tile.get("id"))] = TileSource(
            base / source if source else None, rect, int(float(picture.get("angle", 0)))
        )
    offset = root.find("tileoffset")
    try:
        named = read_tsx(path)
    except NamedTilesError as error:
        raise MapFileError(str(error)) from None
    return LoadedTileset(
        name=root.get("name", path.stem),
        tilewidth=_int(root.get("tilewidth")),
        tileheight=_int(root.get("tileheight")),
        spacing=_int(root.get("spacing")),
        margin=_int(root.get("margin")),
        columns=_int(root.get("columns")),
        tilecount=_int(root.get("tilecount")),
        offset=(_int(offset.get("x")), _int(offset.get("y"))) if offset is not None else (0, 0),
        image=base / image.get("source") if image is not None and image.get("source") else None,
        sources=sources,
        named=named,
        key=str(path.resolve()),
    )


def _properties_of(tree) -> dict[str, Any]:
    """Tiled's JSON properties (a list of name, type, value) as a dict."""
    found = {}
    for prop in tree or []:
        value = prop.get("value")
        found[prop["name"]] = value if not isinstance(value, str) or prop.get("type") in (None, "string") \
            else decode_property(prop.get("type"), value)
    return found


def _tileset_from_json(tree: dict, base: Path, key: str) -> LoadedTileset:
    sources = {}
    tile_properties = {}
    for tile in tree.get("tiles", []):
        id = int(tile["id"])
        props = _properties_of(tile.get("properties"))
        if tile.get("type") or tile.get("class"):
            props.setdefault("kind", tile.get("type") or tile.get("class"))
        tile_properties[id] = props
        rect = None
        if "width" in tile and "height" in tile and ("x" in tile or "y" in tile or "image" in tile):
            rect = (int(tile.get("x", 0)), int(tile.get("y", 0)), int(tile["width"]), int(tile["height"]))
        if "image" in tile:
            sources[id] = TileSource(base / tile["image"], rect if "x" in tile else None)
    offset = tree.get("tileoffset", {})
    try:
        named = named_from_properties(tile_properties, _properties_of(tree.get("properties")), where=key)
    except NamedTilesError as error:
        raise MapFileError(str(error)) from None
    return LoadedTileset(
        name=tree.get("name", Path(key).stem),
        tilewidth=int(tree.get("tilewidth", 0)),
        tileheight=int(tree.get("tileheight", 0)),
        spacing=int(tree.get("spacing", 0)),
        margin=int(tree.get("margin", 0)),
        columns=int(tree.get("columns", 0)),
        tilecount=int(tree.get("tilecount", 0)),
        offset=(int(offset.get("x", 0)), int(offset.get("y", 0))),
        image=base / tree["image"] if tree.get("image") else None,
        sources=sources,
        named=named,
        key=key,
    )


def load_tileset(path: Path | str) -> LoadedTileset:
    """Read a ``.tsx`` or ``.tsj`` (with its picture, found beside it) as a `LoadedTileset` with firstgid 1."""
    path = Path(path)
    if not path.exists():
        raise MapFileError(f"tileset {str(path)!r} doesn't exist")
    if path.suffix == ".tsx":
        return _tileset_from_xml(path)
    if path.suffix in (".tsj", ".json"):
        try:
            tree = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise MapFileError(f"{path}: can't read the tileset ({error})") from None
        return _tileset_from_json(tree, path.parent, str(path.resolve()))
    raise MapFileError(f"tileset {str(path)!r} should be a .tsx or .tsj (a tileset project, .toml, is baked into a .tsx first)")


# ---- maps

def _object(tree: dict, layer: str) -> MapObject:
    return MapObject(
        id=int(tree.get("id", 0)),
        name=str(tree.get("name", "")),
        type=str(tree.get("type") or tree.get("class") or ""),
        x=float(tree.get("x", 0)),
        y=float(tree.get("y", 0)),
        width=float(tree.get("width", 0)),
        height=float(tree.get("height", 0)),
        gid=int(tree.get("gid", 0)),
        rotation=float(tree.get("rotation", 0)),
        visible=bool(tree.get("visible", True)),
        properties=_properties_of(tree.get("properties")),
        layer=layer,
    )


def _layers(trees, width: int, height: int, where) -> list[Layer]:
    found = []
    for tree in trees:
        kind = tree.get("type")
        name = str(tree.get("name", ""))
        visible = bool(tree.get("visible", True))
        opacity = float(tree.get("opacity", 1))
        offsetx, offsety = int(tree.get("offsetx", 0)), int(tree.get("offsety", 0))
        if kind == "tilelayer":
            data = tree.get("data")
            if not isinstance(data, list) or "chunks" in tree:
                raise MapFileError(
                    f"{where}: layer {name!r} stores its tiles as {'chunks' if 'chunks' in tree else 'encoded text'}; "
                    f"tyled reads finite maps with the tile data as a list (Tiled: Map Properties, Tile Layer Format: CSV)"
                )
            if len(data) != width * height:
                raise MapFileError(f"{where}: layer {name!r} has {len(data)} tiles, not {width} × {height}")
            found.append(Layer(name, "tile", visible, opacity, offsetx, offsety, data=[int(g) for g in data]))
        elif kind == "objectgroup":
            found.append(Layer(
                name, "object", visible, opacity, offsetx, offsety,
                objects=[_object(o, name) for o in tree.get("objects", [])],
                draworder=tree.get("draworder", "topdown"),
            ))
        elif kind == "group":
            found.extend(_layers(tree.get("layers", []), width, height, where))
        # image layers aren't drawn or checked
    return found


def _map_from_dict(tree: dict, base: Path, source: Path | None) -> LoadedMap:
    where = str(source) if source is not None else "the map"
    if tree.get("type", "map") != "map":
        raise MapFileError(f"{where} is not a map")
    if tree.get("orientation", "orthogonal") != "orthogonal":
        raise MapFileError(f"{where}: {tree['orientation']!r} maps aren't supported, only orthogonal ones")
    if tree.get("infinite"):
        raise MapFileError(f"{where}: infinite maps aren't supported")
    width, height = int(tree["width"]), int(tree["height"])
    tilesets = []
    for index, entry in enumerate(tree.get("tilesets", [])):
        if "source" in entry:
            loaded = load_tileset(base / entry["source"])
        else:
            loaded = _tileset_from_json(entry, base, f"{where}#{index}")
        loaded.firstgid = int(entry.get("firstgid", 1))
        tilesets.append(loaded)
    return LoadedMap(
        width=width, height=height, tilewidth=int(tree["tilewidth"]), tileheight=int(tree["tileheight"]),
        tilesets=tilesets, layers=_layers(tree.get("layers", []), width, height, where), source=source,
    )


def _combine(parts: list[tuple[LoadedMap, int, int]], source: Path | None) -> LoadedMap:
    """Maps placed at (x, y) pixels, as one map: the way a Tiled world shows them.

    Tilesets that several maps share (the same file) are kept once, with their gids renumbered to match.
    """
    first = parts[0][0]
    tw, th = first.tilewidth, first.tileheight
    for part, _, _ in parts:
        if (part.tilewidth, part.tileheight) != (tw, th):
            raise MapFileError(f"{part.source}: its tiles are {part.tilewidth} × {part.tileheight}, not {tw} × {th} like the world's first map")
    tilesets: list[LoadedTileset] = []
    by_key: dict[str, LoadedTileset] = {}
    next_gid = 1
    for part, _, _ in parts:
        for tileset in part.tilesets:
            if tileset.key not in by_key:
                merged = copy.copy(tileset)
                merged.firstgid = next_gid
                next_gid += merged.span
                by_key[tileset.key] = merged
                tilesets.append(merged)

    def renumber(part: LoadedMap, gid: int) -> int:
        found = part.resolve(gid)
        if found is None:
            return gid  # nothing to renumber; the merged map will report it as unknown, as the part would
        tileset, id = found
        return (gid & (FLAGS | _HEX_FLAG)) | (by_key[tileset.key].firstgid + id)

    cells = []
    for part, x, y in parts:
        if x % tw or y % th:
            raise MapFileError(f"{part.source}: placed at {x},{y}, which isn't on the world's {tw} × {th} grid")
        cells.append((x // tw, y // th))
    width = max(c + part.width for (part, _, _), (c, _) in zip(parts, cells))
    height = max(r + part.height for (part, _, _), (_, r) in zip(parts, cells))

    layers: dict[str, Layer] = {}
    for (part, _, _), (column, row) in zip(parts, cells):
        for layer in part.layers:
            merged = layers.get(layer.name)
            if merged is None:
                merged = layers[layer.name] = Layer(
                    layer.name, layer.kind, layer.visible, layer.opacity, layer.offsetx, layer.offsety,
                    data=[0] * (width * height) if layer.kind == "tile" else [], draworder=layer.draworder,
                )
            elif merged.kind != layer.kind:
                raise MapFileError(f"the layer {layer.name!r} is a {merged.kind} layer in one map and a {layer.kind} layer in another")
            if layer.kind == "tile":
                for r in range(part.height):
                    for c in range(part.width):
                        gid = layer.data[r * part.width + c]
                        if gid:
                            merged.data[(row + r) * width + column + c] = renumber(part, gid)
            else:
                for obj in layer.objects:
                    moved = copy.copy(obj)
                    moved.x += column * tw
                    moved.y += row * th
                    if moved.gid:
                        moved.gid = renumber(part, moved.gid)
                    merged.objects.append(moved)
    for layer in layers.values():
        for index, obj in enumerate(layer.objects, 1):
            obj.id = index
    return LoadedMap(width, height, tw, th, tilesets, list(layers.values()), source)


def load_map(source) -> LoadedMap:
    """Read a map: a ``.tmj`` or ``.world`` path (a world is placed as one map), a dict as Tiled's JSON, or a `MapProject`.

    A dict's tileset sources count from the current folder; a project's are already complete.
    """
    from tyled.map import MapProject  # here: tyled.map doesn't need this module, and this one is rarely the first import

    if isinstance(source, LoadedMap):
        return source
    if isinstance(source, MapProject):
        return _map_from_dict(source.to_dict(), source.base, None)
    if isinstance(source, dict):
        return _map_from_dict(source, Path("."), None)
    path = Path(source)
    if not path.exists():
        raise MapFileError(f"map {str(path)!r} doesn't exist")
    try:
        tree = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise MapFileError(f"{path}: can't read it as JSON ({error}); tyled reads .tmj and .world files") from None
    if path.suffix == ".world" or tree.get("type") == "world":
        entries = tree.get("maps", [])
        if not entries:
            raise MapFileError(f"{path}: the world has no maps")
        parts = [(load_map(path.parent / entry["fileName"]), int(entry.get("x", 0)), int(entry.get("y", 0))) for entry in entries]
        return _combine(parts, path)
    return _map_from_dict(tree, path.parent, path)

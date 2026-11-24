import os
from dataclasses import dataclass

from loguru import logger
from PIL import Image

from tyled.tileset import Tileset
from tyled.tileset.names import (
    ANCHOR_PREFIX,
    NAME_PROPERTY,
    PIECE_PREFIX,
    NamedTile,
    NamedTiles,
    NamedTilesError,
    KIND_PREFIX,
    NINE_SLICE,
    NineSlice,
    Piece,
    encode_ids,
    encode_property,
)

# The tables of a project file that this kind reads itself. Tileset.__init__ copies every key of the
# project onto the object, which would let `tiles` replace the list of tiles; so they are taken out first.
SPEC_KEYS = ("tiles", "pieces", "defaults")


@dataclass
class GridProperty:
    """A Tiled custom property as the template writes it: `type` is None for a string."""

    name: str
    type: str | None
    value: str


@dataclass
class GridTile:
    """A tile that has something to write: its id and its custom properties, name first."""

    id: int
    properties: list[GridProperty]


def _property(name, value) -> GridProperty:
    return GridProperty(name, *encode_property(value))


class GridTileset(Tileset):
    """A tileset over an image that is already a grid of equal tiles (Kenney's tilemaps, say).

    The image is used as it is: nothing is repacked and nothing is copied. The ``.tsx`` refers to it by
    a path relative to where the ``.tsx`` is written. What the kind adds is the naming: tile names,
    properties and pieces from the project file (see `tyled.tileset.names`), kept in the ``.tsx`` as Tiled
    custom properties.

    Tile size is always given. Columns come from the image; spacing and margin come from the project
    file, or, if it gives neither, from the image when only one grid fits it exactly.
    """

    def __init__(self, *config, **kwargs):
        # Tiled's current format; the older kinds write the 1.2 header and keep it.
        defaults = {"version": "1.10", "tiledversion": "1.10.2"}
        self._spec = {}
        given = {}
        cleaned = []
        for dictionary in config:
            dictionary = dict(dictionary)
            for key in SPEC_KEYS:
                if key in dictionary:
                    self._spec[key] = dictionary.pop(key)
            given.update(dictionary)
            cleaned.append(dictionary)
        super().__init__(defaults, *cleaned, **kwargs)
        self._given = set(given) | set(kwargs)
        self.add_template_path("grid/templates")
        self.named = NamedTiles()
        self.tileset_properties: list[GridProperty] = []

    @classmethod
    def create(self, *config, **kwargs):
        ts = GridTileset(*config, **kwargs)
        ts.build()
        return ts

    # -- reading the names back

    def tile(self, name):
        """The tile called `name`: its id and properties. A misspelled name is an error naming the nearest."""
        return self.named.tile(name)

    def piece(self, name):
        """The piece called `name`, as a grid of tile ids with its anchor."""
        return self.named.piece(name)

    # -- building

    def build(self):
        if not self.source:
            raise NamedTilesError(f"{self.name}: a grid tileset needs a source, the image of the grid")
        if not self.tilewidth or not self.tileheight:
            raise NamedTilesError(
                f"{self.name}: a grid tileset needs tilewidth and tileheight; the image can't tell them"
            )
        with Image.open(self.source) as image:
            self.width, self.height = image.size

        self._fit_the_grid()
        self.columns = self._count(self.width, self.tilewidth)
        self.rows = self._count(self.height, self.tileheight)
        self.tilecount = self.columns * self.rows
        logger.debug(
            f"build: {self.columns} × {self.rows} tiles of {self.tilewidth} × {self.tileheight}, "
            f"spacing={self.spacing}, margin={self.margin}"
        )

        self.named = NamedTiles.from_spec(
            columns=self.columns,
            tilecount=self.tilecount,
            tiles=self._spec.get("tiles", ()),
            pieces=self._spec.get("pieces", ()),
            defaults=self._spec.get("defaults"),
        )
        self.tiles = [GridTile(t.id, self._tile_properties(t)) for t in self.named.tiles()]
        self.tileset_properties = [p for piece in self.named.pieces() for p in self._piece_properties(piece)]

        # Where the image is, as Tiled will look for it: relative to the .tsx, which is written here.
        self.image_source = os.path.relpath(self.source).replace(os.sep, "/")

    def _count(self, extent, tile):
        return (extent - 2 * self.margin + self.spacing) // (tile + self.spacing)

    def _fits(self, margin, spacing):
        def exact(extent, tile):
            n = (extent - 2 * margin + spacing) // (tile + spacing)
            return n > 0 and 2 * margin + n * tile + (n - 1) * spacing == extent

        return exact(self.width, self.tilewidth) and exact(self.height, self.tileheight)

    def _fit_the_grid(self):
        """Settle spacing and margin; check that the columns the project gives are the image's."""
        if "spacing" not in self._given and "margin" not in self._given:
            if not self._fits(0, 0):
                # No gap or border fits, so look for one; a single answer is read from the image.
                found = [s for s in range(1, max(self.tilewidth, self.tileheight) + 1) if self._fits(0, s)]
                if len(found) == 1:
                    self.spacing = found[0]
        if self.margin < 0 or self.spacing < 0:
            raise NamedTilesError(f"{self.name}: spacing and margin can't be negative")
        columns = self._count(self.width, self.tilewidth)
        if columns < 1 or self._count(self.height, self.tileheight) < 1:
            raise NamedTilesError(
                f"{self.name}: the image ({self.width} × {self.height}) holds no tile of "
                f"{self.tilewidth} × {self.tileheight} with spacing {self.spacing} and margin {self.margin}"
            )
        if "columns" in self._given and self.columns != columns:
            raise NamedTilesError(
                f"{self.name}: the project says {self.columns} columns, but the image holds {columns} "
                f"(tiles of {self.tilewidth} px, spacing {self.spacing}, margin {self.margin})"
            )

    @staticmethod
    def _tile_properties(tile: NamedTile) -> list[GridProperty]:
        found = [_property(NAME_PROPERTY, tile.name)] if tile.name is not None else []
        return found + [_property(key, value) for key, value in tile.properties.items()]

    @staticmethod
    def _piece_properties(piece: Piece) -> list[GridProperty]:
        found = [
            _property(PIECE_PREFIX + piece.name, encode_ids(piece.ids)),
            _property(ANCHOR_PREFIX + piece.name, f"{piece.anchor[0]},{piece.anchor[1]}"),
        ]
        if isinstance(piece, NineSlice):
            found.append(_property(KIND_PREFIX + piece.name, NINE_SLICE))
        return found

    def do_bake(self):
        # Nothing to draw: the image stays where it is and the .tsx points at it.
        pass

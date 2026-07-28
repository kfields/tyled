from tyled.tileset.collection import CollectionTileset
from tyled.tileset.orthogonal import OrthogonalTileset
from tyled.tileset.atlas import AtlasTileset
from tyled.tileset.sheet import SheetTileset
from tyled.tileset.slice import SliceTileset

class TilesetFactory:
    def __init__(self):
        pass

    def produce(self, config, options):
        kind = config["type"]
        if kind == "collection":
            return CollectionTileset.create(config, options=options)
        elif kind == "orthogonal":
            return OrthogonalTileset.create(config, options=options)
        elif kind == "atlas":
            return AtlasTileset.create(config, options=options)
        elif kind == "sheet":
            return SheetTileset.create(config, options=options)
        elif kind == "slice":
            return SliceTileset.create(config, options=options)
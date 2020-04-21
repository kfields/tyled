import sys
import os
import glob

import jinja2
from PIL import Image

from tyled.tileset import Tile, Tileset

class CollectionTileset(Tileset):
    def __init__(self, *initial_data, **kwargs):
        super().__init__(*initial_data, **kwargs)
        self.add_template_path('collection/templates')

    @classmethod
    def create(self, *initial_data, **kwargs):
        ts = CollectionTileset(*initial_data, **kwargs)
        ts.build()
        return ts

    def build(self):
        columns = self.columns
        margin = self.margin
        tilewidth = self.tilewidth
        tileheight = self.tileheight
        spacing = self.spacing
        source = self.source

        files = sorted(glob.glob(f"{source}/*.png"))
        self.tilecount = tilecount = len(files)

        gid = self.firstgid
        for file in files:
            base = os.path.basename(file)
            kind = os.path.splitext(base)[0]
            self.tiles.append(Tile(file, gid, kind))
            gid +=1

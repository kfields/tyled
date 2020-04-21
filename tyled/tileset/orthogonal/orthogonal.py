import sys
import os
import glob

import jinja2

from PIL import Image

from tyled.tileset import Tile, Tileset

class OrthogonalTileset(Tileset):
    def __init__(self, *initial_data, **kwargs):
        super().__init__(*initial_data, **kwargs)
        self.add_template_path('orthogonal/templates')

    @classmethod
    def create(self, *initial_data, **kwargs):
        ts = OrthogonalTileset(*initial_data, **kwargs)
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

        self.width = (margin*2) + columns * (tilewidth+(spacing))
        rows = int(tilecount / columns)
        self.rows = rows = rows + 1 if tilecount % columns > 0 else rows
        self.height = (margin*2) + rows * (tileheight+(spacing))

        gid = self.firstgid
        for file in files:
            base = os.path.basename(file)
            kind = os.path.splitext(base)[0]
            self.tiles.append(Tile(file, gid, kind))
            gid +=1

    def do_bake(self):
        canvas = Image.new('RGBA', (self.width, self.height), (255, 0, 0, 0))
        tiles = self.tiles.copy()
        for i in range(0, self.rows):
            for j in range(0, self.columns):
                if len(tiles) == 0:
                    break
                tile = tiles.pop(0)
                offset = ( self.margin + (j*(self.tilewidth+(self.spacing))), self.margin + (i*(self.tileheight+(self.spacing))) )
                tile.draw(canvas, offset)
        
        if self.options.show:
            canvas.show()
        if self.options.save:
            canvas.save(f"{self.name}.png")

import sys
import os
import glob

from PIL import Image
from rectpack import newPacker

from tyled import Tile, Tileset

class AtlasTileset(Tileset):
    def __init__(self, *config, **kwargs):
        super().__init__(*config, **kwargs)
        self.add_template_path('atlas/templates')

    @classmethod
    def create(self, *config, **kwargs):
        ts = AtlasTileset(*config, **kwargs)
        ts.build()
        return ts

    def build(self):
        source = self.source

        self.files = files = sorted(glob.glob(f"{source}/*.png"))
        self.tilecount = tilecount = len(files)

        gid = self.firstgid
        for file in files:
            base = os.path.basename(file)
            kind = os.path.splitext(base)[0]
            self.tiles.append(Tile(file, gid, kind))
            gid +=1

    def do_bake(self):
        packer = newPacker(rotation=self.options.rotation)

        for tile in self.tiles:
            #print(tile)
            packer.add_rect(tile.width, tile.height, tile)

        packer.add_bin(self.width, self.height)

        packer.pack()

        canvas = Image.new('RGBA', (self.width, self.height), (255, 0, 0, 0))

        #TODO: possibility of tile groups per bin, spritesheet per bin?
        for abin in packer:
            for rect in abin:
                #print('rect', rect)
                tile = rect.rid
                if self.options.rotation and tile.width != tile.height and tile.width == rect.height:
                    tile.draw(canvas, (rect.x, self.height - rect.y - rect.height), 90)
                else:
                    tile.draw(canvas, (rect.x, self.height - rect.y - rect.height))

        if self.options.show:
            canvas.show()
        if self.options.save:
            canvas.save(f"{self.name}.png")
            self.export()

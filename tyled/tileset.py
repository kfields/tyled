import sys
import os
import glob

class Tile:
    def __init__(self, id, kind):
        self.id = id
        self.kind = kind

class Tileset:
    def __init__(self, *initial_data, **kwargs):
        self.tiles = []
        self.firstgid = 1

        for dictionary in initial_data:
            for key in dictionary:
                setattr(self, key, dictionary[key])
        for key in kwargs:
            setattr(self, key, kwargs[key])

    @classmethod
    def create(self, *initial_data, **kwargs):
        ts = Tileset(*initial_data, **kwargs)
        ts.build()
        return ts

    def build(self):
        columns = self.columns
        margin = self.margin
        tilewidth = self.tilewidth
        tileheight = self.tileheight
        spacing = self.spacing
        source = self.source

        self.files = files = sorted(glob.glob(f"{source}/*.png"))
        self.tilecount = tilecount = len(files)

        self.width = (margin*2) + columns * (tilewidth+(spacing))
        rows = int(tilecount / columns)
        self.rows = rows = rows + 1 if tilecount % columns > 0 else rows
        self.height = (margin*2) + rows * (tileheight+(spacing))

        gid = self.firstgid
        for file in files:
            base = os.path.basename(file)
            kind = os.path.splitext(base)[0]
            self.tiles.append(Tile(gid, kind))
            gid +=1


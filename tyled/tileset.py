import sys
import os
import glob

class Tileset:
    def __init__(self, *initial_data, **kwargs):
        for dictionary in initial_data:
            for key in dictionary:
                setattr(self, key, dictionary[key])
        for key in kwargs:
            setattr(self, key, kwargs[key])

        columns = self.columns
        margin = self.margin
        tilewidth = self.tilewidth
        tileheight = self.tileheight
        spacing = self.spacing
        source = self.source

        #self.width = (margin*2) + columns * (tilewidth+(spacing*2))
        self.width = (margin*2) + columns * (tilewidth+(spacing))

        self.files = files = sorted(glob.glob(f"{source}/*.png"))
        self.tilecount = tilecount = len(files)
        self.rows = rows = int(tilecount / columns)
        #self.height = (margin*2) + rows * (tileheight+(spacing*2))
        self.height = (margin*2) + rows * (tileheight+(spacing))

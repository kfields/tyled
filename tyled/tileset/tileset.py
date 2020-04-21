import sys
import os
import glob

import jinja2

from tyled.tile import Tile

class Options:
    def __init__(self, *options, **kwargs):
        for dictionary in options:
            for key in dictionary:
                setattr(self, key, dictionary[key])
        for key in kwargs:
            setattr(self, key, kwargs[key])

class Tileset:
    def __init__(self, *config, **kwargs):
        self.options = { 'save': True }
        self.version = "1.2"
        self.tiledversion="1.3.3"
        self.tiles = []
        self.firstgid = 1
        self.columns = 0
        self.margin = 0
        self.tilewidth = 0
        self.tileheight = 0
        self.spacing = 0
        self.source = None

        self.searchpath = []
        self.add_template_path('templates')

        for dictionary in config:
            for key in dictionary:
                setattr(self, key, dictionary[key])
        for key in kwargs:
            if key == 'options':
                options = kwargs[key]
                options.update(self.options)
                self.options = options

            setattr(self, key, kwargs[key])

        
        self.options = Options(self.options)

    @classmethod
    def create(self, *options, **kwargs):
        ts = Tileset(*options, **kwargs)
        ts.build()
        return ts

    def build(self):
        pass

    def bake(self):
        self.pre_bake()
        self.do_bake()
        self.post_bake()

    def pre_bake(self):
        pass

    def do_bake(self):
        pass

    def post_bake(self):
        if self.options.save:
            self.export()

    def export(self):
        config = self.__dict__
        '''
        env = Environment(
            loader=PackageLoader('tyled', 'templates'),
            autoescape=select_autoescape(['html', 'xml'])
        )
        '''
        loader = jinja2.FileSystemLoader(searchpath=self.searchpath)
        env = jinja2.Environment(loader=loader)

        template = env.get_template('tileset.xml')
        rendered = template.render(config)
        #print(rendered)
        filename = f"{self.name}.tsx"
        with open(filename,'w') as fh:
            fh.write(rendered)

    def add_template_path(self, path):
        self.searchpath.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), path)))
        #print(self.searchpath)
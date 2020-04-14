import sys
import os

#sys.path.append(os.path.abspath(__file__))

import jinja2
from jinja2 import Environment, PackageLoader, select_autoescape


def main(ts):
    config = ts.__dict__
    '''
    env = Environment(
        loader=PackageLoader('tyled', 'templates'),
        autoescape=select_autoescape(['html', 'xml'])
    )
    '''
    searchpath = os.path.abspath(os.path.join(__file__, '../templates'))
    loader = jinja2.FileSystemLoader(searchpath=searchpath)
    env = jinja2.Environment(loader=loader)

    template = env.get_template('tileset.xml')
    rendered = template.render(config)
    print(rendered)
    filename = f"{ts.name}.tsx"
    with open(filename,'w') as fh:
        fh.write(rendered)

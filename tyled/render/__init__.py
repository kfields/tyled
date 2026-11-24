"""Pictures of maps and tilesets: `render_map` draws a map, `render_sheet` a tileset's contact sheet.

Both return a Pillow image; `save_png` writes it the same way every time, so a picture can be diffed.
"""

from tyled.render.draw import RenderError, save_png
from tyled.render.mapimage import render_map
from tyled.render.sheet import render_sheet

__all__ = ["RenderError", "render_map", "render_sheet", "save_png"]

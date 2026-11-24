"""A map drawn to an image: what an agent or a test can look at instead of opening Tiled."""

from __future__ import annotations

import math
from typing import Iterable

from PIL import Image, ImageDraw

from tyled.map.transform import Transform
from tyled.mapfile import Layer, LoadedMap, MapObject, load_map
from tyled.render.draw import LINE_HEIGHT, RenderError, blit, label, turn

OUTLINE = (255, 230, 0, 255)
GRID = (0, 0, 0, 80)


def render_map(
    map,
    *,
    scale: int = 1,
    region: tuple[int, int, int, int] | None = None,
    layers: Iterable[str] | None = None,
    labels: bool = False,
    grid: bool = False,
) -> Image.Image:
    """Draw a map as an RGBA image, empty cells transparent.

    `map` is what `load_map` takes: the path of a ``.tmj`` or ``.world`` (a world is drawn as one map).
    Tile layers are drawn in order with the flags on their gids applied as Tiled applies them (diagonal
    flip first, then horizontal, then vertical), and tile objects where Tiled puts them: the origin is the
    bottom left, they are scaled to the object's size and turned about that corner by its rotation.

    `scale` enlarges the picture by a whole number, nearest-neighbour, so pixel art stays sharp. `region`
    is ``(x, y, width, height)`` in tiles and draws only that part. `layers` names the layers to draw
    (a hidden layer is drawn when named; by default the visible ones are). `labels` marks every object of
    the drawn layers with an outline and its name; `grid` draws the tile grid.
    """
    loaded = load_map(map)
    if isinstance(scale, bool) or not isinstance(scale, int) or scale < 1:
        raise RenderError(f"scale must be a whole number of 1 or more, not {scale!r}")
    left, top, columns, rows = _region(loaded, region)
    chosen = _chosen(loaded, layers)

    tw, th = loaded.tilewidth, loaded.tileheight
    canvas = Image.new("RGBA", (loaded.width * tw, loaded.height * th), (0, 0, 0, 0))
    for layer in chosen:
        picture = Image.new("RGBA", canvas.size, (0, 0, 0, 0)) if layer.opacity < 1 else canvas
        if layer.kind == "tile":
            _draw_tiles(loaded, layer, picture)
        else:
            _draw_objects(loaded, layer, picture)
        if picture is not canvas:
            factor = min(max(layer.opacity, 0.0), 1.0)
            alpha = picture.getchannel("A").point([round(i * factor) for i in range(256)])
            picture.putalpha(alpha)
            canvas.alpha_composite(picture)

    box = (left * tw, top * th, (left + columns) * tw, (top + rows) * th)
    image = canvas.crop(box)
    if scale > 1:
        image = image.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST)
    if grid:
        _draw_grid(image, tw * scale, th * scale)
    if labels:
        for layer in chosen:
            if layer.kind == "object":
                for obj in layer.objects:
                    _draw_label(image, obj, loaded, box, scale)
    return image


def _region(loaded: LoadedMap, region) -> tuple[int, int, int, int]:
    if region is None:
        return 0, 0, loaded.width, loaded.height
    try:
        x, y, w, h = region
    except (TypeError, ValueError):
        raise RenderError(f"region is x, y, width, height in tiles, not {region!r}") from None
    if any(isinstance(v, bool) or not isinstance(v, int) for v in (x, y, w, h)):
        raise RenderError(f"region is four whole numbers, not {region!r}")
    if w < 1 or h < 1 or x < 0 or y < 0 or x + w > loaded.width or y + h > loaded.height:
        raise RenderError(
            f"region {x},{y},{w},{h} is not inside the map, which is {loaded.width} × {loaded.height} tiles"
        )
    return x, y, w, h


def _chosen(loaded: LoadedMap, layers) -> list[Layer]:
    if layers is None:
        return [layer for layer in loaded.layers if layer.visible]
    names = [layers] if isinstance(layers, str) else list(layers)
    known = loaded.layer_names()
    for name in names:
        if name not in known:
            raise RenderError(f"the map has no layer {name!r}; its layers are {', '.join(known)}")
    return [layer for layer in loaded.layers if layer.name in names]  # the map's order, whatever the order asked


def _draw_tiles(loaded: LoadedMap, layer: Layer, canvas: Image.Image) -> None:
    tw, th = loaded.tilewidth, loaded.tileheight
    for index, gid in enumerate(layer.data):
        if not gid:
            continue
        found = loaded.resolve(gid)
        if found is None:
            continue
        tileset, id = found
        picture = tileset.tile_image(id)
        if picture is None:
            continue
        picture = turn(picture, Transform.from_gid(gid))
        row, column = divmod(index, loaded.width)
        # Tiled puts a tile's bottom left at the bottom left of its cell, so a tall tile grows upwards.
        x = column * tw + tileset.offset[0] + layer.offsetx
        y = (row + 1) * th - picture.height + tileset.offset[1] + layer.offsety
        blit(canvas, picture, x, y)


def _draw_objects(loaded: LoadedMap, layer: Layer, canvas: Image.Image) -> None:
    objects = [o for o in layer.objects if o.gid and o.visible]
    if layer.draworder == "topdown":
        objects.sort(key=lambda o: o.y)  # stable: objects level with each other keep their order
    for obj in objects:
        found = loaded.resolve(obj.gid)
        if found is None:
            continue
        tileset, id = found
        picture = tileset.tile_image(id)
        if picture is None:
            continue
        width = round(obj.width) if obj.width else picture.width
        height = round(obj.height) if obj.height else picture.height
        if (width, height) != picture.size:
            picture = picture.resize((width, height), Image.Resampling.NEAREST)
        picture = turn(picture, Transform.from_gid(obj.gid))
        pivot_x = obj.x + tileset.offset[0] + layer.offsetx
        pivot_y = obj.y + tileset.offset[1] + layer.offsety
        # A tile object's origin is its bottom left, and it turns clockwise about that corner. Its picture's
        # centre starts at (w/2, -h/2) from the corner; turn that and centre the (larger) turned picture on it.
        angle = math.radians(obj.rotation)
        cx, cy = picture.width / 2, -picture.height / 2
        turned_x = cx * math.cos(angle) - cy * math.sin(angle)
        turned_y = cx * math.sin(angle) + cy * math.cos(angle)
        if obj.rotation % 360:
            picture = picture.rotate(-obj.rotation, expand=True, resample=Image.Resampling.NEAREST)
        blit(
            canvas, picture,
            round(pivot_x + turned_x - picture.width / 2), round(pivot_y + turned_y - picture.height / 2),
        )


def _draw_grid(image: Image.Image, cell_width: int, cell_height: int) -> None:
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    lines = ImageDraw.Draw(overlay)
    for x in range(0, image.width + 1, cell_width):
        lines.line([(min(x, image.width - 1), 0), (min(x, image.width - 1), image.height)], fill=GRID)
    for y in range(0, image.height + 1, cell_height):
        lines.line([(0, min(y, image.height - 1)), (image.width, min(y, image.height - 1))], fill=GRID)
    image.alpha_composite(overlay)


def _draw_label(image: Image.Image, obj: MapObject, loaded: LoadedMap, box, scale: int) -> None:
    """Outline an object and write its name above it; drawn after the enlarging, so the text stays small and sharp."""
    if obj.gid:
        found = loaded.resolve(obj.gid)
        width = obj.width or (found[0].tilewidth if found else loaded.tilewidth)
        height = obj.height or (found[0].tileheight if found else loaded.tileheight)
        left, top = obj.x, obj.y - height
    else:
        width, height = obj.width, obj.height
        left, top = obj.x, obj.y
    right, bottom = left + width, top + height
    if right < box[0] or left > box[2] or bottom < box[1] or top > box[3]:
        return
    x0, y0 = round((left - box[0]) * scale), round((top - box[1]) * scale)
    x1, y1 = round((right - box[0]) * scale), round((bottom - box[1]) * scale)
    if x1 - x0 < 3 or y1 - y0 < 3:  # a point: a small cross instead of a box
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        draw = ImageDraw.Draw(image)
        draw.line([(cx - 3, cy), (cx + 3, cy)], fill=OUTLINE)
        draw.line([(cx, cy - 3), (cx, cy + 3)], fill=OUTLINE)
    else:
        ImageDraw.Draw(image).rectangle([x0, y0, x1 - 1, y1 - 1], outline=OUTLINE)
    text = obj.name or obj.type or f"#{obj.id}"
    label(image, x0, y0 - LINE_HEIGHT - 3 if y0 >= LINE_HEIGHT + 3 else y1 + 1, text)

"""Small drawing helpers shared by the map and tileset renderers.

Text is drawn with Pillow's built-in bitmap font, not a TrueType one: it needs no font file and draws
the same pixels everywhere, which keeps golden-image tests stable across machines and Pillow builds.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from tyled.map.transform import Transform

FONT = ImageFont.load_default_imagefont()
CHAR_WIDTH = 6
LINE_HEIGHT = 11


class RenderError(ValueError):
    """Something asked of a renderer that can't be drawn: a region off the map, a layer that isn't there."""


def text_width(text: str) -> int:
    return int(FONT.getlength(text))


def turn(image: Image.Image, transform: Transform) -> Image.Image:
    """The picture of a tile as Tiled draws it with these flags: transposed, then mirrored across, then down."""
    if transform.diagonal:
        image = image.transpose(Image.Transpose.TRANSPOSE)
    if transform.horizontal:
        image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if transform.vertical:
        image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return image


def blit(canvas: Image.Image, picture: Image.Image, x: int, y: int) -> None:
    """Lay `picture` over `canvas` with its top left at (x, y), blending its alpha; what is off the canvas is cut."""
    left, top = max(x, 0), max(y, 0)
    right, bottom = min(x + picture.width, canvas.width), min(y + picture.height, canvas.height)
    if left >= right or top >= bottom:
        return
    piece = picture.crop((left - x, top - y, right - x, bottom - y))
    canvas.alpha_composite(piece, (left, top))


def label(canvas: Image.Image, x: int, y: int, text: str, fill=(255, 255, 255, 255), back=(0, 0, 0, 190)) -> tuple[int, int]:
    """Draw `text` on a dark box with its top left at (x, y); returns the box's width and height."""
    width, height = text_width(text) + 4, LINE_HEIGHT + 2
    box = Image.new("RGBA", (width, height), back)
    ImageDraw.Draw(box).text((2, 0), text, font=FONT, fill=fill)
    blit(canvas, box, x, y)
    return width, height


def save_png(image: Image.Image, path: Path | str) -> Path:
    """Write `image` as a PNG the same way every time: no metadata, a fixed compression."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", compress_level=6)
    return path

"""A tileset drawn as a contact sheet: every tile enlarged, with its id and name, to check names against art.

A name is only as good as the picture it sits under, and a table of ids can't show that a tree's two
halves are swapped. The sheet puts them side by side: the id and name under each tile, a red border on
the tiles that carry a marked property (by default ``walkable = false``), and each piece and nine-slice
outlined in a colour of its own, numbered, with a key at the bottom.
"""

from __future__ import annotations

import math

from PIL import Image, ImageDraw

from tyled.mapfile import LoadedTileset, load_tileset
from tyled.render.draw import CHAR_WIDTH, FONT, LINE_HEIGHT, RenderError, blit, label, text_width
from tyled.tileset.names import NineSlice, Piece

BACKGROUND = (38, 38, 42)
TEXT = (232, 232, 232)
MARK = (230, 40, 40)
CHECKER = ((226, 226, 226), (246, 246, 246))
PIECE_COLOURS = [
    (255, 196, 0), (0, 190, 255), (255, 60, 200), (110, 235, 0), (255, 120, 0),
    (150, 110, 255), (0, 230, 150), (255, 255, 255), (255, 90, 90), (0, 120, 255),
]
PAD = 6
MIN_CELL = 48
DEFAULT_COLUMNS = 8
DEFAULT_MARK = ("walkable", False)


def render_sheet(
    tileset,
    *,
    scale: int = 4,
    columns: int | None = None,
    mark: tuple[str, object] | None = DEFAULT_MARK,
) -> Image.Image:
    """Draw a tileset as an RGB contact sheet.

    `tileset` is the path of a ``.tsx`` (or ``.tsj``), or a `LoadedTileset`. Tiles are enlarged `scale`
    times (nearest-neighbour) and laid out `columns` to a row: the tileset's own columns when it is a grid
    (so the sheet looks like its image), else 8. `mark` is a ``(property, value)`` pair: tiles with that
    property are bordered in red; None marks nothing.
    """
    loaded = tileset if isinstance(tileset, LoadedTileset) else load_tileset(tileset)
    if isinstance(scale, bool) or not isinstance(scale, int) or scale < 1:
        raise RenderError(f"scale must be a whole number of 1 or more, not {scale!r}")
    ids = loaded.ids()
    if not ids:
        raise RenderError(f"tileset {loaded.name!r} has no tiles with a picture to draw")
    if columns is None:
        columns = loaded.columns if loaded.columns > 0 else DEFAULT_COLUMNS
    if isinstance(columns, bool) or not isinstance(columns, int) or columns < 1:
        raise RenderError(f"columns must be a whole number of 1 or more, not {columns!r}")

    pictures = {id: loaded.tile_image(id) for id in ids}
    sizes = [p.size for p in pictures.values() if p is not None] or [(loaded.tilewidth or 1, loaded.tileheight or 1)]
    box_w, box_h = max(w for w, _ in sizes) * scale, max(h for _, h in sizes) * scale
    cell_w = max(box_w, MIN_CELL)

    # Where each tile goes: a grid tileset keeps the place it has in its image, so the sheet reads like it.
    if loaded.columns > 0 and loaded.columns == columns:
        place = {id: (id % columns, id // columns) for id in ids}
    else:
        columns = min(columns, len(ids))
        place = {id: (n % columns, n // columns) for n, id in enumerate(ids)}
    first_row = min(r for _, r in place.values())
    rows = max(r for _, r in place.values()) - first_row + 1

    captions = {id: _wrap(f"{id} {loaded.tile_name(id)}" if loaded.tile_name(id) else str(id), cell_w // CHAR_WIDTH) for id in ids}
    caption_lines = max(len(lines) for lines in captions.values())
    cell_h = box_h + 3 + caption_lines * LINE_HEIGHT

    def origin(id):
        column, row = place[id]
        return PAD + column * (cell_w + PAD), PAD + (row - first_row) * (cell_h + PAD)

    pieces = [p for p in loaded.named.pieces() if any(i in place for r in p.ids for i in r if i is not None)]
    key = _key_lines(loaded, pieces, mark)
    key_width = max(text_width(text) for _, text in key) + 22
    width = max(PAD + columns * (cell_w + PAD), key_width + 2 * PAD)
    key_columns = max(1, (width - PAD) // (key_width + PAD))
    key_rows = math.ceil(len(key) / key_columns)
    body = PAD + rows * (cell_h + PAD)
    sheet = Image.new("RGBA", (width, body + key_rows * (LINE_HEIGHT + 3) + PAD), BACKGROUND + (255,))
    draw = ImageDraw.Draw(sheet)

    for id in ids:
        x, y = origin(id)
        _checker(sheet, x, y, cell_w, box_h, scale)
        picture = pictures[id]
        if picture is not None:
            big = picture.resize((picture.width * scale, picture.height * scale), Image.Resampling.NEAREST)
            blit(sheet, big, x + (cell_w - big.width) // 2, y + (box_h - big.height) // 2)
        if mark is not None and loaded.tile_properties(id).get(mark[0], _MISSING) == mark[1]:
            draw.rectangle([x, y, x + cell_w - 1, y + box_h - 1], outline=MARK, width=2)
        for line, text in enumerate(captions[id]):
            draw.text((x, y + box_h + 3 + line * LINE_HEIGHT), text, font=FONT, fill=TEXT)

    # Outlines: a tile in several pieces gets a nested outline for each, so none hides another.
    depth: dict[int, int] = {}
    tags: dict[int, int] = {}
    for number, piece in enumerate(pieces, 1):
        colour = PIECE_COLOURS[(number - 1) % len(PIECE_COLOURS)]
        cells = [(i, place[i]) for row in piece.ids for i in row if i is not None and i in place]
        for id in dict.fromkeys(i for i, _ in cells):
            _outline(draw, origin(id), cell_w, box_h, 2 + 3 * depth.get(id, 0), colour)
            depth[id] = depth.get(id, 0) + 1
        first = min((cell for _, cell in cells), key=lambda c: (c[1], c[0]))
        first_id = next(i for i, cell in cells if cell == first)
        x, y = origin(first_id)
        tag_x = x + tags.get(first_id, 0)
        width_used, _ = label(sheet, tag_x, y, str(number), fill=(0, 0, 0, 255), back=colour + (255,))
        tags[first_id] = tags.get(first_id, 0) + width_used + 1

    for index, (colour, text) in enumerate(key):
        column, row = index % key_columns, index // key_columns
        x, y = PAD + column * (key_width + PAD), body + row * (LINE_HEIGHT + 3)
        if colour is not None:
            draw.rectangle([x, y + 1, x + 12, y + LINE_HEIGHT - 2], outline=colour, width=2)
        draw.text((x + 18, y), text, font=FONT, fill=TEXT)
    return sheet.convert("RGB")


_MISSING = object()


def _wrap(text: str, chars: int) -> list[str]:
    """`text` in lines of at most `chars` characters, broken after an underscore or space where it can be."""
    chars = max(chars, 4)
    lines: list[str] = []
    line = ""
    for word in text.replace("_", "_\0").replace(" ", " \0").split("\0"):
        while len(word) > chars:  # one long word: break it hard
            room = chars - len(line)
            if room > 0:
                line, word = line + word[:room], word[room:]
            lines.append(line)
            line = ""
        if len(line) + len(word) > chars:
            lines.append(line)
            line = ""
        line += word
    if line:
        lines.append(line)
    return [ln.rstrip() for ln in lines]


def _checker(sheet: Image.Image, x: int, y: int, width: int, height: int, scale: int) -> None:
    """A light chequerboard behind a tile, so transparent parts show as transparent, whatever the art's colours."""
    square = max(scale * 2, 4)
    draw = ImageDraw.Draw(sheet)
    for top in range(0, height, square):
        for left in range(0, width, square):
            colour = CHECKER[((left // square) + (top // square)) % 2]
            draw.rectangle([x + left, y + top, min(x + left + square, x + width) - 1, min(y + top + square, y + height) - 1], fill=colour)


def _outline(draw: ImageDraw.ImageDraw, origin, width: int, height: int, inset: int, colour) -> None:
    x, y = origin
    if width - 2 * inset < 2 or height - 2 * inset < 2:
        return
    draw.rectangle([x + inset, y + inset, x + width - 1 - inset, y + height - 1 - inset], outline=colour, width=2)


def _key_lines(loaded: LoadedTileset, pieces: list[Piece], mark) -> list[tuple[tuple[int, int, int] | None, str]]:
    lines = []
    if mark is not None:
        value = str(mark[1]).lower() if isinstance(mark[1], bool) else mark[1]
        lines.append((MARK, f"{mark[0]} = {value}"))
    for number, piece in enumerate(pieces, 1):
        kind = " (nine-slice)" if isinstance(piece, NineSlice) else ""
        lines.append((PIECE_COLOURS[(number - 1) % len(PIECE_COLOURS)], f"{number} {piece.name}{kind}"))
    return lines or [(None, loaded.name)]

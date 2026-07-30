import os
import re
from dataclasses import dataclass
from typing import List, Tuple

import cv2
import numpy as np
from PIL import Image
from rectpack import newPacker

from tyled import Tile, Tileset


def _slug(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "sheet"


class SheetTileset(Tileset):
    """
    Build a tileset from a single RGBA sheet PNG by:
      - detecting sprites via OpenCV contours on alpha channel
      - extracting each bbox as its own PNG (trimmed)
      - packing extracted PNGs into a new atlas PNG
      - exporting tileset metadata (tsx) using your existing Tile/Tileset machinery
    """

    def __init__(self, *config, **kwargs):
        super().__init__(*config, **kwargs)
        self.add_template_path("sheet/templates")

        # For debugging / optional manifest later
        self._rects: List[Tuple[int, int, int, int]] = []  # (x, y, w, h)

    @classmethod
    def create(cls, *config, **kwargs):
        ts = cls(*config, **kwargs)
        ts.build()
        return ts

    # ----------------------------
    # Options helpers
    # ----------------------------
    def _opt(self, name: str, default):
        return getattr(self.options, name, default)

    def _out_dir(self) -> str:
        """
        Where we write extracted crops. Defaults to: <cwd>/<name>_tiles/
        You can override with options.tiles_dir if you want.
        """
        d = self._opt("tiles_dir", f"{self.name}_tiles")
        os.makedirs(d, exist_ok=True)
        return d

    # ----------------------------
    # Build: detect + extract -> Tiles
    # ----------------------------
    def build(self):
        """
        `self.source` is expected to be a single PNG path (sheet).
        """
        sheet_path = self.source
        if not os.path.isfile(sheet_path):
            raise FileNotFoundError(f"Sheet source not found: {sheet_path}")

        sheet_bgra = cv2.imread(sheet_path, cv2.IMREAD_UNCHANGED)
        if sheet_bgra is None:
            raise RuntimeError(f"OpenCV failed to read: {sheet_path}")
        if sheet_bgra.ndim != 3 or sheet_bgra.shape[2] != 4:
            raise ValueError(f"Sheet must be RGBA (have alpha channel): {sheet_path}")

        H, W, _ = sheet_bgra.shape

        # Alpha mask -> binary
        alpha = sheet_bgra[:, :, 3]
        alpha_threshold = int(self._opt("alpha_threshold", 8))
        _, mask = cv2.threshold(alpha, alpha_threshold, 255, cv2.THRESH_BINARY)

        # Optional morphology to remove specks / close small gaps
        morph_open = int(self._opt("morph_open", 0))   # 0 disables
        morph_close = int(self._opt("morph_close", 0)) # 0 disables

        if morph_open > 0:
            k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (morph_open, morph_open))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)

        if morph_close > 0:
            k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (morph_close, morph_close))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        min_area = int(self._opt("min_area", 16))
        min_w = int(self._opt("min_width", 1))
        min_h = int(self._opt("min_height", 1))
        padding = int(self._opt("padding", 0))

        rects: List[Tuple[int, int, int, int]] = []
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            if w < min_w or h < min_h:
                continue
            if w * h < min_area:
                continue

            if padding:
                x0 = max(0, x - padding)
                y0 = max(0, y - padding)
                x1 = min(W, x + w + padding)
                y1 = min(H, y + h + padding)
                x, y, w, h = x0, y0, (x1 - x0), (y1 - y0)

            rects.append((x, y, w, h))

        # Stable order (top->bottom, left->right)
        rects.sort(key=lambda r: (r[1], r[0]))
        self._rects = rects

        # Convert to PIL RGBA once; crop via PIL for accurate alpha
        sheet_rgba = cv2.cvtColor(sheet_bgra, cv2.COLOR_BGRA2RGBA)
        sheet_img = Image.fromarray(sheet_rgba, mode="RGBA")

        out_dir = self._out_dir()
        base = _slug(os.path.splitext(os.path.basename(sheet_path))[0])
        prefix = self._opt("name_prefix", base)

        self.tiles = []
        id = 0

        for i, (x, y, w, h) in enumerate(rects):
            kind = f"{prefix}_{i:04d}"
            crop = sheet_img.crop((x, y, x + w, y + h))

            # Write extracted sprite so your Tile class can load it from disk
            crop_path = os.path.join(out_dir, f"{kind}.png")
            crop.save(crop_path)

            tile = Tile(crop_path, id, kind)

            # Optional: keep original sheet rect if you ever want it in export/template
            tile.sheet_x = x
            tile.sheet_y = y
            tile.sheet_w = w
            tile.sheet_h = h

            self.tiles.append(tile)
            id += 1

        self.tilecount = len(self.tiles)

    # ----------------------------
    # Bake: pack extracted tiles into atlas
    # ----------------------------
    def do_bake(self):
        rotation = bool(self._opt("rotation", False))
        packer = newPacker(rotation=rotation)

        for tile in self.tiles:
            packer.add_rect(tile.width, tile.height, tile)

        packer.add_bin(int(self.width), int(self.height))
        packer.pack()

        canvas = Image.new("RGBA", (int(self.width), int(self.height)), (0, 0, 0, 0))

        # Keep your previous y-flip convention so your TSX export remains consistent.
        for abin in packer:
            for rect in abin:
                tile: Tile = rect.rid
                x = int(rect.x)
                y = int(rect.y)
                w = int(rect.width)
                h = int(rect.height)

                draw_pos = (x, int(self.height) - y - h)

                if rotation and tile.width != tile.height and tile.width == h:
                    tile.place(draw_pos, 90)
                    self._draw_tile_rgba(canvas, tile, draw_pos, 90)
                else:
                    tile.place(draw_pos, 0)
                    self._draw_tile_rgba(canvas, tile, draw_pos, 0)

        if self._opt("show", False):
            canvas.show()

        if self._opt("save", True):
            canvas.save(f"{self.name}.png")
            self.export()

    @staticmethod
    def _draw_tile_rgba(canvas: Image.Image, tile: Tile, position: Tuple[int, int], angle: int = 0) -> None:
        """
        Correct RGBA paste (your current Tile.draw() drops alpha because it doesn't pass a mask).
        We keep Tile.place() for metadata, but draw with proper compositing here.
        """
        im = tile.image
        if angle:
            im = im.rotate(angle, expand=True)

        # Use the image as its own mask for alpha
        canvas.paste(im, position, im)

import os
import re
from typing import List, Tuple

import cv2
from PIL import Image

from tyled import Tile, Tileset


def _slug(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "sheet"


class SliceTileset(Tileset):
    """
    Build a tileset from a single RGBA sheet PNG by:
      - detecting sprites via OpenCV contours on alpha channel
      - extracting each bbox as its own PNG (trimmed)
      - exporting tileset metadata (tsx) using collection templates
    """

    def __init__(self, *config, **kwargs):
        super().__init__(*config, **kwargs)
        # You said you reused CollectionTileset Jinja templates.
        # Ensure this points at those templates.
        self.add_template_path("collection/templates")

        self._rects: List[Tuple[int, int, int, int]] = []  # (x, y, w, h)

    @classmethod
    def create(cls, *config, **kwargs):
        ts = cls(*config, **kwargs)
        ts.build()
        return ts

    def _opt(self, name: str, default):
        return getattr(self.options, name, default)

    def _out_dir(self) -> str:
        d = self._opt("tiles_dir", f"{self.name}_tiles")
        os.makedirs(d, exist_ok=True)
        return d

    def build(self):
        """
        `self.source` is expected to be a single PNG path (sheet).
        Writes per-sprite PNGs into tiles_dir and creates Tile objects for them.
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

        alpha = sheet_bgra[:, :, 3]
        alpha_threshold = int(self._opt("alpha_threshold", 8))
        _, mask = cv2.threshold(alpha, alpha_threshold, 255, cv2.THRESH_BINARY)

        morph_open = int(self._opt("morph_open", 0))
        morph_close = int(self._opt("morph_close", 0))

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

        rects.sort(key=lambda r: (r[1], r[0]))
        self._rects = rects

        # Convert BGRA -> RGBA and crop with PIL
        sheet_rgba = cv2.cvtColor(sheet_bgra, cv2.COLOR_BGRA2RGBA)
        sheet_img = Image.fromarray(sheet_rgba, mode="RGBA")

        out_dir = self._out_dir()
        base = _slug(os.path.splitext(os.path.basename(sheet_path))[0])
        prefix = self._opt("name_prefix", base)

        self.tiles = []
        gid = int(self.firstgid)

        max_w = 1
        max_h = 1

        for i, (x, y, w, h) in enumerate(rects):
            kind = f"{prefix}_{i:04d}"
            crop = sheet_img.crop((x, y, x + w, y + h))

            crop_path = os.path.join(out_dir, f"{kind}.png")
            crop.save(crop_path)

            tile = Tile(crop_path, gid, kind)

            # Optional provenance (not required by Tiled)
            tile.sheet_x = x
            tile.sheet_y = y
            tile.sheet_w = w
            tile.sheet_h = h

            self.tiles.append(tile)
            gid += 1

            if tile.width > max_w:
                max_w = tile.width
            if tile.height > max_h:
                max_h = tile.height

        self.tilecount = len(self.tiles)

        # IMPORTANT: collection tilesets still need valid tilewidth/tileheight in TSX.
        # Using max dimensions is typical.
        self.tilewidth = max_w
        self.tileheight = max_h

        # Collection tilesets normally set columns=0
        self.columns = 0

    def do_bake(self):
        """
        No packing, no atlas image. Just export the TSX using the collection templates.
        """
        self.export()

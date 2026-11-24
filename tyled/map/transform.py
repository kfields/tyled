"""Rotating and flipping tiles the way Tiled does: with flag bits on the global tile id.

Tiled keeps three flags in the top bits of a gid. Applied in this order they turn the tile's image:
the diagonal flag transposes it (mirrors it across the top-left to bottom-right diagonal), then the
horizontal flag mirrors it left to right, then the vertical flag mirrors it top to bottom. Eight
combinations make every way of turning a square: four rotations, each with or without a mirror.

A legend entry says what it wants as a clockwise rotation (0, 90, 180, 270) and a flip (``h``, ``v``,
``hv``, done after the rotation, on the picture as it then is). `Transform` turns that into the flags,
can be put after another one (a tile that is already flagged, in a piece), and can turn a whole grid of
tiles (a piece or a nine-slice) as one picture.
"""

from __future__ import annotations

from dataclasses import dataclass

FLIP_HORIZONTAL = 0x80000000
FLIP_VERTICAL = 0x40000000
FLIP_DIAGONAL = 0x20000000
FLAGS = FLIP_HORIZONTAL | FLIP_VERTICAL | FLIP_DIAGONAL

Matrix = tuple[tuple[int, int], tuple[int, int]]


def _multiply(a: Matrix, b: Matrix) -> Matrix:
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(2)) for j in range(2)) for i in range(2))  # type: ignore[return-value]


_D: Matrix = ((0, 1), (1, 0))
_H: Matrix = ((-1, 0), (0, 1))
_V: Matrix = ((1, 0), (0, -1))
_I: Matrix = ((1, 0), (0, 1))


@dataclass(frozen=True)
class Transform:
    """A turn of a square: which of Tiled's three flags are set (diagonal first, then h, then v)."""

    diagonal: bool = False
    horizontal: bool = False
    vertical: bool = False

    @classmethod
    def of(cls, rotate: int = 0, flip: str = "") -> "Transform":
        """The transform for a clockwise `rotate` of 0, 90, 180 or 270 degrees, then a `flip`.

        Clockwise 90 is the diagonal and horizontal flags; 180 is horizontal and vertical; 270 is
        diagonal and vertical. A flip afterwards just toggles the horizontal or vertical flag, because
        those come last in Tiled's order.
        """
        if isinstance(rotate, bool) or rotate not in (0, 90, 180, 270):
            raise ValueError(f"rotate must be 0, 90, 180 or 270, not {rotate!r}")
        if not isinstance(flip, str) or set(flip) - set("hv") or len(set(flip)) != len(flip):
            raise ValueError(f"flip must be 'h', 'v' or 'hv', not {flip!r}")
        base = {
            0: cls(),
            90: cls(diagonal=True, horizontal=True),
            180: cls(horizontal=True, vertical=True),
            270: cls(diagonal=True, vertical=True),
        }[rotate]
        return cls(base.diagonal, base.horizontal != ("h" in flip), base.vertical != ("v" in flip))

    @classmethod
    def from_gid(cls, gid: int) -> "Transform":
        return cls(bool(gid & FLIP_DIAGONAL), bool(gid & FLIP_HORIZONTAL), bool(gid & FLIP_VERTICAL))

    @property
    def flags(self) -> int:
        return (
            (FLIP_DIAGONAL if self.diagonal else 0)
            | (FLIP_HORIZONTAL if self.horizontal else 0)
            | (FLIP_VERTICAL if self.vertical else 0)
        )

    @property
    def is_identity(self) -> bool:
        return not (self.diagonal or self.horizontal or self.vertical)

    @property
    def matrix(self) -> Matrix:
        m = _I
        if self.diagonal:
            m = _multiply(_D, m)
        if self.horizontal:
            m = _multiply(_H, m)
        if self.vertical:
            m = _multiply(_V, m)
        return m

    @classmethod
    def from_matrix(cls, matrix: Matrix) -> "Transform":
        for d in (False, True):
            for h in (False, True):
                for v in (False, True):
                    candidate = cls(d, h, v)
                    if candidate.matrix == matrix:
                        return candidate
        raise ValueError(f"{matrix} is not a turn of a square")  # pragma: no cover

    def then(self, other: "Transform") -> "Transform":
        """This transform followed by `other`: a tile already flagged, turned again."""
        return Transform.from_matrix(_multiply(other.matrix, self.matrix))

    def apply_to_gid(self, gid: int) -> int:
        """`gid` (flags included) turned by this transform; the tile id part is left alone."""
        turned = Transform.from_gid(gid).then(self)
        return (gid & ~FLAGS) | turned.flags

    def apply_to_grid(self, grid, anchor):
        """Turn a grid of tile ids (None for gaps) and the (column, row) of its anchor as one picture.

        Each cell moves to where the turn puts it and each tile id gets the flags that turn it the same
        way; the result is a tuple of rows and the anchor's new place. A turn by the diagonal swaps the
        grid's width and height.
        """
        height, width = len(grid), len(grid[0])
        new_width, new_height = (height, width) if self.diagonal else (width, height)
        (a, b), (c, d) = self.matrix
        out: list[list[int | None]] = [[None] * new_width for _ in range(new_height)]

        def moved(column, row):
            # Doubled coordinates from the centre, so the half-cell offsets of even sizes stay whole.
            x, y = 2 * column - (width - 1), 2 * row - (height - 1)
            nx, ny = a * x + b * y, c * x + d * y
            return (nx + new_width - 1) // 2, (ny + new_height - 1) // 2

        for row in range(height):
            for column in range(width):
                cell = grid[row][column]
                if cell is not None:
                    new_column, new_row = moved(column, row)
                    out[new_row][new_column] = self.apply_to_gid(cell)
        return tuple(tuple(r) for r in out), moved(*anchor)

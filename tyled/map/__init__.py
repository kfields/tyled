"""Maps from text layouts: a character a tile, turned into a Tiled ``.tmj``.

`build` is the one call most programs need (`build_all` also says every file it wrote); `MapProject` is what it uses, for a program that wants the
map as data (`to_dict`) or as text (`to_json`) instead of a file.
"""

from tyled.map.builder import MapError, MapProject, build, build_all
from tyled.map.transform import Transform

__all__ = ["MapError", "MapProject", "Transform", "build", "build_all"]

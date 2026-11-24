"""`tyled render` and `tyled sheet`: maps and tilesets drawn to images, held to golden PNGs."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner
from PIL import Image

from bakehelp import FIXTURES, GOLDEN, bake_fixture
from test_areas import town as areas_town  # noqa: F401  (a function that makes a project of four areas)
from test_map import town, world  # noqa: F401  (the town example, built; a baked test tileset)
from tyled.command import cli
from tyled.map import build_all
from tyled.mapfile import MapFileError, load_map, load_tileset
from tyled.render import RenderError, render_map, render_sheet, save_png

D, H, V = 0x20000000, 0x80000000, 0x40000000
RENDER = GOLDEN / "render"


def colours_of(image):
    return {colour for _, colour in image.convert("RGB").getcolors(maxcolors=1 << 20)}


def assert_same_picture(image, name):
    """`image` is tests/golden/render/<name>, pixel for pixel."""
    want = Image.open(RENDER / name).convert(image.mode)
    assert image.size == want.size, f"{name}: {image.size} is not {want.size}"
    assert image.tobytes() == want.tobytes(), f"{name} differs in pixels"


# ---- a small hand-made tileset and map, for what flat colours can't show

# Tile 0 is 4 × 4 with every pixel a different colour, so any turn of it is told from any other. Tile 1 is
# a flat one, tile 2 is 4 × 8 (taller than a cell) and comes from a file of its own, as in a collection.
def pixel(x, y):
    return (40 + 50 * x, 40 + 50 * y, 200 - 20 * (x + y), 255)


def make_tileset(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    glyph = Image.new("RGBA", (4, 4))
    for y in range(4):
        for x in range(4):
            glyph.putpixel((x, y), pixel(x, y))
    flat = Image.new("RGBA", (4, 4), (250, 10, 10, 255))
    sheet = Image.new("RGBA", (8, 4))
    sheet.paste(glyph, (0, 0))
    sheet.paste(flat, (4, 0))
    sheet.save(folder / "glyphs.png")
    tall = Image.new("RGBA", (4, 8), (10, 200, 10, 255))
    tall.putpixel((0, 0), (255, 255, 255, 255))
    tall.save(folder / "tall.png")
    (folder / "glyphs.tsx").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<tileset version="1.10" name="glyphs" tilewidth="4" tileheight="4" tilecount="2" columns="2">\n'
        ' <image source="glyphs.png" width="8" height="4"/>\n'
        '</tileset>\n'
    )
    (folder / "tall.tsx").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<tileset version="1.10" name="tall" tilewidth="4" tileheight="8" tilecount="1" columns="0">\n'
        ' <tile id="0"><image width="4" height="8" source="tall.png"/></tile>\n'
        '</tileset>\n'
    )
    return folder


def tile_layer(name, width, height, data, **extra):
    return {"type": "tilelayer", "name": name, "width": width, "height": height, "data": data, **extra}


def tile_object(id, gid, x, y, **extra):
    return {"id": id, "name": f"o{id}", "type": "thing", "gid": gid, "x": x, "y": y, "width": 4, "height": 4,
            "rotation": 0, "visible": True, **extra}


def write_map(folder: Path, layers, width, height, name="m.tmj", tilesets=("glyphs.tsx", "tall.tsx")):
    make_tileset(folder)
    firstgids = {"glyphs.tsx": 1, "tall.tsx": 3}
    tree = {"type": "map", "orientation": "orthogonal", "infinite": False, "width": width, "height": height,
            "tilewidth": 4, "tileheight": 4, "layers": layers,
            "tilesets": [{"firstgid": firstgids[t], "source": t} for t in tilesets]}
    path = folder / name
    path.write_text(json.dumps(tree))
    return path


def glyph():
    image = Image.new("RGBA", (4, 4))
    for y in range(4):
        for x in range(4):
            image.putpixel((x, y), pixel(x, y))
    return image


def flags_image(folder: Path):
    """Glyph tiles with each of the eight combinations of flags, then the plain one: a row of nine."""
    combos = [0, D, H, V, D | H, H | V, D | V, D | H | V]
    data = [1 | flags for flags in combos]
    path = write_map(folder, [tile_layer("ground", 8, 1, data)], 8, 1)
    return render_map(path, scale=4)


def objects_image(folder: Path):
    """Tile objects: plain, squeezed, turned a quarter, and two overlapping in an order other than their listing."""
    objects = [
        tile_object(1, 1, 4, 8),                                        # a tile object's origin is its bottom left
        tile_object(2, 3, 12, 8, width=8, height=8),                    # the tall tile, squeezed to 8 × 8
        tile_object(3, 1, 20, 8, rotation=90),                          # turned clockwise about (20, 8)
        tile_object(4, 2, 4, 20),                                       # the red square, with its foot lower: on top...
        tile_object(5, 1, 6, 18),                                       # ...though this one is listed after it
    ]
    layers = [tile_layer("ground", 8, 6, [0] * 48), {"type": "objectgroup", "name": "objects", "objects": objects}]
    return render_map(write_map(folder, layers, 8, 6), scale=4)


# ---- C1: a map drawn

def test_the_town_is_drawn_the_same_as_its_golden_picture(town):
    path = build_all("town.toml")[0]
    assert_same_picture(render_map(path), "town.png")


def test_a_region_is_a_part_of_the_town_drawn_the_same_as_its_golden_picture(town):
    path = build_all("town.toml")[0]
    part = render_map(path, scale=4, region=(10, 7, 8, 6))
    assert part.size == (8 * 16 * 4, 6 * 16 * 4)
    assert_same_picture(part, "town-region.png")
    whole = render_map(path, scale=4)
    assert part.tobytes() == whole.crop((10 * 64, 7 * 64, 18 * 64, 13 * 64)).tobytes()


def test_flags_turn_a_tile_as_tiled_does_and_the_picture_matches_its_golden(tmp_path):
    image = flags_image(tmp_path / "flags")
    assert_same_picture(image, "flags.png")

    def cell(n):  # the n-th cell, shrunk back to the tile's own pixels
        return image.crop((n * 16, 0, n * 16 + 16, 16)).resize((4, 4), Image.Resampling.NEAREST)

    tile = glyph()
    assert cell(0).tobytes() == tile.tobytes()
    assert cell(1).tobytes() == tile.transpose(Image.Transpose.TRANSPOSE).tobytes()  # diagonal: swap x and y
    assert cell(2).tobytes() == tile.transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes()
    assert cell(3).tobytes() == tile.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes()
    assert cell(4).tobytes() == tile.rotate(-90).tobytes()  # D + H is a quarter turn clockwise
    assert cell(5).tobytes() == tile.rotate(180).tobytes()
    assert cell(6).tobytes() == tile.rotate(90).tobytes()   # D + V is a quarter turn the other way


def test_tile_objects_are_drawn_from_their_bottom_left_and_the_picture_matches_its_golden(tmp_path):
    image = objects_image(tmp_path / "objects")
    assert_same_picture(image, "objects.png")

    def at(x, y, w=4, h=4):  # a rectangle of the map in pixels, shrunk to the tile's own
        return image.crop((x * 4, y * 4, (x + w) * 4, (y + h) * 4)).resize((w, h), Image.Resampling.NEAREST)

    assert at(4, 4).tobytes() == glyph().tobytes()                    # y = 8 is the bottom, so it stands in the row above
    assert at(12, 0, 8, 8).getpixel((0, 0)) == (255, 255, 255, 255)   # the tall tile's mark, at its top left
    assert at(12, 0, 8, 8).getpixel((7, 7)) == (10, 200, 10, 255)     # ...and it fills the 8 × 8 it was given
    # Turned a quarter clockwise about its bottom left corner, it lies to the right of and below that corner.
    assert at(20, 8).tobytes() == glyph().rotate(-90).tobytes()
    # The one with the lower foot is drawn on top, though it was listed first: Tiled's top-down order.
    assert at(7, 17, 1, 1).getpixel((0, 0)) == (250, 10, 10, 255)    # where they overlap, the red one's foot is lower
    assert at(6, 14).getpixel((0, 0)) == pixel(0, 0)                  # the other one's own corner, not covered


def test_a_tile_taller_than_its_cell_grows_upwards_from_the_cells_bottom(tmp_path):
    path = write_map(tmp_path, [tile_layer("ground", 2, 2, [0, 0, 0, 3])], 2, 2)
    image = render_map(path)
    assert image.getpixel((4, 4 - 4)) == (255, 255, 255, 255)  # its top row, one cell above the cell it is in
    assert image.getpixel((7, 7)) == (10, 200, 10, 255)
    assert image.getpixel((0, 0)) == (0, 0, 0, 0)


def test_scale_enlarges_without_blurring_and_the_default_is_a_whole_number(tmp_path):
    path = write_map(tmp_path, [tile_layer("ground", 2, 1, [1, 2])], 2, 1)
    one, three = render_map(path), render_map(path, scale=3)
    assert three.size == (one.width * 3, one.height * 3)
    assert three.tobytes() == one.resize(three.size, Image.Resampling.NEAREST).tobytes()
    for bad in (0, -1, 1.5, True):
        with pytest.raises(RenderError, match="scale"):
            render_map(path, scale=bad)


def test_a_region_off_the_map_is_refused(tmp_path):
    path = write_map(tmp_path, [tile_layer("ground", 4, 3, [1] * 12)], 4, 3)
    for region in [(0, 0, 5, 1), (3, 0, 2, 1), (0, 2, 1, 2), (-1, 0, 1, 1), (0, 0, 0, 1)]:
        with pytest.raises(RenderError, match="not inside the map, which is 4 × 3"):
            render_map(path, region=region)
    assert render_map(path, region=(3, 2, 1, 1)).size == (4, 4)


def test_layers_choose_what_is_drawn_and_hidden_layers_only_when_asked(tmp_path):
    layers = [
        tile_layer("ground", 1, 1, [1]),
        tile_layer("top", 1, 1, [2], visible=False),
        {"type": "objectgroup", "name": "objects", "objects": [tile_object(1, 2, 0, 4)]},
    ]
    path = write_map(tmp_path, layers, 1, 1)
    red, green = (250, 10, 10, 255), pixel(0, 0)
    assert render_map(path).getpixel((0, 0)) == red  # tile 2 (the red one) is on "top", which is hidden...
    assert render_map(path, layers=["ground"]).getpixel((0, 0)) == green
    assert render_map(path, layers=["objects", "ground"]).getpixel((0, 0)) == red  # the object, over the ground
    assert render_map(path, layers="top").getpixel((0, 0)) == red
    assert render_map(path, layers=[]).getpixel((0, 0)) == (0, 0, 0, 0)
    with pytest.raises(RenderError, match="no layer 'sky'; its layers are ground, top, objects"):
        render_map(path, layers=["ground", "sky"])


def test_a_layers_opacity_blends_it_over_what_is_below(tmp_path):
    layers = [tile_layer("ground", 1, 1, [2]), tile_layer("half", 1, 1, [1], opacity=0.5)]
    got = render_map(write_map(tmp_path, layers, 1, 1)).getpixel((0, 0))
    # Half of the glyph's corner (40, 40, 200) over red (250, 10, 10), and still opaque.
    assert got[3] == 255
    assert all(abs(g - w) <= 2 for g, w in zip(got, (145, 25, 105)))


def test_labels_and_the_grid_are_drawn_only_when_asked(tmp_path):
    objects = [tile_object(1, 1, 8, 8, name="lamp")]
    layers = [tile_layer("ground", 4, 4, [2] * 16), {"type": "objectgroup", "name": "objects", "objects": objects}]
    path = write_map(tmp_path, layers, 4, 4)
    plain = render_map(path, scale=4)
    marked = render_map(path, scale=4, labels=True)
    gridded = render_map(path, scale=4, grid=True)
    assert plain.tobytes() != marked.tobytes() != gridded.tobytes()
    assert marked.getpixel((8 * 4, 4 * 4)) == (255, 230, 0, 255)  # the object's outline: its top left corner
    assert plain.getpixel((16, 16)) == (250, 10, 10, 255) and gridded.getpixel((16, 16)) != (250, 10, 10, 255)
    assert gridded.getpixel((17, 17)) == (250, 10, 10, 255)  # the lines are the grid's, not a wash over everything
    assert render_map(path, scale=4, labels=False, grid=False).tobytes() == plain.tobytes()


def test_the_same_map_gives_the_same_png_bytes(tmp_path):
    path = write_map(tmp_path, [tile_layer("ground", 8, 1, [1 | f for f in (0, D, H, V, D | H, H | V, D | V, D | H | V)])], 8, 1)
    first = save_png(render_map(path, scale=3, grid=True), tmp_path / "one" / "a.png")
    second = save_png(render_map(path, scale=3, grid=True), tmp_path / "two" / "a.png")
    assert first.read_bytes() == second.read_bytes()


def test_a_world_is_drawn_as_its_maps_side_by_side_the_same_as_the_merged_map(areas_town, tmp_path):
    project = areas_town()
    written = build_all(project, tmp_path / "out" / "town.world", merged=True)
    from_world = render_map(written[0], scale=2)
    from_merged = render_map(written[-1], scale=2)
    assert from_world.size == (6 * 8 * 2, 4 * 8 * 2)
    assert from_world.tobytes() == from_merged.tobytes()
    assert (load_map(written[0]).width, load_map(written[0]).height) == (6, 4)
    # The areas share one tileset, so putting them together keeps one copy of it.
    assert len(load_map(written[0]).tilesets) == 1


def test_a_missing_tileset_picture_is_an_error_saying_which_and_what_to_do(tmp_path):
    path = write_map(tmp_path, [tile_layer("ground", 1, 1, [1])], 1, 1)
    (tmp_path / "glyphs.png").unlink()
    with pytest.raises(MapFileError, match="glyphs.png is missing.*baked"):
        render_map(path)


def test_a_map_that_is_not_there_or_not_json_or_infinite_is_refused(tmp_path):
    with pytest.raises(MapFileError, match="doesn't exist"):
        render_map(tmp_path / "nope.tmj")
    (tmp_path / "x.tmx").write_text("<map/>")
    with pytest.raises(MapFileError, match="tyled reads .tmj and .world"):
        render_map(tmp_path / "x.tmx")
    path = write_map(tmp_path, [tile_layer("ground", 1, 1, [1])], 1, 1)
    tree = json.loads(path.read_text())
    tree["infinite"] = True
    path.write_text(json.dumps(tree))
    with pytest.raises(MapFileError, match="infinite"):
        render_map(path)


def test_a_packed_tile_that_the_packer_turned_is_drawn_upright(tmp_path):
    """The rotation fixture's atlas has tiles stored turned by 90 degrees; they come out the way they went in."""
    tileset = load_tileset(GOLDEN / "rotation" / "rotation.tsx")
    for id, name in enumerate("abcd"):
        original = Image.open(FIXTURES / "rotation" / "tiles" / f"{name}.png").convert("RGBA")
        got = tileset.tile_image(id)
        assert got is not None and got.size == original.size, name
        assert got.tobytes() == original.tobytes(), name


# ---- C2: a contact sheet

@pytest.fixture
def grid_sheet(tmp_path, monkeypatch):
    """The grid fixture, baked: its .tsx, beside the image it refers to."""
    bake_fixture("grid", tmp_path, monkeypatch)
    return tmp_path / "work" / "grid.tsx"


def test_the_contact_sheet_of_a_tileset_matches_its_golden_picture(grid_sheet):
    assert_same_picture(render_sheet(grid_sheet), "sheet.png")


def test_the_contact_sheet_borders_tiles_with_the_marked_property_and_only_those(grid_sheet):
    red = (230, 40, 40)
    tileset = load_tileset(grid_sheet)
    assert [id for id in tileset.ids() if tileset.tile_properties(id).get("walkable") is False] == [1, 5]  # water, stall
    image = render_sheet(grid_sheet, scale=2)

    def corner(id):  # the top left pixel of a tile's box, in the first row: 4 columns, cells 48 wide (the least), 6 apart
        return image.getpixel((6 + id * (48 + 6), 6))

    assert corner(1) == red
    assert corner(0) != red and corner(2) != red and corner(3) != red
    assert render_sheet(grid_sheet, scale=2, mark=None).getpixel((6 + 54, 6)) != red
    assert render_sheet(grid_sheet, scale=2, mark=("kind", "food_stall")).getpixel((6 + 54, 6)) != red
    assert render_sheet(grid_sheet, scale=2, mark=("depth", 2)).getpixel((6 + 54, 6)) == red


def test_the_contact_sheet_outlines_each_piece_in_a_colour_of_its_own(grid_sheet, tmp_path):
    tileset = load_tileset(grid_sheet)
    assert [p.name for p in tileset.named.pieces()] == ["house", "roof"]
    colours = colours_of(render_sheet(grid_sheet, scale=2, mark=None))
    assert {(255, 196, 0), (0, 190, 255)} <= colours  # the first and second colours: house and roof
    plain = render_sheet(make_tileset(tmp_path / "plain") / "glyphs.tsx", scale=2, mark=None)
    assert not {(255, 196, 0), (0, 190, 255)} & colours_of(plain)  # a tileset without pieces has none


def test_the_contact_sheet_lays_tiles_out_in_the_columns_asked_for(tmp_path):
    work = make_tileset(tmp_path / "tiles")
    one = render_sheet(work / "glyphs.tsx", scale=1, columns=1, mark=None)
    two = render_sheet(work / "glyphs.tsx", scale=1, columns=2, mark=None)
    assert one.mode == "RGB"
    assert one.height > two.height and one.width < two.width
    assert render_sheet(work / "tall.tsx", scale=2).size[0] >= 6 + 48 + 6  # a tileset with no columns of its own: one tile, one cell
    with pytest.raises(RenderError, match="columns"):
        render_sheet(work / "glyphs.tsx", columns=0)
    with pytest.raises(RenderError, match="scale"):
        render_sheet(work / "glyphs.tsx", scale=0)


# ---- the commands

def test_render_writes_a_png_named_after_the_map_in_the_current_folder(tmp_path, monkeypatch):
    path = write_map(tmp_path / "src", [tile_layer("ground", 2, 2, [1, 2, 1, 2])], 2, 2)
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(cli, ["render", str(path)])
    assert result.exit_code == 0, result.output
    image = Image.open(tmp_path / "m.png")
    assert image.size == (2 * 4 * 2, 2 * 4 * 2)  # the default scale is 2
    out = tmp_path / "x" / "y.png"
    result = CliRunner().invoke(cli, ["render", str(path), "-o", str(out), "--scale", "1", "--region", "1,0,1,2",
                                      "--layers", "ground", "--labels", "--grid"])
    assert result.exit_code == 0, result.output
    assert Image.open(out).size == (4, 8)


def test_render_says_what_is_wrong_with_exit_status_2(tmp_path):
    path = write_map(tmp_path, [tile_layer("ground", 2, 2, [1, 2, 1, 2])], 2, 2)
    for args, text in [(["--region", "1,2"], "--region is 4 whole numbers"),
                       (["--region", "0,0,9,9"], "not inside the map"),
                       (["--layers", "sky"], "no layer 'sky'"),
                       (["--scale", "0"], "scale")]:
        result = CliRunner().invoke(cli, ["render", str(path), "-o", str(tmp_path / "o.png"), *args])
        assert result.exit_code == 2 and text in result.output, (args, result.output)
    assert not (tmp_path / "o.png").exists()


def test_sheet_writes_a_png_and_marks_what_it_is_asked_to(grid_sheet, tmp_path):
    out = tmp_path / "sheet.png"
    result = CliRunner().invoke(cli, ["sheet", str(grid_sheet), "-o", str(out), "--scale", "2"])
    assert result.exit_code == 0, result.output
    assert Image.open(out).convert("RGB").tobytes() == render_sheet(grid_sheet, scale=2).tobytes()
    for mark, mark_arg in [("none", None), ("kind=food_stall", ("kind", "food_stall")), ("depth=2", ("depth", 2)),
                           ("speed=0.5", ("speed", 0.5))]:
        CliRunner().invoke(cli, ["sheet", str(grid_sheet), "-o", str(out), "--scale", "2", "--mark", mark])
        assert Image.open(out).convert("RGB").tobytes() == render_sheet(grid_sheet, scale=2, mark=mark_arg).tobytes(), mark
    bad = CliRunner().invoke(cli, ["sheet", str(grid_sheet), "--mark", "walkable"])
    assert bad.exit_code == 2 and "PROPERTY=VALUE" in bad.output

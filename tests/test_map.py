"""`tyled map`: a map from a text layout, written as a Tiled .tmj."""

import json
import shutil
import tomllib
from pathlib import Path

import pytest
from click.testing import CliRunner

from bakehelp import GOLDEN
from test_named_tiles import EXAMPLES, TINY_TOWN_IMAGE, make_grid_image
from tyled.command import cli
from tyled.map import MapError, MapProject, Transform, build
from tyled.map.transform import FLIP_DIAGONAL as D, FLIP_HORIZONTAL as H, FLIP_VERTICAL as V
from tyled.tileset.factory import TilesetFactory

# A small tileset for the tests: 4 × 5 tiles of 8 px, ids 0 to 19.
#
#   0 grass   1 road   2 wall (blocks)   3 flower (its own layer)
#   4 stall (blocks, kind food_stall)   5 arch   6 lamp (kind lamp)   7 door
#   8-10, 12-14, 16-18: the nine-slice 'plaza', its edges block and its centre (13) doesn't
SHEET = """
name = 'sheet'
type = 'grid'
source = 'sheet.png'
tilewidth = 8
tileheight = 8

[defaults]
walkable = true

[[tiles]]
at = [0, 0]
name = 'grass'
[[tiles]]
at = [1, 0]
name = 'road'
[[tiles]]
at = [2, 0]
name = 'wall'
properties = { walkable = false }
[[tiles]]
at = [3, 0]
name = 'flower'
properties = { layer = 'decor' }
[[tiles]]
at = [0, 1]
name = 'stall'
properties = { walkable = false, kind = 'food_stall' }
[[tiles]]
at = [1, 1]
name = 'arch'
[[tiles]]
at = [2, 1]
name = 'lamp'
properties = { kind = 'lamp' }
[[tiles]]
at = [3, 1]
name = 'door'
[[tiles]]
region = [0, 2, 3, 3]
properties = { walkable = false }
[[tiles]]
at = [1, 3]
properties = { walkable = true }

[[pieces]]
name = 'house'
rows = [['wall', 'wall'], ['wall', 'door']]
anchor = [1, 1]
[[pieces]]
name = 'tall'
rows = [['lamp'], ['flower']]
anchor = [0, 1]
[[pieces]]
name = 'gappy'
rows = [['wall', ''], ['wall', 'wall']]
[[pieces]]
name = 'plaza'
kind = 'nine_slice'
region = [0, 2, 3, 3]
"""

EXTRA = """
name = 'extra'
type = 'grid'
source = 'extra.png'
tilewidth = 8
tileheight = 8
[[tiles]]
at = [0, 0]
name = 'moss'
[[tiles]]
at = [1, 0]
name = 'grass'
"""

ID = {"grass": 0, "road": 1, "wall": 2, "flower": 3, "stall": 4, "arch": 5, "lamp": 6, "door": 7}


def gid(name, flags=0):
    return ID[name] + 1 + flags  # the first tileset starts at gid 1


@pytest.fixture
def world(tmp_path, monkeypatch):
    """A folder holding the baked test tileset, and a function that makes a map project there."""
    work = tmp_path / "work"
    work.mkdir()
    make_grid_image(work / "sheet.png", columns=4, rows=5, size=8)
    make_grid_image(work / "extra.png", columns=2, rows=1, size=8)
    (work / "sheet.toml").write_text(SHEET)
    (work / "extra.toml").write_text(EXTRA)
    monkeypatch.chdir(work)
    for name in ("sheet", "extra"):
        with open(f"{name}.toml", "rb") as fh:
            TilesetFactory().produce(tomllib.load(fh), options={"save": True}).bake()

    def make(layout, legend=None, tilesets=("sheet.toml",), **project):
        (work / "m.txt").write_text(layout)
        config = dict(name="m", tilewidth=8, tileheight=8, layout="m.txt", tilesets=list(tilesets),
                      legend=legend or {}, **project)
        return MapProject(config, base=work)

    make.work = work
    return make


def layer(tmj, name):
    """A layer's tile ids as rows (the raw gids, flags included)."""
    found = next(l for l in tmj["layers"] if l["name"] == name)
    width = found["width"]
    return [found["data"][i:i + width] for i in range(0, len(found["data"]), width)]


# ---- C1: the project, the tmj

def test_a_map_is_a_tmj_with_the_layers_tilesets_and_sizes_of_the_project(world):
    tmj = world("..\n..\n", {}, fill="grass").to_dict()
    assert (tmj["width"], tmj["height"], tmj["tilewidth"], tmj["tileheight"]) == (2, 2, 8, 8)
    assert (tmj["type"], tmj["orientation"], tmj["infinite"], tmj["version"]) == ("map", "orthogonal", False, "1.10")
    assert [l["name"] for l in tmj["layers"]] == ["ground", "obstacles", "objects"]
    assert [l["type"] for l in tmj["layers"]] == ["tilelayer", "tilelayer", "objectgroup"]
    assert tmj["nextlayerid"] == 4 and tmj["nextobjectid"] == 1
    assert tmj["tilesets"] == [{"firstgid": 1, "source": str(world.work / "sheet.tsx")}]


def test_tilesets_get_their_firstgids_in_order_as_tiled_gives_them(world):
    project = world(".m\n", {"m": "moss"}, tilesets=("sheet.toml", "extra.tsx"))
    tmj = project.to_dict()
    assert [t["firstgid"] for t in tmj["tilesets"]] == [1, 21]  # the first tileset has 20 tiles
    assert layer(tmj, "ground")[0] == [0, 21]  # moss is tile 0 of the second tileset


def test_tileset_sources_are_written_relative_to_the_map(world, tmp_path):
    out = world(".\n", {}).write(world.work / "maps" / "m.tmj")
    assert json.loads(out.read_text())["tilesets"][0]["source"] == "../sheet.tsx"


def test_a_tileset_project_that_was_not_baked_is_an_error_saying_so(world):
    (world.work / "sheet.tsx").unlink()
    with pytest.raises(MapError, match="has not been baked.*tyled bake sheet.toml"):
        world(".\n", {})


def test_a_name_in_two_tilesets_needs_the_tileset_said(world):
    sets = ("sheet.toml", "extra.toml")
    # 'extra.toml' is also a project; both have a tile called 'grass'
    with pytest.raises(MapError, match="more than one tileset"):
        world("g\n", {"g": "grass"}, tilesets=sets)
    project = world("g\n", {"g": {"tile": "grass", "tileset": "extra"}}, tilesets=sets)
    assert layer(project.to_dict(), "ground") == [[21 + 1]]


# ---- C2: the layout and the fill

def test_ragged_lines_are_refused_naming_the_line(world):
    with pytest.raises(MapError, match="line 3 has 2 characters, but line 1 has 3"):
        world("...\n...\n..\n", {})


def test_a_blank_line_in_the_middle_is_a_ragged_line(world):
    with pytest.raises(MapError, match="line 2 has 0 characters"):
        world("...\n\n...\n", {})


def test_an_empty_layout_is_refused(world):
    with pytest.raises(MapError, match="layout is empty"):
        world("\n\n", {})


def test_the_fill_goes_under_everything_and_a_ground_tile_replaces_it(world):
    tmj = world("r.\n..\n", {"r": "road"}, fill="grass").to_dict()
    assert layer(tmj, "ground") == [[gid("road"), gid("grass")], [gid("grass"), gid("grass")]]


def test_without_a_fill_the_ground_is_empty_where_nothing_is_drawn(world):
    assert layer(world("r.\n", {"r": "road"}).to_dict(), "ground") == [[gid("road"), 0]]


def test_the_fill_must_be_a_tile_that_exists(world):
    with pytest.raises(MapError, match="did you mean 'grass'"):
        world(".\n", {}, fill="gras")


# ---- C3: the legend, a tile

def test_a_tile_is_placed_where_its_character_is(world):
    tmj = world("..\n.w\n", {"w": "wall"}).to_dict()
    assert layer(tmj, "obstacles") == [[0, 0], [0, gid("wall")]]


def test_the_legend_may_name_what_it_places_or_say_which_kind_it_is(world):
    tmj = world("ab\n", {"a": "wall", "b": {"tile": "road"}}).to_dict()
    assert layer(tmj, "obstacles") == [[gid("wall"), 0]] and layer(tmj, "ground") == [[0, gid("road")]]


@pytest.mark.parametrize(
    "entry, flags",
    [
        ({}, 0),
        ({"flip": "h"}, H),
        ({"flip": "v"}, V),
        ({"flip": "hv"}, H | V),
        ({"rotate": 90}, D | H),
        ({"rotate": 180}, H | V),
        ({"rotate": 270}, D | V),
        ({"rotate": 90, "flip": "h"}, D),  # turned, then mirrored: the transpose
        ({"rotate": 90, "flip": "v"}, D | H | V),
        ({"rotate": 180, "flip": "v"}, H),
    ],
)
def test_a_tile_can_be_rotated_and_flipped_with_tileds_flag_bits(world, entry, flags):
    tmj = world("r\n", {"r": {"tile": "road", **entry}}).to_dict()
    assert layer(tmj, "ground") == [[gid("road", flags)]]


def test_the_flags_turn_a_tile_the_way_the_words_say():
    # A pixel at the top right of a 3 × 3 tile, where each transform sends it (column, row).
    def where(transform):
        grid = ((None, None, 7), (None,) * 3, (None,) * 3)
        turned, _ = transform.apply_to_grid(grid, (2, 0))
        return next((c, r) for r, row in enumerate(turned) for c, cell in enumerate(row) if cell is not None)

    assert where(Transform.of(90)) == (2, 2)  # clockwise: top right goes to bottom right
    assert where(Transform.of(180)) == (0, 2)
    assert where(Transform.of(270)) == (0, 0)
    assert where(Transform.of(0, "h")) == (0, 0)
    assert where(Transform.of(0, "v")) == (2, 2)


@pytest.mark.parametrize("entry", [{"rotate": 45}, {"rotate": "90"}, {"flip": "x"}, {"flip": "hh"}])
def test_a_rotation_or_flip_that_is_not_one_of_the_eight_is_refused(world, entry):
    with pytest.raises(MapError, match="legend 'r'"):
        world("r\n", {"r": {"tile": "road", **entry}})


def test_a_character_the_legend_does_not_know_is_an_error_naming_it_and_where(world):
    with pytest.raises(MapError, match=r"'\?' at line 2, column 3 is not in the legend"):
        world("...\n..?\n", {}).to_dict()


def test_the_legend_needs_names_that_exist_with_the_nearest_suggested(world):
    with pytest.raises(MapError, match="legend 'r'.*did you mean 'road'"):
        world("r\n", {"r": "raod"})


@pytest.mark.parametrize(
    "key, value, message",
    [
        (".", "road", "blank of the layout"),
        ("ab", "road", "isn't a single character"),
        ("a", {"tile": "road", "piece": "house"}, "exactly one of"),
        ("a", {}, "exactly one of"),
        ("a", {"tile": "road", "colour": 1}, "unknown keys"),
        ("a", {"nine_slice": "house"}, "'house' is a piece, not a nine-slice"),
    ],
)
def test_a_legend_entry_that_makes_no_sense_is_refused(world, key, value, message):
    with pytest.raises(MapError, match=message):
        world(".\n", {key: value})


# ---- C3: pieces

def test_a_piece_is_placed_so_its_anchor_lands_on_its_character(world):
    layout = "....\n.H..\n....\n"
    tmj = world(layout, {"H": "house"}).to_dict()
    # The house is 2 × 2 with its door (bottom right) as the anchor: it covers rows 0-1, columns 0-1.
    assert layer(tmj, "obstacles") == [[gid("wall"), gid("wall"), 0, 0], [gid("wall"), 0, 0, 0], [0] * 4]
    assert layer(tmj, "ground") == [[0] * 4, [0, gid("door"), 0, 0], [0] * 4]


def test_a_piece_may_be_drawn_with_its_own_character_in_its_other_cells(world):
    # 'gappy' has its anchor at the top left and a gap at its top right.
    tmj = world("H.\nHH\n", {"H": "gappy"}).to_dict()
    assert layer(tmj, "obstacles") == [[gid("wall"), 0], [gid("wall"), gid("wall")]]


def test_a_piece_running_off_the_map_is_an_error_naming_it(world):
    with pytest.raises(MapError, match=r"piece 'house' \('H' at line 1, column 1\) runs off the map"):
        world("H.\n..\n", {"H": "house"}).to_dict()


def test_a_piece_over_something_else_in_the_layout_is_an_error_naming_both(world):
    with pytest.raises(MapError) as error:
        world("..\nrH\n", {"H": "house", "r": "road"}).to_dict()
    assert "piece 'house'" in str(error.value) and "tile 'road'" in str(error.value)


def test_two_pieces_over_the_same_cell_are_an_error_naming_both(world):
    with pytest.raises(MapError) as error:
        world("....\n.HH.\n", {"H": "house"}).to_dict()
    message = str(error.value)
    assert "line 2, column 3" in message and "line 2, column 2" in message and "overlaps piece 'house'" in message


def test_a_piece_turned_puts_its_anchor_on_the_character(world):
    # 'House' turned 90° clockwise: [[wall, wall], [wall, door]] becomes [[wall, wall], [door, wall]],
    # the door at the bottom left. The character stands on the door.
    tmj = world("...\n.H.\n", {"H": {"piece": "house", "rotate": 90}}).to_dict()
    turned = D | H
    assert layer(tmj, "ground")[1] == [0, gid("door", turned), 0]
    assert layer(tmj, "obstacles")[0] == [0, gid("wall", turned), gid("wall", turned)]
    assert layer(tmj, "obstacles")[1] == [0, 0, gid("wall", turned)]


def test_a_piece_flipped_is_mirrored_with_its_anchor(world):
    tmj = world("...\n.H.\n", {"H": {"piece": "house", "flip": "h"}}).to_dict()
    assert layer(tmj, "ground")[1] == [0, gid("door", H), 0]  # the door stays on the character
    assert layer(tmj, "obstacles")[0] == [0, gid("wall", H), gid("wall", H)]
    assert layer(tmj, "obstacles")[1] == [0, 0, gid("wall", H)]


# ---- C3: nine-slices

def test_a_nine_slice_is_stretched_to_the_rectangle_of_its_character(world):
    tmj = world(".NNNN.\n.NNNN.\n.NNNN.\n", {"N": "plaza"}).to_dict()
    ids = [[8, 9, 9, 10], [12, 13, 13, 14], [16, 17, 17, 18]]
    ground, obstacles = layer(tmj, "ground"), layer(tmj, "obstacles")
    for r, row in enumerate(ids):
        for c, i in enumerate(row):
            placed = (ground if i == 13 else obstacles)[r][c + 1]
            assert placed == i + 1, (r, c)
    assert ground[1] == [0, 0, 14, 14, 0, 0]  # the centre doesn't block, so it is on the ground


def test_a_nine_slice_can_be_as_small_as_its_four_corners(world):
    tmj = world("NN\nNN\n", {"N": "plaza"}).to_dict()
    assert layer(tmj, "obstacles") == [[9, 11], [17, 19]]


def test_a_nine_slice_that_is_not_a_rectangle_is_refused(world):
    with pytest.raises(MapError, match=r"nine-slice 'plaza' \('N' at line 1, column 1\) isn't a rectangle"):
        world("NNN\nN..\nNNN\n", {"N": "plaza"}).to_dict()


def test_a_nine_slice_one_tile_wide_is_refused(world):
    with pytest.raises(MapError, match="smallest size is 2 × 2"):
        world("N\nN\nN\n", {"N": "plaza"}).to_dict()


def test_a_nine_slice_can_be_turned_before_it_is_stretched(world):
    tmj = world("NNN\nNNN\nNNN\n", {"N": {"nine_slice": "plaza", "flip": "h"}}).to_dict()
    assert layer(tmj, "obstacles")[0] == [10 + 1 + H, 9 + 1 + H, 8 + 1 + H]


# ---- C4: layers

def test_a_tile_that_blocks_goes_on_obstacles_and_the_rest_on_ground(world):
    tmj = world("wr\n", {"w": "wall", "r": "road"}).to_dict()
    assert layer(tmj, "obstacles") == [[gid("wall"), 0]]
    assert layer(tmj, "ground") == [[0, gid("road")]]


def test_a_piece_puts_each_tile_on_the_layer_its_own_properties_choose(world):
    tmj = world("..\n.H\n", {"H": "house"}).to_dict()
    assert layer(tmj, "ground")[1][1] == gid("door") and layer(tmj, "obstacles")[0][0] == gid("wall")


def test_the_legend_can_choose_a_layer_for_an_entry(world):
    tmj = world("w\n", {"w": {"tile": "wall", "layer": "ground"}}).to_dict()
    assert layer(tmj, "ground") == [[gid("wall")]] and layer(tmj, "obstacles") == [[0]]


def test_a_tiles_own_layer_property_chooses_its_layer(world):
    tmj = world("f\n", {"f": "flower"}, layers={"extra": ["decor"]}).to_dict()
    assert layer(tmj, "decor") == [[gid("flower")]]


def test_a_walkable_layer_takes_the_walkable_tiles_of_an_entry_off_the_ground(world):
    tmj = world("..\n.H\n", {"H": {"piece": "house", "walkable_layer": "decor"}}, layers={"extra": ["decor"]}).to_dict()
    assert layer(tmj, "decor")[1][1] == gid("door") and layer(tmj, "ground") == [[0, 0], [0, 0]]
    assert layer(tmj, "obstacles")[0][0] == gid("wall")  # what blocks still blocks


def test_layer_names_and_extra_layers_come_from_the_project_in_order(world):
    layers = {"ground": "floor", "obstacles": "solid", "objects": "things", "extra": ["under", "over"]}
    tmj = world(".\n", {}, layers=layers).to_dict()
    assert [l["name"] for l in tmj["layers"]] == ["floor", "under", "over", "solid", "things"]
    assert [l["id"] for l in tmj["layers"]] == [1, 2, 3, 4, 5]
    tmj = world("wr\n", {"w": "wall", "r": "road"}, layers=layers).to_dict()
    assert layer(tmj, "solid") == [[gid("wall"), 0]] and layer(tmj, "floor") == [[0, gid("road")]]


def test_a_layer_that_is_not_declared_is_refused_so_a_typo_shows(world):
    with pytest.raises(MapError, match="there is no layer 'groud'"):
        world("r\n", {"r": {"tile": "road", "layer": "groud"}})
    with pytest.raises(MapError, match="there is no layer 'decor'"):
        world("f\n", {"f": "flower"}).to_dict()  # the tile asks for decor, which this project doesn't have


def test_layer_names_must_differ(world):
    with pytest.raises(MapError, match="must differ"):
        world(".\n", {}, layers={"ground": "x", "obstacles": "x"})


# ---- C5: objects

def test_an_object_is_a_tile_object_positioned_at_its_bottom_left_and_typed_by_its_tiles_kind(world):
    tmj = world("..s\n...\n", {"s": {"tile": "stall", "layer": "objects"}}).to_dict()
    objects = tmj["layers"][-1]["objects"]
    assert objects == [{
        "class": "food_stall", "gid": gid("stall"), "height": 8, "id": 1, "name": "stall", "rotation": 0,
        "type": "food_stall", "visible": True, "width": 8, "x": 16, "y": 8,
    }]
    assert tmj["nextobjectid"] == 2
    assert layer(tmj, "obstacles") == [[0, 0, 0], [0, 0, 0]]  # an object is not also a tile


def test_an_entry_gives_an_object_its_own_name_and_type(world):
    tmj = world("l\n.\n", {"l": {"tile": "lamp", "layer": "objects", "name": "street lamp", "type": "light"}}).to_dict()
    (obj,) = tmj["layers"][-1]["objects"]
    assert (obj["name"], obj["type"], obj["y"]) == ("street lamp", "light", 8)


def test_objects_are_numbered_in_reading_order_and_can_be_flipped(world):
    legend = {"s": {"tile": "stall", "layer": "objects", "flip": "h"}, "l": {"tile": "lamp", "layer": "objects"}}
    tmj = world("l.s\ns..\n", legend).to_dict()
    objects = tmj["layers"][-1]["objects"]
    assert [(o["id"], o["type"], o["x"], o["y"]) for o in objects] == [
        (1, "lamp", 0, 8), (2, "food_stall", 16, 8), (3, "food_stall", 0, 16)]
    assert objects[1]["gid"] == gid("stall", H)


def test_an_object_can_not_be_turned_by_a_quarter(world):
    with pytest.raises(MapError, match="not turned by 90 or 270"):
        world("l\n", {"l": {"tile": "lamp", "layer": "objects", "rotate": 90}})


def test_only_a_tile_can_be_an_object(world):
    with pytest.raises(MapError, match="only a tile can be an object"):
        world("H\n", {"H": {"piece": "house", "layer": "objects"}})


def test_a_name_or_type_is_for_objects_only(world):
    with pytest.raises(MapError, match="name and type are for objects"):
        world("l\n", {"l": {"tile": "lamp", "name": "x"}})


# ---- C6: the same bytes every time

def test_the_same_project_gives_the_same_bytes(world):
    legend = {"H": "house", "N": "plaza", "s": {"tile": "stall", "layer": "objects"}, "r": "road"}
    layout = "......\n.H..NN\nr..sNN\n"
    first = world(layout, legend, fill="grass").write(world.work / "a.tmj")
    second = world(layout, legend, fill="grass").write(world.work / "b.tmj")
    assert first.read_bytes() == second.read_bytes()
    assert first.read_bytes().endswith(b"}\n") and b"\r" not in first.read_bytes()


def test_a_tmj_is_json_that_tiled_reads_with_a_row_of_tiles_to_a_line(world):
    path = world("r.\n.r\n", {"r": "road"}).write(world.work / "m.tmj")
    text = path.read_text()
    assert json.loads(text)["layers"][0]["data"] == [2, 0, 0, 2]
    assert "    2,0,\n    0,2\n   ]" in text


# ---- the library and the command line

def project_files(work, **extra):
    config = dict(name="m", tilewidth=8, tileheight=8, layout="m.txt", tilesets=["sheet.toml"],
                  legend={"r": "road"}, **extra)
    (work / "m.txt").write_text("r.\n.r\n")
    return config


def test_build_takes_a_project_file_and_writes_the_tmj_named_after_it(world):
    (world.work / "m.txt").write_text("r.\n")
    (world.work / "m.toml").write_text(
        "name = 'm'\ntilewidth = 8\ntileheight = 8\nlayout = 'm.txt'\ntilesets = ['sheet.toml']\n[legend]\nr = 'road'\n")
    path = build("m.toml")
    assert path == Path("m.tmj") and json.loads(path.read_text())["layers"][0]["data"] == [2, 0]
    other = build("m.toml", world.work / "out" / "other.tmj")
    assert json.loads(other.read_text())["tilesets"][0]["source"] == "../sheet.tsx"


def test_build_takes_a_dict_whose_paths_count_from_the_current_folder(world):
    path = build(project_files(world.work))
    assert json.loads(path.read_text())["layers"][0]["data"] == [2, 0, 0, 2]


def test_the_map_command_writes_the_tmj(world):
    (world.work / "m.txt").write_text("r.\n")
    (world.work / "m.toml").write_text(
        "name = 'm'\ntilewidth = 8\ntileheight = 8\nlayout = 'm.txt'\ntilesets = ['sheet.toml']\n[legend]\nr = 'road'\n")
    result = CliRunner().invoke(cli, ["map", "m.toml"])
    assert result.exit_code == 0, result.output
    assert (world.work / "m.tmj").exists()
    result = CliRunner().invoke(cli, ["map", "m.toml", "--output", "elsewhere.tmj"])
    assert result.exit_code == 0 and (world.work / "elsewhere.tmj").exists()


def test_the_map_command_reports_a_bad_layout_as_a_message_not_a_traceback(world):
    (world.work / "m.txt").write_text("r.\n?.\n")
    (world.work / "m.toml").write_text(
        "name = 'm'\ntilewidth = 8\ntileheight = 8\nlayout = 'm.txt'\ntilesets = ['sheet.toml']\n[legend]\nr = 'road'\n")
    result = CliRunner().invoke(cli, ["map", "m.toml"])
    assert result.exit_code == 1
    assert "'?' at line 2, column 1 is not in the legend" in result.output
    assert "Traceback" not in result.output
    assert not (world.work / "m.tmj").exists()


# ---- C7, C8: the town on Tiny Town

@pytest.fixture
def town(tmp_path, monkeypatch):
    """examples/town.* copied beside the pack's image, with Tiny Town baked; returns the folder."""
    pack_image = EXAMPLES / TINY_TOWN_IMAGE
    if not pack_image.exists():
        pytest.skip(f"Kenney's Tiny Town isn't at {pack_image.parent.parent}; copy the pack there (CC0)")
    work = tmp_path / "work"
    (work / TINY_TOWN_IMAGE).parent.mkdir(parents=True)
    shutil.copy(pack_image, work / TINY_TOWN_IMAGE)
    for name in ("tiny-town.toml", "town.toml", "town.txt"):
        shutil.copy(EXAMPLES / name, work / name)
    monkeypatch.chdir(work)
    with open("tiny-town.toml", "rb") as fh:
        TilesetFactory().produce(tomllib.load(fh), options={"save": True}).bake()
    return work


def test_the_town_matches_its_golden_tmj(town):
    out = build("town.toml")  # written beside its tileset, as the README does it
    assert out.read_bytes() == (GOLDEN / "town" / "town.tmj").read_bytes()


def test_the_town_is_30_by_20_with_neighbots_layers_and_objects(town):
    tmj = MapProject(tomllib.loads((town / "town.toml").read_text()), base=town).to_dict()
    assert (tmj["width"], tmj["height"]) == (30, 20)
    assert [l["name"] for l in tmj["layers"]] == ["ground", "decor", "obstacles", "objects"]
    objects = tmj["layers"][-1]["objects"]
    assert sorted((o["type"], o["name"]) for o in objects) == [
        ("bench", "bench"), ("food_stall", "food_stall"), ("target", "target"), ("well", "well")]


def test_the_town_houses_have_their_doors_on_the_road_and_walls_that_block(town):
    tmj = MapProject(tomllib.loads((town / "town.toml").read_text()), base=town).to_dict()
    ground, obstacles = layer(tmj, "ground"), layer(tmj, "obstacles")
    door_wood, road = 85 + 1, 43 + 1  # Tiled's gids: ids 85 (door_wood) and 43 (road_cobble), plus 1
    assert ground[11][4] == door_wood and ground[12][4] == road  # the door is on the ground, the road below
    assert obstacles[10][4] != 0 and obstacles[9][4] != 0  # the wall above the door blocks
    assert all(obstacles[r][c] == 0 for r in (12, 13, 18, 19) for c in range(30))  # the roads are clear


def test_the_town_courtyard_is_a_stretched_nine_slice_with_a_floor_you_can_walk_on(town):
    tmj = MapProject(tomllib.loads((town / "town.toml").read_text()), base=town).to_dict()
    ground, obstacles = layer(tmj, "ground"), layer(tmj, "obstacles")
    assert obstacles[1][21] == 96 + 1 and obstacles[1][28] == 98 + 1 and obstacles[6][28] == 122 + 1
    assert ground[3][24] == 109 + 1 and obstacles[3][24] == 0

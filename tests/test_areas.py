"""C9: a layout that is a grid of area files, written as maps of their own, a Tiled world and a merged map."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from test_map import gid, layer, world  # noqa: F401  (the `world` fixture: a baked test tileset in a folder)
from tyled.command import cli
from tyled.map import MapError, MapProject, build, build_all

# Four areas of 3 × 2 tiles in a 2 × 2 grid, so the whole map is 6 × 4:
#
#   a: a road and a stall (an object)   b: a wall and a road   c: two walls   d: a lamp (an object) and a road
AREAS = {
    "a.txt": "r..\n.s.\n",
    "b.txt": "...\n.wr\n",
    "c.txt": "ww.\n...\n",
    "d.txt": "l..\n..r\n",
}
GRID = [["a.txt", "b.txt"], ["c.txt", "d.txt"]]
LEGEND = {"r": "road", "w": "wall", "s": {"tile": "stall", "layer": "objects"},
          "l": {"tile": "lamp", "layer": "objects", "name": "lamp_post"}}


@pytest.fixture
def town(world):
    """A function that writes the four layout files and makes a project over them."""
    def make(files=AREAS, grid=GRID, legend=LEGEND, **project):
        for name, text in files.items():
            (world.work / name).write_text(text)
        config = dict(name="town", tilewidth=8, tileheight=8, layout=grid, tilesets=["sheet.toml"],
                      legend=legend, fill="grass", **project)
        return MapProject(config, base=world.work)

    make.work = world.work
    return make


def test_each_area_is_a_map_of_its_own_named_after_its_layout_file(town):
    project = town()
    found = {area.name: tmj for area, tmj in project.area_dicts()}
    assert list(found) == ["a", "b", "c", "d"]
    assert all((t["width"], t["height"]) == (3, 2) for t in found.values())
    assert layer(found["a"], "ground") == [[gid("road"), gid("grass"), gid("grass")]] + [[gid("grass")] * 3]
    assert layer(found["c"], "obstacles") == [[gid("wall"), gid("wall"), 0], [0, 0, 0]]


def test_the_merged_map_is_the_areas_side_by_side(town):
    project = town()
    merged = project.to_dict()
    assert (merged["width"], merged["height"]) == (6, 4)
    areas = dict((a.name, t) for a, t in project.area_dicts())
    for name in merged["layers"]:
        if name["type"] != "tilelayer":
            continue
        for row in range(4):
            # Each row of the merged layer is the same row of the areas above and beside each other.
            left, right = ("a", "b") if row < 2 else ("c", "d")
            local = row % 2
            wanted = layer(areas[left], name["name"])[local] + layer(areas[right], name["name"])[local]
            assert layer(merged, name["name"])[row] == wanted, (name["name"], row)


def test_objects_are_placed_in_their_area_and_in_the_merged_map_by_where_they_stand(town):
    project = town()
    merged = {o["name"]: (o["x"], o["y"]) for o in project.to_dict()["layers"][-1]["objects"]}
    areas = {a.name: t["layers"][-1]["objects"] for a, t in project.area_dicts()}
    assert merged == {"stall": (8, 16), "lamp_post": (24, 24)}  # d starts 3 tiles across and 2 down
    assert [(o["name"], o["x"], o["y"]) for o in areas["a"]] == [("stall", 8, 16)]
    assert [(o["name"], o["x"], o["y"]) for o in areas["d"]] == [("lamp_post", 0, 8)]  # its own corner
    assert areas["b"] == [] and areas["c"] == []
    assert [o["id"] for o in areas["d"]] == [1]  # each area numbers its objects from 1


def test_the_world_places_the_areas_in_pixels_side_by_side(town):
    world_dict = town().world_dict()
    assert world_dict["type"] == "world" and world_dict["onlyShowAdjacentMaps"] is False
    assert world_dict["maps"] == [
        {"fileName": "a.tmj", "height": 16, "width": 24, "x": 0, "y": 0},
        {"fileName": "b.tmj", "height": 16, "width": 24, "x": 24, "y": 0},
        {"fileName": "c.tmj", "height": 16, "width": 24, "x": 0, "y": 16},
        {"fileName": "d.tmj", "height": 16, "width": 24, "x": 24, "y": 16},
    ]


def test_writing_makes_the_world_and_an_area_map_each_beside_it(town, tmp_path):
    out = tmp_path / "out" / "town.world"
    written = town().write_files(out)
    assert written == [out] + [out.parent / f"{n}.tmj" for n in "abcd"]
    assert sorted(p.name for p in out.parent.iterdir()) == ["a.tmj", "b.tmj", "c.tmj", "d.tmj", "town.world"]
    assert json.loads(out.read_text())["maps"][3]["fileName"] == "d.tmj"
    a = json.loads((out.parent / "a.tmj").read_text())
    assert a["tilesets"][0]["source"].endswith("sheet.tsx") and a["tilesets"][0]["source"].startswith("../")


def test_a_merged_map_is_written_only_when_asked_for(town, tmp_path):
    project = town()
    project.write_files(tmp_path / "one" / "town.world")
    assert not (tmp_path / "one" / "town.tmj").exists()
    written = project.write_files(tmp_path / "two" / "town.world", merged=True)
    assert written[-1] == tmp_path / "two" / "town.tmj"
    assert json.loads(written[-1].read_text()) == project.to_dict(tmp_path / "two")


def test_the_same_areas_give_the_same_bytes(town, tmp_path):
    first = town().write_files(tmp_path / "one" / "town.world", merged=True)
    second = town().write_files(tmp_path / "two" / "town.world", merged=True)
    for one, two in zip(first, second):
        assert one.read_bytes() == two.read_bytes(), one.name


def test_the_default_output_is_beside_the_current_folder_and_named_after_the_project(town, monkeypatch, tmp_path):
    project = town()
    monkeypatch.chdir(tmp_path)
    assert build(project) == Path("town.world")
    assert build_all(project, merged=True)[-1] == Path("town.tmj")
    assert (tmp_path / "a.tmj").exists()


def test_an_area_layout_is_written_as_a_world_so_the_output_must_say_so(town, tmp_path):
    with pytest.raises(MapError, match="should end in .world"):
        town().write_files(tmp_path / "town.tmj")


def test_a_single_layout_has_no_areas_and_no_world(world):
    project = world("r.\n", {"r": "road"})
    assert project.areas == [] and project.area_dicts() == []
    with pytest.raises(MapError, match="a world is made of areas"):
        project.world_dict()
    assert project.write_files(world.work / "single.tmj", merged=True) == [world.work / "single.tmj"]


def test_rotation_and_flip_work_in_an_area_as_in_a_single_map(town):
    turned = {**LEGEND, "r": {"tile": "road", "rotate": 90}}
    areas = dict((a.name, t) for a, t in town(legend=turned).area_dicts())
    assert layer(areas["a"], "ground")[0][0] == gid("road", 0x20000000 | 0x80000000)  # D | H, as in a single map


# ---- the edges of areas

def test_a_piece_may_not_cross_an_areas_edge_and_the_error_names_both_areas(town):
    # The house's anchor is at its bottom right: standing at the top left of d, it spills up and left,
    # into the areas b, a and c.
    files = {**AREAS, "d.txt": "H..\n...\n"}
    with pytest.raises(MapError) as error:
        town(files, legend={**LEGEND, "H": "house"}).to_dict()
    message = str(error.value)
    assert "piece 'house' ('H' at line 1, column 1 of area 'd.txt')" in message
    assert "crosses the edge of its area" in message
    assert "reaches line 2, column 3 of area 'a.txt'" in message and "outside area 'd.txt'" in message


def test_a_piece_that_stays_inside_its_area_is_fine_beside_other_areas(town):
    files = {**AREAS, "d.txt": "...\n.H.\n"}
    areas = dict((a.name, t) for a, t in town(files, legend={**LEGEND, "H": "house"}).area_dicts())
    assert layer(areas["d"], "ground")[0][1] != 0 or layer(areas["d"], "obstacles")[0][1] != 0


def test_a_piece_running_off_the_whole_map_is_off_the_map_not_in_another_area(town):
    files = {**AREAS, "a.txt": "H..\n...\n"}  # a is at the top left: nothing lies beyond it
    with pytest.raises(MapError, match=r"runs off the map: its cell for line 0, column 0 of area 'a.txt'"):
        town(files, legend={**LEGEND, "H": "house"}).to_dict()


def test_a_nine_slice_may_not_cross_an_areas_edge_and_the_error_names_both_areas(town):
    files = {**AREAS, "a.txt": "..N\n..N\n", "b.txt": "N..\nN..\n"}
    with pytest.raises(MapError, match=r"nine-slice 'plaza'.*crosses the edge of its area.*'a.txt', 'b.txt'"):
        town(files, legend={**LEGEND, "N": "plaza"}).to_dict()


def test_a_nine_slice_inside_an_area_is_stretched_to_it_with_a_gate_in_its_wall(town):
    # Areas are all the same size, so each is the 4 × 3 of the plaza.
    files = {name: "....\n....\n....\n" for name in AREAS}
    files["c.txt"] = "NNNN\nNNNN\nNGGN\n"
    areas = dict((a.name, t) for a, t in town(files, legend={**LEGEND, "N": "plaza", "G": "gate"}).area_dicts())
    assert layer(areas["c"], "obstacles")[2] == [16 + 1, 0, 0, 18 + 1]
    assert layer(areas["c"], "ground")[2][1:3] == [gid("arch"), gid("door")]
    assert layer(areas["c"], "ground")[1][1] == 13 + 1  # the centre is the floor
    assert layer(areas["d"], "obstacles") == [[0] * 4] * 3


# ---- what a bad layout says

def test_an_area_that_is_not_the_size_of_the_others_is_refused_naming_it(town):
    with pytest.raises(MapError, match=r"every area must be the same size, but 'c.txt' is 3 × 3 and 'a.txt' is 3 × 2"):
        town({**AREAS, "c.txt": "ww.\n...\n...\n"})


def test_a_ragged_line_in_an_area_names_the_file_and_the_line(town):
    with pytest.raises(MapError, match=r"layout 'b.txt': line 2 has 2 characters, but line 1 has 3"):
        town({**AREAS, "b.txt": "...\n..\n"})


def test_an_unknown_character_in_an_area_names_the_area_the_line_and_the_column(town):
    with pytest.raises(MapError, match=r"'\?' at line 2, column 3 of area 'd.txt' is not in the legend"):
        town({**AREAS, "d.txt": "l..\n..?\n"}).to_dict()


def test_a_missing_area_file_is_named(town):
    with pytest.raises(MapError, match=r"layout: 'nowhere.txt' doesn't exist"):
        town(grid=[["a.txt", "nowhere.txt"]])


@pytest.mark.parametrize(
    "grid, message",
    [
        (["a.txt", "b.txt"], "row 1 of the grid of areas must be a list"),
        ([["a.txt", "b.txt"], ["c.txt"]], "row 2 of the grid of areas has 1 areas, but row 1 has 2"),
        ([["a.txt", "b.txt"], ["a.txt", "d.txt"]], "would both be written as a.tmj"),
        ([[]], "row 1 of the grid of areas must be a list"),
        ([], "give the path of a layout file, or a grid"),
    ],
)
def test_a_grid_that_is_not_a_grid_of_different_files_is_refused(town, grid, message):
    with pytest.raises(MapError, match=message):
        town(grid=grid)


# ---- the command

def test_the_map_command_writes_the_world_the_areas_and_with_merged_the_whole_map(town, monkeypatch):
    town()
    (town.work / "town.toml").write_text(
        "name = 'town'\ntilewidth = 8\ntileheight = 8\ntilesets = ['sheet.toml']\n"
        "layout = [['a.txt', 'b.txt'], ['c.txt', 'd.txt']]\nfill = 'grass'\n"
        "[legend]\nr = 'road'\nw = 'wall'\ns = { tile = 'stall', layer = 'objects' }\n"
        "l = { tile = 'lamp', layer = 'objects' }\n")
    monkeypatch.chdir(town.work)
    result = CliRunner().invoke(cli, ["map", "town.toml"])
    assert result.exit_code == 0, result.output
    assert (town.work / "town.world").exists() and (town.work / "a.tmj").exists()
    assert not (town.work / "town.tmj").exists()
    result = CliRunner().invoke(cli, ["map", "town.toml", "--merged", "--output", "out/whole.world"])
    assert result.exit_code == 0, result.output
    assert (town.work / "out" / "whole.world").exists() and (town.work / "out" / "town.tmj").exists()


def test_the_map_command_reports_a_crossing_piece_as_a_message(town, monkeypatch):
    town({**AREAS, "d.txt": "H..\n...\n"})
    (town.work / "town.toml").write_text(
        "name = 'town'\ntilewidth = 8\ntileheight = 8\ntilesets = ['sheet.toml']\n"
        "layout = [['a.txt', 'b.txt'], ['c.txt', 'd.txt']]\n"
        "[legend]\nr = 'road'\nw = 'wall'\nH = 'house'\ns = 'stall'\nl = 'lamp'\n")
    monkeypatch.chdir(town.work)
    result = CliRunner().invoke(cli, ["map", "town.toml"])
    assert result.exit_code == 1 and "crosses the edge of its area" in result.output
    assert "Traceback" not in result.output and not (town.work / "town.world").exists()

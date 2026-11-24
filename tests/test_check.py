"""`tyled check`: a map checked as a place, from its tiles' properties."""

import json

import pytest
from click.testing import CliRunner

from test_areas import town as areas_town  # noqa: F401  (a function that makes a project of four areas)
from test_map import town, world  # noqa: F401  (the town example, built; a baked test tileset)
from tyled.check import CheckError, Finding, check_map
from tyled.command import cli
from tyled.map import build_all

D, H, V = 0x20000000, 0x80000000, 0x40000000

# A tileset of 9 tiles of 8 px. A check reads only the .tsx, so there is no picture.
#
#   0 floor   1 wall (blocks)   2 door   3 door_east (opens east)   4 crate (blocks)   5 lamp
#   6 has no name and is in no piece   7 door_bad (opens 'up')   8 has no name but is in the piece 'pair'
TSX = """<?xml version="1.0" encoding="UTF-8"?>
<tileset version="1.10" name="t" tilewidth="8" tileheight="8" tilecount="9" columns="3">
 <properties>
  <property name="piece:pair" value="8,0"/>
  <property name="anchor:pair" value="0,0"/>
 </properties>
 <image source="t.png" width="24" height="24"/>
{tiles}</tileset>
"""

TILES = {
    0: dict(name="floor"),
    1: dict(name="wall", walkable=False),
    2: dict(name="door", kind="door"),
    3: dict(name="door_east", kind="door", opens="east"),
    4: dict(name="crate", walkable=False, kind="crate"),
    5: dict(name="lamp"),
    7: dict(name="door_bad", kind="door", opens="up"),
}
# What a character in the rows stands for: a gid (the tile's id + 1).
GIDS = {".": 1, "#": 2, "D": 3, "E": 4, "c": 5, "l": 7, "x": 8, "B": 9, "p": 9, "?": 99}
CRATE, LAMP, DOOR = 5, 6, 3  # as gids, for objects


def write_tsx(folder):
    tiles = ""
    for id, props in TILES.items():
        items = ""
        for key, value in props.items():
            if isinstance(value, bool):
                items += f'   <property name="{key}" type="bool" value="{str(value).lower()}"/>\n'
            else:
                items += f'   <property name="{key}" value="{value}"/>\n'
        tiles += f' <tile id="{id}">\n  <properties>\n{items}  </properties>\n </tile>\n'
    (folder / "t.tsx").write_text(TSX.format(tiles=tiles))


def thing(gid, column, row, name, width=8, height=8):
    """A tile object standing on a cell (its y is the bottom of the cell)."""
    return {"id": 0, "name": name, "type": "", "gid": gid, "x": column * 8, "y": (row + 1) * 8,
            "width": width, "height": height, "rotation": 0, "visible": True}


def make_map(folder, rows, objects=(), name="m.tmj"):
    """A map: the characters of `rows` (see GIDS, a space is nothing) on a layer 'ground', and `objects` on 'objects'."""
    folder.mkdir(parents=True, exist_ok=True)
    write_tsx(folder)
    height, width = len(rows), len(rows[0])
    listed = [{**o, "id": index} for index, o in enumerate(objects, 1)]
    tree = {"type": "map", "orientation": "orthogonal", "infinite": False, "width": width, "height": height,
            "tilewidth": 8, "tileheight": 8, "tilesets": [{"firstgid": 1, "source": "t.tsx"}],
            "layers": [
                {"type": "tilelayer", "name": "ground", "width": width, "height": height,
                 "data": [GIDS.get(ch, 0) for row in rows for ch in row]},
                {"type": "objectgroup", "name": "objects", "objects": listed},
            ]}
    path = folder / name
    path.write_text(json.dumps(tree))
    return path


def kinds(findings):
    return [f.kind for f in findings]


def where(findings):
    return [(f.kind, f.x, f.y) for f in findings]


# ---- the town passes

def test_the_town_example_passes_every_check(town):
    path = build_all("town.toml")[0]
    assert check_map(path) == []
    assert check_map("town.toml") == []  # given as a project, it is its own: its layers are the declared ones
    assert check_map(path, project="town.toml") == []
    assert check_map(path, start="well") == []
    assert check_map(path, start=(0, 0)) == []


def test_a_map_of_floor_passes(tmp_path):
    assert check_map(make_map(tmp_path, ["....", "...."])) == []


# ---- objects stand on walkable tiles

def test_an_object_on_a_tile_that_blocks_is_reported_where_it_stands(tmp_path):
    path = make_map(tmp_path, ["...", ".#.", "..."], objects=[thing(LAMP, 1, 1, "lamp_post"), thing(LAMP, 0, 0, "fine")])
    found = check_map(path)
    assert where(found) == [("object_on_blocked_tile", 1, 1)]
    assert found[0].object == "lamp_post" and found[0].layer == "objects" and "lamp_post" in found[0].message


def test_an_object_that_blocks_stands_on_floor_or_beside_it_and_is_enclosed_with_neither(tmp_path):
    on_floor = make_map(tmp_path / "a", ["...", "...", "..."], [thing(CRATE, 1, 1, "crate")])
    on_a_wall_with_floor_beside = make_map(tmp_path / "b", ["#..", "...", "..."], [thing(CRATE, 0, 0, "crate")])
    among_walls = make_map(tmp_path / "c", ["###.", "###.", "###."], [thing(CRATE, 1, 1, "crate")])
    assert check_map(on_floor) == []
    assert check_map(on_a_wall_with_floor_beside) == []
    found = check_map(among_walls)
    assert [(f.kind, f.x, f.y, f.object) for f in found] == [("object_enclosed", 1, 1, "crate")]


def test_an_object_off_the_map_is_not_standing_on_anything(tmp_path):
    assert kinds(check_map(make_map(tmp_path, ["..", ".."], [thing(LAMP, 5, 5, "far")]))) == ["object_on_blocked_tile"]


def test_a_tile_object_covers_the_cells_its_size_says(tmp_path):
    # 16 × 8 with its bottom left at (8, 16): the cells (1, 1) and (2, 1), and (2, 1) is a wall
    path = make_map(tmp_path, ["....", "..#.", "...."], [thing(LAMP, 1, 1, "wide", width=16)])
    assert where(check_map(path)) == [("object_on_blocked_tile", 1, 1)]


# ---- everything can be reached

def test_a_region_cut_off_is_listed_with_its_size_place_and_what_it_holds(tmp_path):
    path = make_map(tmp_path, ["..#...", "..#...", "..#..."], objects=[thing(LAMP, 5, 2, "lamp_post")])
    found = check_map(path)
    assert where(found) == [("region_cut_off", 0, 0)]  # 6 and 9 tiles: the smaller one is the one cut off
    assert found[0].details["cells"] == 6 and found[0].details["bounds"] == [0, 0, 2, 3]
    assert found[0].details["objects"] == []
    inside = make_map(tmp_path / "b", ["...#..", "...#.."], objects=[thing(LAMP, 5, 1, "lamp_post")])
    cut = check_map(inside)[0]
    assert (cut.x, cut.y, cut.details["cells"], cut.details["objects"]) == (4, 0, 4, ["lamp_post"])
    assert "lamp_post" in cut.message and "4 walkable tiles" in cut.message


def test_the_largest_walkable_area_is_the_one_everything_must_reach(tmp_path):
    found = check_map(make_map(tmp_path / "a", ["..#.......", "..#......."]))
    assert [(f.x, f.y, f.details["cells"]) for f in found] == [(0, 0, 4)]
    tie = check_map(make_map(tmp_path / "b", [".#."]))
    assert [(f.x, f.y) for f in tie] == [(2, 0)]  # equal: the first in reading order is the main one


def test_a_start_names_where_people_come_from_by_tile_or_by_object(tmp_path):
    path = make_map(tmp_path, ["...#..", "...#.."], objects=[thing(LAMP, 5, 1, "lamp_post")])
    from_left = check_map(path, start=(0, 0))
    assert [(f.x, f.y) for f in from_left] == [(4, 0)] and from_left[0].details["objects"] == ["lamp_post"]
    assert "the start (0,0)" in from_left[0].message
    from_right = check_map(path, start=(5, 0))
    assert [(f.x, f.y, f.details["cells"]) for f in from_right] == [(0, 0, 6)]
    by_name = check_map(path, start="lamp_post")
    assert [(f.x, f.y, f.details["cells"]) for f in by_name] == [(0, 0, 6)] and "the start (lamp_post)" in by_name[0].message


def test_a_start_that_cannot_be_used_is_an_error(tmp_path):
    path = make_map(tmp_path, ["..#.", "..#."], objects=[thing(LAMP, 0, 0, "lamp")])
    for start, text in [((2, 0), "can't be walked on"), ((9, 9), "not on the map"), ("nobody", "no object named 'nobody'"),
                        (5, "start is a tile"), ((1,), "start is a tile")]:
        with pytest.raises(CheckError, match=text):
            check_map(path, start=start)


def test_a_blocking_object_in_a_corridor_cuts_it(tmp_path):
    path = make_map(tmp_path, ["....."], [thing(CRATE, 3, 0, "crate")])
    found = check_map(path)
    assert [(f.kind, f.x, f.y, f.details["cells"]) for f in found] == [("region_cut_off", 4, 0, 1)]


def test_a_map_nothing_can_be_walked_on_says_so(tmp_path):
    assert kinds(check_map(make_map(tmp_path, ["##", "##"]))) == ["nothing_walkable"]


def test_walking_goes_up_down_and_sideways_but_not_diagonally(tmp_path):
    assert where(check_map(make_map(tmp_path, [".#", "#."]))) == [("region_cut_off", 1, 1)]


def test_an_empty_cell_is_not_walkable_there_is_nothing_to_stand_on(tmp_path):
    assert where(check_map(make_map(tmp_path, ["..  ..", "..  .."]))) == [("region_cut_off", 4, 0)]


# ---- doors

def test_a_door_needs_a_walkable_tile_below_it_by_default(tmp_path):
    assert check_map(make_map(tmp_path / "a", ["..", "D.", ".."])) == []
    found = check_map(make_map(tmp_path / "b", ["..", "D.", "#."]))
    assert where(found) == [("door_blocked", 0, 1)]
    assert found[0].details == {"opens": "south", "front": [0, 2]} and "0,2" in found[0].message
    assert where(check_map(make_map(tmp_path / "c", ["..", "D."]))) == [("door_blocked", 0, 1)]  # the map ends below it


def test_a_tile_property_names_the_side_a_door_opens_to(tmp_path):
    assert check_map(make_map(tmp_path / "a", ["E.", ".#"])) == []
    found = check_map(make_map(tmp_path / "b", ["E#", ".."]))
    assert where(found) == [("door_blocked", 0, 0)] and found[0].details["opens"] == "east"
    assert where(check_map(make_map(tmp_path / "c", ["x.", ".."]))) == [("door_bad_side", 0, 0)]


@pytest.mark.parametrize("flags, opens, away", [
    (0, "south", "north"),
    (D | H, "west", "east"),        # a quarter turn clockwise: the bottom goes to the left
    (D | V, "east", "west"),        # a quarter turn the other way
    (H | V, "north", "south"),      # half a turn
    (H, "south", "north"),          # mirrored across: the bottom stays where it is
    (V, "north", "south"),          # mirrored down: the bottom goes to the top
])
def test_a_door_turned_by_its_flags_opens_to_the_turned_side(tmp_path, flags, opens, away):
    sides = {"north": (1, 0), "south": (1, 2), "west": (0, 1), "east": (2, 1)}

    def door_with_wall(folder, side):
        rows = [list("..."), list("..."), list("...")]
        column, row = sides[side]
        rows[row][column] = "#"
        path = make_map(folder, ["".join(r) for r in rows])
        tree = json.loads(path.read_text())
        tree["layers"][0]["data"][4] = 3 | flags  # the door is the middle cell
        path.write_text(json.dumps(tree))
        return path

    blocked = check_map(door_with_wall(tmp_path / "blocked", opens))
    assert [(f.kind, f.details["opens"]) for f in blocked] == [("door_blocked", opens)]
    assert check_map(door_with_wall(tmp_path / "free", away)) == []


def test_a_tile_object_can_be_a_door_too(tmp_path):
    path = make_map(tmp_path, ["...", "...", "#.."], [thing(DOOR, 0, 1, "front_door")])
    found = check_map(path)
    assert [(f.kind, f.x, f.y, f.object) for f in found] == [("door_blocked", 0, 1, "front_door")]


# ---- tiles the tileset doesn't know or name

def test_a_tile_with_no_name_is_reported_once_with_where_it_is_and_how_many(tmp_path):
    found = check_map(make_map(tmp_path, ["..l.", "l...", "..l."]))
    assert where(found) == [("unnamed_tile", 2, 0)]
    assert found[0].layer == "ground" and found[0].details["count"] == 3
    assert found[0].details["positions"] == [[2, 0], [0, 1], [2, 2]] and "and 2 more" in found[0].message


def test_a_tile_without_a_name_that_is_in_a_piece_is_fine_and_flags_do_not_matter(tmp_path):
    path = make_map(tmp_path, ["B.l", "..."])
    tree = json.loads(path.read_text())
    tree["layers"][0]["data"][2] |= H | D
    path.write_text(json.dumps(tree))
    found = check_map(path)
    assert where(found) == [("unnamed_tile", 2, 0)]  # the one in the piece (tile 8) passes; tile 6 doesn't, turned or not
    assert found[0].details["gid"] == 7


def test_a_tile_the_tileset_does_not_have_is_unknown(tmp_path):
    found = check_map(make_map(tmp_path, ["?.", ".?"]))
    assert where(found) == [("unknown_tile", 0, 0)] and found[0].details["count"] == 2
    assert "gid 99" in found[0].message and "isn't in any tileset" in found[0].message


def test_an_object_with_an_unnamed_tile_is_reported_on_its_layer(tmp_path):
    path = make_map(tmp_path, ["..", ".."], [thing(7, 1, 1, "mystery")])
    found = check_map(path)
    assert [(f.kind, f.x, f.y, f.layer) for f in found] == [("unnamed_tile", 1, 1, "objects")]


# ---- layers the project doesn't declare

def test_layers_the_project_does_not_declare_are_reported(world, tmp_path):
    project = world("..\n..\n", {}, fill="grass")
    path = project.write(world.work / "m.tmj")
    assert check_map(path, project=project) == []
    tree = json.loads(path.read_text())
    tree["layers"].insert(1, {**tree["layers"][0], "name": "secret", "id": 9})
    path.write_text(json.dumps(tree))
    found = check_map(path, project=project)
    assert [(f.kind, f.layer, f.x, f.y) for f in found] == [("undeclared_layer", "secret", None, None)]
    assert "declared" in found[0].message and "'ground'" in found[0].message
    assert check_map(path) == []  # without the project, there is nothing to hold the layers to
    assert check_map(project) == []  # a project is its own


def test_the_layers_a_project_declares_include_the_extra_ones(world):
    project = world("f\n", {"f": {"tile": "flower"}}, fill="grass", layers={"extra": ["decor"]})
    assert check_map(project) == []


# ---- worlds, the library's findings, and the commands

def test_a_world_is_checked_as_one_map_the_same_as_the_merged_map(areas_town, tmp_path):
    written = build_all(areas_town(), tmp_path / "out" / "town.world", merged=True)
    assert check_map(written[0]) == check_map(written[-1])
    assert check_map(written[0], start=(0, 0)) == check_map(written[-1], start=(0, 0))


def test_the_same_map_gives_the_same_findings(tmp_path):
    path = make_map(tmp_path, ["..#..", "l.#?.", "..#.."], [thing(LAMP, 3, 1, "lamp_post")])
    first, second = check_map(path), check_map(path)
    assert first == second and first


def test_a_finding_is_plain_data_with_kind_position_and_text():
    finding = Finding("door_blocked", "door opens onto a wall", 3, 4, "ground", None, {"front": [3, 5]})
    assert finding.to_dict() == {"kind": "door_blocked", "message": "door opens onto a wall", "x": 3, "y": 4,
                                 "layer": "ground", "object": None, "details": {"front": [3, 5]}}
    assert str(finding) == "3,4: door opens onto a wall [door_blocked]"
    assert str(Finding("undeclared_layer", "no")) == "no [undeclared_layer]"


def test_check_prints_each_problem_with_where_it_is_and_exits_with_1(tmp_path):
    path = make_map(tmp_path, ["..#.", "..#."], [thing(LAMP, 3, 1, "lamp_post")])
    result = CliRunner().invoke(cli, ["check", str(path)])
    assert result.exit_code == 1
    lines = result.output.strip().splitlines()
    assert lines[0].startswith("3,0: ") and "[region_cut_off]" in lines[0] and "lamp_post" in lines[0]
    assert lines[-1] == "1 problem"


def test_check_says_ok_and_exits_with_0_for_a_map_that_is_fine(tmp_path):
    result = CliRunner().invoke(cli, ["check", str(make_map(tmp_path, ["..", ".."]))])
    assert result.exit_code == 0 and result.output.strip() == "ok: no problems"


def test_check_json_has_ok_and_a_list_of_findings_with_the_same_keys(tmp_path):
    path = make_map(tmp_path / "bad", ["..#.", "..#."], [thing(LAMP, 3, 1, "lamp_post")])
    result = CliRunner().invoke(cli, ["check", str(path), "--json"])
    assert result.exit_code == 1
    shape = json.loads(result.output)
    assert list(shape) == ["ok", "findings"] and shape["ok"] is False
    [finding] = shape["findings"]
    assert list(finding) == ["kind", "message", "x", "y", "layer", "object", "details"]
    assert (finding["kind"], finding["x"], finding["y"]) == ("region_cut_off", 3, 0)
    assert finding["details"]["objects"] == ["lamp_post"] and finding["details"]["bounds"] == [3, 0, 1, 2]
    clean = CliRunner().invoke(cli, ["check", str(make_map(tmp_path / "ok", ["..", ".."])), "--json"])
    assert clean.exit_code == 0 and json.loads(clean.output) == {"ok": True, "findings": []}


def test_check_takes_a_start_a_project_and_a_project_as_the_map(tmp_path, world):
    path = make_map(tmp_path / "s", ["...#..", "...#.."])
    runner = CliRunner()
    far = json.loads(runner.invoke(cli, ["check", str(path), "--start", "5,0", "--json"]).output)
    assert [(f["x"], f["y"]) for f in far["findings"]] == [(0, 0)]
    assert runner.invoke(cli, ["check", str(path), "--start", "nobody"]).exit_code == 2
    project = world("..\n..\n", {}, fill="grass")
    built = project.write(world.work / "m.tmj")
    (world.work / "m.toml").write_text(
        "name = 'm'\ntilewidth = 8\ntileheight = 8\nlayout = 'm.txt'\ntilesets = ['sheet.toml']\nfill = 'grass'\n")
    assert runner.invoke(cli, ["check", str(built), "--project", str(world.work / "m.toml")]).exit_code == 0
    assert runner.invoke(cli, ["check", str(world.work / "m.toml")]).exit_code == 0


def test_check_says_what_is_wrong_with_how_it_was_used_with_exit_status_2(tmp_path):
    path = make_map(tmp_path, ["..", ".."])
    for args, text in [([str(tmp_path / "nope.tmj")], "doesn't exist"), ([str(path), "--start", "1,2,3"], "--start is 2 whole numbers"),
                       ([str(path), "--start", "9,9"], "not on the map"), ([str(path), "--start", "a,b"], "--start is 2 whole")]:
        result = CliRunner().invoke(cli, ["check", *args])
        assert result.exit_code == 2 and text in result.output, (args, result.output)

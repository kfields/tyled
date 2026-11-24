"""Grid tilesets, and the names, properties and pieces of their tiles."""

import shutil
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from click.testing import CliRunner
from PIL import Image

from bakehelp import FIXTURES, assert_matches_golden, bake_fixture, files_under
from tyled.command import cli
from tyled.tileset.factory import TilesetFactory
from tyled.tileset.grid import GridTileset
from tyled.tileset.names import NamedTilesError, UnknownNameError, read_tsx

EXAMPLES = Path(__file__).parent.parent / "examples"
TINY_TOWN_IMAGE = Path("kenney/tiny-town/Tilemap/tilemap.png")


def make_grid_image(path, columns, rows, size=8, spacing=0, margin=0):
    """An image of columns × rows flat-coloured tiles, laid out the way a Tiled tileset says."""
    width = 2 * margin + columns * size + (columns - 1) * spacing
    height = 2 * margin + rows * size + (rows - 1) * spacing
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    for row in range(rows):
        for column in range(columns):
            tile = Image.new("RGBA", (size, size), (10 * (row * columns + column), 90, 200, 255))
            image.paste(tile, (margin + column * (size + spacing), margin + row * (size + spacing)))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def bake_config(config, workdir, monkeypatch):
    """Bake a project given as a dict in `workdir`; return the tileset."""
    workdir.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(workdir)
    return TilesetFactory().produce(config, options={"save": True, "show": False, "rotation": False})


def baked_grid(tmp_path, monkeypatch):
    """The grid fixture, baked; returns the tileset and the folder it was baked in."""
    bake_fixture("grid", tmp_path, monkeypatch)
    return read_tsx(tmp_path / "work" / "grid.tsx"), tmp_path / "work"


# ---- C1: a grid tileset used as it is

def test_a_grid_tileset_matches_its_golden_tsx_and_writes_no_image(tmp_path, monkeypatch):
    out = bake_fixture("grid", tmp_path, monkeypatch)
    assert_matches_golden("grid", out)
    assert files_under(out) == {"grid.tsx"}


def test_a_grid_tileset_refers_to_the_image_where_it_is(tmp_path, monkeypatch):
    bake_fixture("grid", tmp_path, monkeypatch)
    root = ET.parse(tmp_path / "work" / "grid.tsx").getroot()
    assert root.get("columns") == "4" and root.get("tilecount") == "12"
    assert (root.get("tilewidth"), root.get("spacing"), root.get("margin")) == ("8", "1", "2")
    image = root.find("image")
    assert image is not None
    assert image.get("source") == "grid.png"
    assert (image.get("width"), image.get("height")) == ("39", "30")


def test_columns_are_read_from_the_image(tmp_path, monkeypatch):
    make_grid_image(tmp_path / "w" / "sheet.png", columns=5, rows=2, size=16, spacing=1)
    config = dict(name="sheet", type="grid", source="sheet.png", tilewidth=16, tileheight=16, spacing=1)
    ts = bake_config(config, tmp_path / "w", monkeypatch)
    assert (ts.columns, ts.rows, ts.tilecount) == (5, 2, 10)


def test_spacing_is_read_from_the_image_when_only_one_gap_fits(tmp_path, monkeypatch):
    make_grid_image(tmp_path / "w" / "sheet.png", columns=12, rows=11, size=16, spacing=1)
    config = dict(name="sheet", type="grid", source="sheet.png", tilewidth=16, tileheight=16)
    ts = bake_config(config, tmp_path / "w", monkeypatch)
    assert (ts.spacing, ts.margin, ts.columns, ts.rows) == (1, 0, 12, 11)


def test_a_tile_size_is_needed_because_the_image_cannot_tell_it(tmp_path, monkeypatch):
    make_grid_image(tmp_path / "w" / "sheet.png", columns=2, rows=2)
    with pytest.raises(NamedTilesError, match="tilewidth"):
        bake_config(dict(name="sheet", type="grid", source="sheet.png"), tmp_path / "w", monkeypatch)


def test_columns_that_disagree_with_the_image_are_an_error(tmp_path, monkeypatch):
    make_grid_image(tmp_path / "w" / "sheet.png", columns=4, rows=2)
    config = dict(name="sheet", type="grid", source="sheet.png", tilewidth=8, tileheight=8, columns=5)
    with pytest.raises(NamedTilesError, match="5 columns.*holds 4"):
        bake_config(config, tmp_path / "w", monkeypatch)


# ---- C2, C3: names and properties, written and read back

def test_a_name_is_written_as_the_tile_property_name(tmp_path, monkeypatch):
    bake_fixture("grid", tmp_path, monkeypatch)
    root = ET.parse(tmp_path / "work" / "grid.tsx").getroot()
    tile = next(t for t in root.findall("tile") if t.get("id") == "5")
    props = {p.get("name"): p for p in tile.findall("properties/property")}
    assert props["name"].get("value") == "stall"
    assert props["name"].get("type") is None  # a string, as Tiled writes it


def test_names_and_properties_are_read_back_from_the_tsx(tmp_path, monkeypatch):
    named, _ = baked_grid(tmp_path, monkeypatch)
    assert named.tile("grass").id == 0
    assert named.tile("stall").id == 5
    assert named.tile("stall").properties == {"walkable": False, "kind": "food_stall"}
    assert named.tile("water").properties == {"walkable": False, "depth": 2, "speed": 0.5}
    assert named.names() == ["grass", "water", "stall", "roof_left", "roof_right", "door"]


def test_properties_come_back_with_tiled_types(tmp_path, monkeypatch):
    named, work = baked_grid(tmp_path, monkeypatch)
    water = named.tile("water").properties
    assert type(water["walkable"]) is bool
    assert type(water["depth"]) is int
    assert type(water["speed"]) is float
    xml = (work / "grid.tsx").read_text()
    assert '<property name="walkable" type="bool" value="false"/>' in xml
    assert '<property name="depth" type="int" value="2"/>' in xml
    assert '<property name="speed" type="float" value="0.5"/>' in xml


def test_the_library_gives_the_same_answer_as_the_tsx(tmp_path, monkeypatch):
    named, _ = baked_grid(tmp_path, monkeypatch)
    with open(FIXTURES / "grid" / "project.toml", "rb") as fh:
        config = tomllib.load(fh)
    ts = GridTileset.create(config, options={"save": False})
    assert ts.tile("water") == named.tile("water")
    assert ts.piece("house") == named.piece("house")
    assert ts.named.tiles() == named.tiles()


def test_every_tile_has_the_default_properties_unless_it_says_otherwise(tmp_path, monkeypatch):
    named, _ = baked_grid(tmp_path, monkeypatch)
    assert named.tile("grass").properties == {"walkable": True}
    assert named.tile("water").properties["walkable"] is False
    unnamed = named.tile_by_id(7)
    assert unnamed is not None and unnamed.name is None and unnamed.properties == {"walkable": True}
    assert all(t.properties["walkable"] in (True, False) for t in named.tiles())
    assert len(named.tiles()) == 12


def test_a_property_set_on_a_region_reaches_every_tile_of_it_and_survives_xml_escaping(tmp_path, monkeypatch):
    named, _ = baked_grid(tmp_path, monkeypatch)
    for id in (2, 3):
        tile = named.tile_by_id(id)
        assert tile is not None
        assert tile.properties["label"] == 'a "quoted" <b> & more'


def test_a_tileset_without_defaults_leaves_unmentioned_tiles_out(tmp_path, monkeypatch):
    make_grid_image(tmp_path / "w" / "g.png", columns=2, rows=2)
    config = dict(
        name="g", type="grid", source="g.png", tilewidth=8, tileheight=8,
        tiles=[{"at": [1, 1], "name": "only"}],
    )
    ts = bake_config(config, tmp_path / "w", monkeypatch)
    assert [t.id for t in ts.named.tiles()] == [3]


# ---- C2: misspelled and clashing names

def test_a_misspelled_name_is_an_error_that_suggests_the_nearest_names(tmp_path, monkeypatch):
    named, _ = baked_grid(tmp_path, monkeypatch)
    with pytest.raises(UnknownNameError) as error:
        named.tile("watr")
    assert "no tile named 'watr'" in str(error.value)
    assert "'water'" in str(error.value)
    assert isinstance(error.value, KeyError)


def test_a_misspelled_piece_name_suggests_the_nearest_piece(tmp_path, monkeypatch):
    named, _ = baked_grid(tmp_path, monkeypatch)
    with pytest.raises(UnknownNameError, match="did you mean 'house'"):
        named.piece("hose")


def test_a_name_with_nothing_near_it_gets_no_suggestion(tmp_path, monkeypatch):
    named, _ = baked_grid(tmp_path, monkeypatch)
    with pytest.raises(UnknownNameError) as error:
        named.tile("zzzzzz")
    assert "did you mean" not in str(error.value)


def grid_config(tmp_path, **extra):
    make_grid_image(tmp_path / "g.png", columns=3, rows=2)
    return dict(name="g", type="grid", source=str(tmp_path / "g.png"), tilewidth=8, tileheight=8, **extra)


@pytest.mark.parametrize(
    "tiles, message",
    [
        ([{"at": [0, 0], "name": "a"}, {"at": [1, 0], "name": "a"}], "'a' is used for tiles 0 and 1"),
        ([{"at": [0, 0], "name": "a"}, {"at": [0, 0], "name": "b"}], "tile 0 is already named 'a'"),
        ([{"at": [3, 0], "name": "a"}], "outside the image"),
        ([{"at": [0, 2], "name": "a"}], "outside the image"),
        ([{"id": 6, "name": "a"}], "outside the tileset"),
        ([{"name": "a"}], "exactly one of id, at, region"),
        ([{"at": [0, 0], "id": 0}], "exactly one of id, at, region"),
        ([{"region": [0, 0, 2, 1], "name": "a"}], "a name goes with one tile"),
        ([{"at": [0, 0], "name": ""}], "non-empty string"),
        ([{"at": [0, 0], "properties": {"name": "x"}}], "'name' is the tile's name"),
        ([{"at": [0, 0], "properties": {"when": [1, 2]}}], "must be a string, integer, float or boolean"),
    ],
)
def test_a_project_that_names_tiles_wrongly_is_an_error(tiles, message, tmp_path, monkeypatch):
    with pytest.raises(NamedTilesError, match=message):
        bake_config(grid_config(tmp_path, tiles=tiles), tmp_path / "w", monkeypatch)


# ---- C4: pieces

def test_a_piece_from_a_region_is_a_grid_of_ids_with_its_anchor(tmp_path, monkeypatch):
    named, _ = baked_grid(tmp_path, monkeypatch)
    house = named.piece("house")
    assert house.ids == ((4, 5, 6), (8, 9, 10))
    assert (house.width, house.height) == (3, 2)
    assert house.anchor == (2, 1)
    assert house.anchor_id == 10


def test_a_piece_from_rows_of_names_is_a_grid_of_ids_with_gaps_as_none(tmp_path, monkeypatch):
    named, _ = baked_grid(tmp_path, monkeypatch)
    roof = named.piece("roof")
    assert roof.ids == ((8, 9), (10, None))
    assert roof.anchor == (0, 1)
    assert roof.anchor_id == 10


def test_a_piece_may_mix_names_and_ids_and_defaults_to_the_top_left_anchor(tmp_path, monkeypatch):
    config = grid_config(
        tmp_path,
        tiles=[{"at": [1, 1], "name": "b"}],
        pieces=[{"name": "p", "rows": [[0, 1], [2, "b"]]}],
    )
    ts = bake_config(config, tmp_path / "w", monkeypatch)
    assert ts.piece("p").ids == ((0, 1), (2, 4))
    assert ts.piece("p").anchor == (0, 0)


def test_pieces_are_kept_as_tileset_properties_in_the_tsx(tmp_path, monkeypatch):
    bake_fixture("grid", tmp_path, monkeypatch)
    root = ET.parse(tmp_path / "work" / "grid.tsx").getroot()
    props = {p.get("name"): p.get("value") for p in root.findall("properties/property")}
    assert props["piece:house"] == "4,5,6;8,9,10"
    assert props["anchor:house"] == "2,1"
    assert props["piece:roof"] == "8,9;10,-"


@pytest.mark.parametrize(
    "piece, message",
    [
        ({"name": "p"}, "exactly one of region, rows"),
        ({"name": "p", "region": [0, 0, 1, 1], "rows": [[0]]}, "exactly one of region, rows"),
        ({"name": "p", "region": [2, 1, 2, 1]}, "outside the image"),
        ({"name": "p", "region": [0, 0, 0, 1]}, "width and a height of at least 1"),
        ({"name": "p", "rows": [[0, 1], [2]]}, "same, non-zero, length"),
        ({"name": "p", "rows": [["nope"]]}, "no tile named 'nope'"),
        ({"name": "p", "rows": [[9]]}, "outside the tileset"),
        ({"name": "p", "region": [0, 0, 2, 2], "anchor": [2, 0]}, "anchor \\[2, 0\\] is outside the piece"),
        ({"name": "p", "rows": [[0, ""]], "anchor": [1, 0]}, "anchor is on an empty cell"),
        ({"name": "a"}, "exactly one of region, rows"),
    ],
)
def test_a_project_that_describes_a_piece_wrongly_is_an_error(piece, message, tmp_path, monkeypatch):
    tiles = [{"at": [0, 0], "name": "a"}]
    with pytest.raises(NamedTilesError, match=message):
        bake_config(grid_config(tmp_path, tiles=tiles, pieces=[piece]), tmp_path / "w", monkeypatch)


def test_a_piece_may_not_share_its_name_with_a_tile(tmp_path, monkeypatch):
    config = grid_config(
        tmp_path,
        tiles=[{"at": [0, 0], "name": "a"}],
        pieces=[{"name": "a", "region": [0, 0, 1, 1]}],
    )
    with pytest.raises(NamedTilesError, match="names both a tile and a piece"):
        bake_config(config, tmp_path / "w", monkeypatch)


def test_two_pieces_may_not_share_a_name(tmp_path, monkeypatch):
    piece = {"name": "p", "region": [0, 0, 1, 1]}
    with pytest.raises(NamedTilesError, match="two pieces named 'p'"):
        bake_config(grid_config(tmp_path, pieces=[piece, piece]), tmp_path / "w", monkeypatch)


# ---- C5, C6: Tiny Town

def bake_tiny_town(workdir, monkeypatch):
    """Bake examples/tiny-town.toml in `workdir`, with the pack's image copied to where the project expects it."""
    pack_image = EXAMPLES / TINY_TOWN_IMAGE
    if not pack_image.exists():
        pytest.skip(f"Kenney's Tiny Town isn't at {pack_image.parent.parent}; copy the pack there (CC0)")
    work = workdir / "work"
    (work / TINY_TOWN_IMAGE).parent.mkdir(parents=True)
    shutil.copy(pack_image, work / TINY_TOWN_IMAGE)
    shutil.copy(EXAMPLES / "tiny-town.toml", work / "project.toml")
    monkeypatch.chdir(work)
    with open("project.toml", "rb") as fh:
        config = tomllib.load(fh)
    TilesetFactory().produce(config, options={"save": True, "show": False, "rotation": False}).bake()
    return work


def test_the_tiny_town_project_bakes_to_its_golden_tsx(tmp_path, monkeypatch):
    work = bake_tiny_town(tmp_path, monkeypatch)
    out = tmp_path / "out"
    out.mkdir()
    shutil.copy(work / "tiny-town.tsx", out / "tiny-town.tsx")
    assert_matches_golden("tiny-town", out)


def test_the_tiny_town_tileset_names_the_things_the_town_is_made_of(tmp_path, monkeypatch):
    work = bake_tiny_town(tmp_path, monkeypatch)
    root = ET.parse(work / "tiny-town.tsx").getroot()
    assert (root.get("columns"), root.get("tilecount"), root.get("spacing")) == ("12", "132", "1")
    assert root.find("image").get("source") == "kenney/tiny-town/Tilemap/tilemap.png"  # type: ignore[union-attr]

    named = read_tsx(work / "tiny-town.tsx")
    for name in ("grass", "road_cobble", "pine", "well", "target"):
        named.tile(name)
    assert named.tile("well").id == 104  # Tiled's gid 105, the "tile 105" Neighbots' maps say
    assert named.tile("well").properties["walkable"] is False
    assert named.tile("target").properties["walkable"] is False
    assert named.tile("grass").properties["walkable"] is True
    assert named.tile("road_cobble").properties["walkable"] is True
    assert named.tile("pine").properties["walkable"] is False
    assert named.tile("door_wood").properties["walkable"] is True
    assert named.tile("castle_wall").properties["walkable"] is False
    assert named.tile("castle_gate_left").properties["walkable"] is True
    assert len(named.tiles()) == 132  # the default reaches every tile


def test_the_tiny_town_fence_tiles_are_named_as_pieces_gaps_and_posts(tmp_path, monkeypatch):
    work = bake_tiny_town(tmp_path, monkeypatch)
    named = read_tsx(work / "tiny-town.tsx")
    ids = {"fence_nw": 44, "fence_t": 45, "fence_ne": 46, "fence_post_n": 47, "fence_w": 56, "fence_e": 58,
           "fence_v": 59, "fence_sw": 68, "fence_gap": 69, "fence_se": 70, "fence_post_s": 71,
           "fence_post_w": 80, "fence_h": 81, "fence_post_e": 82}
    for name, id in ids.items():
        assert named.tile(name).id == id, name
        assert named.tile(name).properties["kind"] == "fence"
        assert named.tile(name).properties["walkable"] is (name == "fence_gap")
    assert named.piece("castle_gateway").ids == ((123, 124),)


def test_the_tiny_town_pieces_are_grids_of_ids_anchored_on_their_doors(tmp_path, monkeypatch):
    work = bake_tiny_town(tmp_path, monkeypatch)
    named = read_tsx(work / "tiny-town.tsx")
    house = named.piece("house_wood_grey")
    assert house.ids == ((48, 49, 50), (60, 63, 62), (72, 85, 75))
    assert house.anchor_id == named.tile("door_wood").id
    assert named.piece("house_stone_red").anchor_id == named.tile("door_stone").id
    assert named.piece("castle_gate_house").ids == ((99, 100), (111, 112), (123, 124))
    assert named.piece("well_roofed").ids == ((92,), (104,))
    assert named.piece("forest_green").ids == ((6, 7, 8), (18, 19, 20), (30, 31, 32))
    for piece in named.pieces():
        assert piece.anchor_id is not None


# ---- The CLI and determinism

def test_the_cli_bakes_a_grid_project(tmp_path, monkeypatch):
    work = tmp_path / "work"
    shutil.copytree(FIXTURES / "grid", work)
    monkeypatch.chdir(work)
    result = CliRunner().invoke(cli, ["bake", "project.toml"])
    assert result.exit_code == 0, result.output
    assert result.stdout == ""
    assert (work / "grid.tsx").read_bytes() == (Path(__file__).parent / "golden/grid/grid.tsx").read_bytes()


def test_baking_a_grid_project_twice_gives_identical_files(tmp_path, monkeypatch):
    first = bake_fixture("grid", tmp_path / "one", monkeypatch)
    second = bake_fixture("grid", tmp_path / "two", monkeypatch)
    assert (first / "grid.tsx").read_bytes() == (second / "grid.tsx").read_bytes()

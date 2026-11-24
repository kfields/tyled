"""Nine-slices: pieces of three by three tiles that a map stretches to any size."""

import pytest

from test_named_tiles import bake_config, bake_tiny_town, make_grid_image
from tyled.tileset.names import NamedTilesError, NineSlice, Piece, read_tsx

COURTYARD = ((96, 97, 98), (108, 109, 110), (120, 121, 122))
DIRT = ((12, 13, 14), (24, 25, 26), (36, 37, 38))


def baked_nine_slice(tmp_path, monkeypatch, **piece):
    """A 4 × 3 synthetic grid with one nine-slice over its first three columns, baked and read back."""
    make_grid_image(tmp_path / "g.png", columns=4, rows=3)
    config = dict(
        name="g", type="grid", source=str(tmp_path / "g.png"), tilewidth=8, tileheight=8,
        pieces=[{"name": "box", "kind": "nine_slice", "region": [0, 0, 3, 3], **piece}],
    )
    bake_config(config, tmp_path / "w", monkeypatch).bake()
    return read_tsx(tmp_path / "w" / "g.tsx")


def test_a_nine_slice_is_read_back_from_the_tsx_with_its_nine_tiles(tmp_path, monkeypatch):
    named = baked_nine_slice(tmp_path, monkeypatch)
    box = named.nine_slice("box")
    assert isinstance(box, NineSlice)
    assert box.ids == ((0, 1, 2), (4, 5, 6), (8, 9, 10))
    assert box.anchor == (1, 1)  # the centre unless the project says otherwise


def test_a_nine_slice_is_stored_in_the_tsx_beside_the_pieces(tmp_path, monkeypatch):
    baked_nine_slice(tmp_path, monkeypatch)
    xml = (tmp_path / "w" / "g.tsx").read_text()
    assert '<property name="piece:box" value="0,1,2;4,5,6;8,9,10"/>' in xml
    assert '<property name="kind:box" value="nine_slice"/>' in xml


def test_a_nine_slice_can_be_given_as_rows_of_names_and_an_anchor(tmp_path, monkeypatch):
    make_grid_image(tmp_path / "g.png", columns=3, rows=3)
    tiles = [{"id": i, "name": f"t{i}"} for i in range(9)]
    rows = [[f"t{3 * r + c}" for c in range(3)] for r in range(3)]
    config = dict(
        name="g", type="grid", source=str(tmp_path / "g.png"), tilewidth=8, tileheight=8, tiles=tiles,
        pieces=[{"name": "box", "kind": "nine_slice", "rows": rows, "anchor": [0, 0]}],
    )
    bake_config(config, tmp_path / "w", monkeypatch).bake()
    box = read_tsx(tmp_path / "w" / "g.tsx").nine_slice("box")
    assert box.ids == ((0, 1, 2), (3, 4, 5), (6, 7, 8))
    assert box.anchor == (0, 0)


def test_a_plain_piece_is_not_a_nine_slice(tmp_path, monkeypatch):
    make_grid_image(tmp_path / "g.png", columns=3, rows=3)
    config = dict(
        name="g", type="grid", source=str(tmp_path / "g.png"), tilewidth=8, tileheight=8,
        pieces=[{"name": "block", "region": [0, 0, 3, 3]}],
    )
    bake_config(config, tmp_path / "w", monkeypatch).bake()
    assert "kind:block" not in (tmp_path / "w" / "g.tsx").read_text()
    named = read_tsx(tmp_path / "w" / "g.tsx")
    assert type(named.piece("block")) is Piece
    with pytest.raises(NamedTilesError, match="'block' is a piece, not a nine-slice"):
        named.nine_slice("block")


def test_a_nine_slice_stretched_to_3_by_3_is_itself(tmp_path, monkeypatch):
    box = baked_nine_slice(tmp_path, monkeypatch).nine_slice("box")
    assert box.stretch(3, 3) == box.ids


def test_a_nine_slice_stretched_to_5_by_4_repeats_its_edges_and_centre(tmp_path, monkeypatch):
    box = baked_nine_slice(tmp_path, monkeypatch).nine_slice("box")
    assert box.stretch(5, 4) == (
        (0, 1, 1, 1, 2),
        (4, 5, 5, 5, 6),
        (4, 5, 5, 5, 6),
        (8, 9, 9, 9, 10),
    )


def test_a_nine_slice_stretched_to_2_by_2_is_its_four_corners(tmp_path, monkeypatch):
    box = baked_nine_slice(tmp_path, monkeypatch).nine_slice("box")
    assert box.stretch(2, 2) == ((0, 2), (8, 10))


@pytest.mark.parametrize("width, height", [(1, 3), (3, 1), (0, 0), (-2, 5)])
def test_a_nine_slice_smaller_than_its_corners_is_an_error(width, height, tmp_path, monkeypatch):
    box = baked_nine_slice(tmp_path, monkeypatch).nine_slice("box")
    with pytest.raises(NamedTilesError, match="smallest size is 2 × 2"):
        box.stretch(width, height)


@pytest.mark.parametrize(
    "piece, message",
    [
        ({"region": [0, 0, 2, 3]}, "three rows of three tiles, not 2 × 3"),
        ({"region": [0, 0, 3, 2]}, "three rows of three tiles, not 3 × 2"),
        ({"region": None, "rows": [[0, 1, 2], [4, "", 6], [8, 9, 10]]}, "can't have gaps"),
        ({"kind": "nine-slice"}, "kind must be 'piece' or 'nine_slice'"),
    ],
)
def test_a_nine_slice_that_is_not_three_by_three_with_no_gaps_is_an_error(piece, message, tmp_path, monkeypatch):
    make_grid_image(tmp_path / "g.png", columns=4, rows=3)
    entry = {"name": "box", "kind": "nine_slice", "region": [0, 0, 3, 3], **piece}
    entry = {k: v for k, v in entry.items() if v is not None}
    config = dict(name="g", type="grid", source=str(tmp_path / "g.png"), tilewidth=8, tileheight=8, pieces=[entry])
    with pytest.raises(NamedTilesError, match=message):
        bake_config(config, tmp_path / "w", monkeypatch).bake()


# ---- Tiny Town: the courtyard and the dirt patch

def test_the_tiny_town_courtyard_and_dirt_patch_are_nine_slices(tmp_path, monkeypatch):
    named = read_tsx(bake_tiny_town(tmp_path, monkeypatch) / "tiny-town.tsx")
    assert named.nine_slice("castle_courtyard").ids == COURTYARD
    assert named.nine_slice("dirt_patch").ids == DIRT
    assert named.nine_slice("castle_courtyard").anchor_id == 109


def test_the_tiny_town_courtyard_stretched_to_5_by_4_is_a_grid_of_ids(tmp_path, monkeypatch):
    named = read_tsx(bake_tiny_town(tmp_path, monkeypatch) / "tiny-town.tsx")
    assert named.nine_slice("castle_courtyard").stretch(5, 4) == (
        (96, 97, 97, 97, 98),
        (108, 109, 109, 109, 110),
        (108, 109, 109, 109, 110),
        (120, 121, 121, 121, 122),
    )
    assert named.nine_slice("dirt_patch").stretch(4, 3) == (
        (12, 13, 13, 14),
        (24, 25, 25, 26),
        (36, 37, 37, 38),
    )


def test_only_the_centre_of_the_tiny_town_courtyard_can_be_walked_on(tmp_path, monkeypatch):
    named = read_tsx(bake_tiny_town(tmp_path, monkeypatch) / "tiny-town.tsx")
    walkable = {id: named.tile_by_id(id).properties["walkable"] for row in COURTYARD for id in row}
    assert [id for id, free in walkable.items() if free] == [109]
    assert all(named.tile_by_id(id).properties["walkable"] for row in DIRT for id in row)


def test_the_tiny_town_doors_and_gate_passage_stay_walkable(tmp_path, monkeypatch):
    named = read_tsx(bake_tiny_town(tmp_path, monkeypatch) / "tiny-town.tsx")
    for name in ("doorway_wood", "doorway_stone", "door_wood", "door_wood_arch", "door_wood_right",
                 "door_stone", "door_stone_arch", "door_stone_right", "castle_gate_left", "castle_gate_right"):
        assert named.tile(name).properties["walkable"] is True, name


def test_the_two_tile_trees_have_top_and_bottom_halves_and_the_single_trees_keep_their_names(tmp_path, monkeypatch):
    named = read_tsx(bake_tiny_town(tmp_path, monkeypatch) / "tiny-town.tsx")
    ids = {name: named.tile(name).id for name in
           ("pine_autumn_top", "pine_autumn_bottom", "pine_top", "pine_bottom", "pine_autumn", "pine")}
    assert ids == {"pine_autumn_top": 3, "pine_autumn_bottom": 15, "pine_top": 4, "pine_bottom": 16,
                   "pine_autumn": 27, "pine": 28}
    for old in ("pine_autumn_small", "pine_small", "pine_autumn_trunk", "pine_trunk"):
        assert old not in named.names()
    assert named.piece("pine_tall").ids == ((4,), (16,))
    assert named.piece("pine_autumn_tall").ids == ((3,), (15,))

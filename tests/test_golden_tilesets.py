"""Each kind of tileset, baked from a small fixture project, against its golden files."""

from bakehelp import assert_matches_golden, bake_fixture, files_under


def test_a_collection_tileset_matches_its_golden_tsx(tmp_path, monkeypatch):
    out = bake_fixture("collection", tmp_path, monkeypatch)
    assert_matches_golden("collection", out)


def test_an_orthogonal_tileset_matches_its_golden_tsx_and_image(tmp_path, monkeypatch):
    out = bake_fixture("orthogonal", tmp_path, monkeypatch)
    assert_matches_golden("orthogonal", out)


def test_an_atlas_tileset_matches_its_golden_tsx_and_image(tmp_path, monkeypatch):
    out = bake_fixture("atlas", tmp_path, monkeypatch)
    assert_matches_golden("atlas", out)


def test_a_sheet_tileset_matches_its_golden_tsx_image_and_cut_sprites(tmp_path, monkeypatch):
    out = bake_fixture("sheet", tmp_path, monkeypatch)
    assert_matches_golden("sheet", out)


def test_a_slice_tileset_matches_its_golden_tsx_and_cut_sprites(tmp_path, monkeypatch):
    out = bake_fixture("slice", tmp_path, monkeypatch)
    assert_matches_golden("slice", out)


def test_an_atlas_baked_with_rotation_matches_its_golden_tsx_and_image(tmp_path, monkeypatch):
    out = bake_fixture("rotation", tmp_path, monkeypatch)
    assert_matches_golden("rotation", out)
    # The fixture is built so that tiles must turn; if none did, the test would prove nothing.
    assert 'angle="90"' in (out / "rotation.tsx").read_text()


def test_baking_the_same_project_twice_gives_identical_files(tmp_path, monkeypatch):
    for kind in ("collection", "orthogonal", "atlas", "sheet", "slice", "rotation"):
        first = bake_fixture(kind, tmp_path / kind / "one", monkeypatch)
        second = bake_fixture(kind, tmp_path / kind / "two", monkeypatch)
        assert files_under(first) == files_under(second)
        for name in files_under(first):
            assert (first / name).read_bytes() == (second / name).read_bytes(), (kind, name)

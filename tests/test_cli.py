"""The command line: it reads TOML project files and bakes through the library."""

import shutil

from click.testing import CliRunner

from bakehelp import FIXTURES, assert_matches_golden, files_under
from tyled.command import cli


def start_in_a_copy_of(kind, tmp_path, monkeypatch):
    work = tmp_path / "work"
    shutil.copytree(FIXTURES / kind, work)
    monkeypatch.chdir(work)
    return work


def test_bake_writes_the_tileset_and_image_next_to_where_it_is_run(tmp_path, monkeypatch):
    work = start_in_a_copy_of("orthogonal", tmp_path, monkeypatch)
    result = CliRunner().invoke(cli, ["bake", "project.toml"])
    assert result.exit_code == 0, result.output
    assert {"orthogonal.tsx", "orthogonal.png"} <= files_under(work)
    out = tmp_path / "out"
    out.mkdir()
    for name in ("orthogonal.tsx", "orthogonal.png"):
        shutil.copy(work / name, out / name)
    assert_matches_golden("orthogonal", out)


def test_bake_prints_nothing_to_standard_output(tmp_path, monkeypatch):
    start_in_a_copy_of("collection", tmp_path, monkeypatch)
    result = CliRunner().invoke(cli, ["bake", "project.toml"])
    assert result.exit_code == 0, result.output
    assert result.stdout == ""


def test_bake_with_no_save_writes_no_files(tmp_path, monkeypatch):
    work = start_in_a_copy_of("orthogonal", tmp_path, monkeypatch)
    before = files_under(work)
    result = CliRunner().invoke(cli, ["bake", "--no-save", "project.toml"])
    assert result.exit_code == 0, result.output
    assert files_under(work) == before


def test_bake_takes_rotation_from_the_command_line(tmp_path, monkeypatch):
    work = start_in_a_copy_of("atlas", tmp_path, monkeypatch)
    (work / "project.toml").write_text(
        (work / "project.toml").read_text().replace("width = 32\nheight = 32", "width = 32\nheight = 8")
    )
    result = CliRunner().invoke(cli, ["bake", "--rotation", "project.toml"])
    assert result.exit_code == 0, result.output
    assert 'angle="90"' in (work / "atlas.tsx").read_text()


def test_options_in_the_project_file_win_over_the_command_line(tmp_path, monkeypatch):
    work = start_in_a_copy_of("rotation", tmp_path, monkeypatch)
    result = CliRunner().invoke(cli, ["bake", "--no-rotation", "project.toml"])
    assert result.exit_code == 0, result.output
    assert 'angle="90"' in (work / "rotation.tsx").read_text()


def test_export_writes_only_the_tsx(tmp_path, monkeypatch):
    work = start_in_a_copy_of("collection", tmp_path, monkeypatch)
    before = files_under(work)
    result = CliRunner().invoke(cli, ["export", "project.toml"])
    assert result.exit_code == 0, result.output
    assert files_under(work) - before == {"collection.tsx"}


def test_a_project_file_that_does_not_exist_is_an_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(cli, ["bake", "nothing.toml"])
    assert result.exit_code != 0

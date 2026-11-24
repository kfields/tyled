"""Shared helpers for the golden-file tests: bake a fixture project and compare its outputs.

A bake writes into the current folder, so each test copies its fixture into a temporary
folder, works there, and looks only at the files the bake added.
"""

import shutil
import tomllib
from pathlib import Path

from PIL import Image

from tyled.tileset.factory import TilesetFactory

FIXTURES = Path(__file__).parent / "fixtures"
GOLDEN = Path(__file__).parent / "golden"


def files_under(folder: Path) -> set[str]:
    return {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}


def bake_fixture(kind: str, workdir: Path, monkeypatch, **options) -> Path:
    """Bake tests/fixtures/<kind>/project.toml in `workdir`; return a folder holding only the outputs."""
    work = workdir / "work"
    shutil.copytree(FIXTURES / kind, work)
    monkeypatch.chdir(work)
    before = files_under(work)

    with open("project.toml", "rb") as fh:
        config = tomllib.load(fh)
    options = {"save": True, "show": False, "rotation": False, **options}
    TilesetFactory().produce(config, options=options).bake()

    out = workdir / "out"
    for name in sorted(files_under(work) - before):
        (out / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(work / name, out / name)
    return out


def assert_matches_golden(kind: str, out: Path) -> None:
    """Same set of files as tests/golden/<kind>; .tsx byte for byte, images pixel for pixel."""
    golden = GOLDEN / kind
    assert files_under(out) == files_under(golden)
    for name in sorted(files_under(golden)):
        if name.endswith(".png"):
            got, want = Image.open(out / name), Image.open(golden / name)
            assert got.mode == want.mode, name
            assert got.size == want.size, name
            assert got.tobytes() == want.tobytes(), f"{name} differs in pixels"
        else:
            assert (out / name).read_bytes() == (golden / name).read_bytes(), name

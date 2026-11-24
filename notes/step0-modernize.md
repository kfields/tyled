# Step 0: modernize, with tests

Drafted 2026-11-24 by the planning chat. Nothing new: tyled as it is, on Python 3.12, with tests, so the
map work starts on firm ground.

## Criteria

- **C1** Python 3.12: `pyproject.toml` already says `>=3.12` and Pillow 10+ (Kurt's edit). The code runs
  on them: whatever Pillow 10 removed (`Image.ANTIALIAS` and the like) replaced.
- **C2** `tomllib` from the standard library reads project files (binary mode, as it requires); say in the
  report that the `toml` dependency can then be dropped (`pyproject.toml` is Kurt's to edit).
- **C3** Golden-file tests for each tileset kind (collection, orthogonal, atlas, sheet, slice, rotation),
  each baking a small project from its own fixture under `tests/fixtures/` into a temporary folder and
  comparing the `.tsx` (and the packed image, pixel for pixel) with `tests/golden/`. Where output isn't
  deterministic today (an order taken from the file system, a timestamp), make it so, and say what.
- **C4** The CLI's `print(vars(tileset.options))` becomes a log line or goes; the CLI is tested with
  click's `CliRunner`.
- **C5** `sheet copy.py` (a stray copy beside `sheet.py`) and anything else unused: say what, and remove
  only what nothing imports.
- **C6** The README's install section matches today (a `.venv`, `pip install -e ".[test]"`).

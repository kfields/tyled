# tyled: rules for every change

tyled is a Python library and CLI for making [Tiled](https://www.mapeditor.org/) tilesets and, now, maps:
it bakes tilesets (`.tsx`, with a packed image where needed) from a TOML project file, and is growing to
name tiles, generate maps from text layouts, render and check them, and serve map editing to agents.
`notes/plan.md` has the plan and the reasons; read it before a change that adds a feature.

## The shape of the project

- **Python 3.12, a library first and a thin CLI over it.** Everything the CLI does is a function or class
  a program can call (`tyled.map`, `tyled.tileset`, ...); `tyled/command/` only parses arguments and
  calls them. Neighbots and other projects will import the library, not run the CLI.
- **Tiled's own formats, read and written as Tiled does:** tilesets as `.tsx` (XML) or `.tsj`, maps as
  `.tmj` (JSON) or `.tmx`; a file tyled writes opens in Tiled without a warning and survives a save there.
  Global tile ids (gids) follow Tiled's rules: a map's tilesets each have a `firstgid`, and the high bits
  are flip flags.
- **Deterministic output:** the same project file and inputs give byte-identical files, so outputs can
  be diffed and tested against golden files. Randomness, where a feature wants it, comes from a seed.
- **Project files are TOML,** read with the standard library's `tomllib`.

## Assets

- Example art lives under `examples/`, each pack with its license. Never fetch assets or packages:
  there is no network where the agent works. If something is missing, say what and where it should go.

## Tests

- pytest, under `tests/`, one file per feature (`tests/test_<feature>.py`), each test named as a sentence.
- Outputs are compared with golden files under `tests/golden/`; a golden file is changed only on purpose,
  with the reason in the report.
- Tests write only to temporary folders, never into `examples/` or the project's tracked files.

## Writing

- Docstrings say what a thing is for and why, in plain sentences; comments explain decisions, not
  mechanics.
- The README says how to install and use tyled; change it when a change alters either.

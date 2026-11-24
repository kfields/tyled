# tyled: from tilesets to maps

Drafted 2026-11-24 by the planning chat. Kurt: "I wanted to go beyond tileset generation but I never
thought about tilemap generation. Let's do it!"

## Why

tyled bakes Tiled tilesets from TOML project files (collection, orthogonal, atlas, sheet). Making
**maps** is the natural next chapter, and Neighbots needs one now: a 3 × 3 town (90 × 60 tiles of 16 px,
a town square in the middle, a castle, a farm, neighborhoods, forest and meadow) from Kenney's Tiny Town,
Tiny Farm and Tiny Dungeon. Drawing that by hand in Tiled is slow; placing hundreds of tile ids in JSON
by hand is error-prone. A text layout turned into a map by tyled can be regenerated, enlarged and
rearranged at will, and later Questbots' chapter maps can come from the same tool.

## Steps, smallest first

0. **Modernize:** Python 3.12, `tomllib` instead of `toml`, Pillow 10+, pytest with golden-file tests
   for the existing tileset kinds (`notes/step0-modernize.md`). Nothing new.
1. **Named tiles:** a tileset's tiles get names and properties from the project file (`target`, `well`,
   `walkable = false`), written as Tiled tile properties, so layouts, code and agents say "well", not
   "tile 105"; including naming regions of an existing tilemap image (Kenney's), and multi-tile pieces.
2. **`tyled map`:** a map from a text layout: a legend from characters to named tiles, stamps (multi-tile
   pieces such as a house or a castle tower placed by a character), several layers (ground, things on
   it, collision), and an objects layer; written as `.tmj`.
   Tiles placed rotated or flipped (Tiled's flag bits on a gid), so one fence or road-edge tile serves
   every direction, which matters with small packs.
3. **`tyled render` and `tyled check`:** a PNG of a map or a region (so an agent can see its work), and
   checks: walkability from tile properties, objects on free tiles, every place reachable.
4. **Terrains (Wang sets):** declared in the tileset, so Tiled and `tyled map` pick edges and corners
   (road edges, grass meeting dirt) themselves.
5. **Merging packs:** several tilesets into one atlas with one namespace of tile names.
6. **`tyled mcp`:** a map-editing MCP server over the library (list tiles, set and fill, stamp, add
   objects, render, check), working on files only: Tiled reloads a map changed on disk, so a person
   watching sees the agent's edits live, with no editor plugin and no scripting.

## Decided

1. Kurt decided to take tyled from tilesets to maps (2026-11-24, quoted above).
2. The planning chat proposed working on files, not the Tiled editor, for the MCP server (step 6):
   Tiled's scripting API runs with the user's full rights (files, processes), which an agent shouldn't
   reach; a server that edits files gets the live view through Tiled's reload.

## Open questions

- **Rotated tiles in a packed atlas** (`--rotation`, from `rectpack`): tyled records `angle="90"` on such a
  tile in the `.tsx`, which Tiled may not read (it rotates tiles placed in a map, by flag bits, not tiles in
  a tileset's image). Check in Tiled whether they show upright; if not, unrotate them when writing, or
  drop the option. Step 0's golden file pins today's output.

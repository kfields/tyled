# Step 3: `tyled render`, `tyled sheet` and `tyled check`

Drafted 2026-11-24 by the planning chat, from `notes/plan.md`, step 3.

The problem: a map tyled builds can only be seen by opening it in Tiled, so neither an agent nor a test can
look at it; a tileset's names can only be checked by eye, tile by tile; and nothing says whether a map works
as a place (a door that opens into a tree, a field nobody can reach). This step lets tyled draw maps and
tilesets to images and check maps as places, so an agent can design a town by looking at what it built, and
tests can hold a map to more than its file.

## Criteria

- **C1** `tyled render MAP` (and `tyled.render.render_map` in the library) draws a `.tmj` (or a `.world`) to a
  PNG: every tile layer in order, rotations and flips applied as Tiled applies them, tile objects drawn
  where Tiled draws them, at a chosen scale (nearest-neighbour, so pixel art stays sharp); `--region x,y,w,h`
  in tiles draws a part; `--layers` chooses layers; optional object labels and a tile grid. Deterministic:
  the same map gives the same PNG, byte for byte.
- **C2** `tyled sheet TILESET` draws a tileset as a contact sheet: each tile enlarged, with its id and name
  under it, and a border marking a property (by default `walkable = false`), pieces and nine-slices outlined
  with their names; the way to check a tileset's names against its art at a glance. (The planning chat made
  one by hand for Tiny Town on 2026-11-24, and it found a misnamed pair of tree halves.)
- **C3** `tyled check MAP` checks a map as a place, from its tiles' properties, and reports each problem with
  where it is:
  - every object stands on a walkable tile, or beside one if the object itself blocks;
  - every walkable tile and object can be reached from every other (or from a named start), listing the
    regions cut off;
  - every door has a walkable tile in front of it (a tile property names which side a door opens to, or the
    tile below by default);
  - tiles with no name or unknown to the tileset, and layers the project doesn't declare.
  Exit status 1 when anything is wrong; `--json` for programs.
- **C4** The library returns what the commands print (an image; a list of findings with kinds and
  positions), so Neighbots and tests can use them without the CLI.
- **C5** Tests: rendering against golden PNGs (the town example, a region, a rotated and flipped tile, an
  object), the contact sheet against a golden PNG, each check finding a planted problem and passing the
  town example, `--json`'s shape; step 0's, 1's and 2's golden files unchanged.

## Decided

1. Kurt decided to take tyled from tilesets to maps (`notes/plan.md`).
2. The planning chat proposed the contact sheet (C2) after checking Tiny Town's names by drawing one.

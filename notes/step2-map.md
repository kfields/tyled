# Step 2: `tyled map`, a map from a text layout

Drafted 2026-11-24 by the planning chat, from `notes/plan.md`, step 2.

The problem: a map is hundreds of tile ids in a JSON file. With names, pieces and nine-slices from step 1,
a map can be drawn as text instead, a character a tile, and turned into a Tiled map that can be
regenerated, enlarged and rearranged at will. Neighbots needs one now (a 3 × 3 town of 90 × 60 tiles),
and reads a map by convention: a tile layer `ground`, a tile layer `obstacles` (any tile on it blocks), and
an object layer `objects` whose tile objects' `type` names a smart object (`food_stall`, `bench`, ...).

## Criteria

- **C1** A map project file (TOML) names its tilesets (step 1's projects or `.tsx` files, each given its
  `firstgid` in order, as Tiled does), a layout file, a legend, and the tile size; `tyled map town.toml`
  (and `tyled.map.build(...)` in the library) writes a `.tmj` that opens in Tiled without a warning.
- **C2** The layout: a text file, one character a tile, every line the same length (an error names the
  line otherwise). A ground fill for characters with nothing else (grass, say), so a layout draws only
  what's on the ground.
- **C3** The legend maps a character to a named tile, a piece or a nine-slice, by name, with optional
  rotation or flip (Tiled's flag bits on the gid), so one fence or edge tile serves every direction:
  - **a tile:** placed where the character is;
  - **a piece:** placed so its anchor lands on the character (a house's door where `H` is); the piece's
    other cells in the layout must be the same character or a filler (`.`), and a piece running off the
    map or over another is an error naming both;
  - **a nine-slice:** a rectangle of the same character becomes the nine-slice stretched to it (a castle
    courtyard as big as the rectangle); a shape that isn't a rectangle is an error.
- **C4** Layers: each placed tile goes on a layer the legend or its tile's properties choose. By default a
  tile with `walkable = false` goes on `obstacles` and the rest on `ground`, the layer names set in the
  project file, so Neighbots' convention comes out without saying it for every entry.
- **C5** Objects: a legend entry may place a tile object on an object layer instead (`objects`), with a
  name and a `type` (from the entry, or the tile's `kind` property), positioned as Tiled positions tile
  objects (x at the left, y at the bottom of the tile).
- **C6** Deterministic: the same project, layout and tilesets give a byte-identical `.tmj`; a layout
  character the legend doesn't know is an error naming it and its line and column.
- **C7** A worked example under `examples/`: a small town on Tiny Town (30 × 20, Neighbots' size today)
  with grass, roads, a dirt patch, houses (pieces, doors on the road), trees, a castle courtyard
  (nine-slice) with its gate, and objects (a food stall, a bench, the well, the target); the README shows
  its layout and how to build it.
- **C8** Tests: each legend kind placed, with rotation and flip; a piece by its anchor, off the map and
  overlapping; a nine-slice stretched and a non-rectangle refused; layers by walkability; objects'
  positions and types; the example against a golden `.tmj`; unknown characters and ragged lines refused;
  and step 0's and step 1's golden files unchanged.

## Decided

1. Kurt decided to take tyled from tilesets to maps (`notes/plan.md`).
2. The planning chat proposed Neighbots' layer convention as tyled's default (`ground`, `obstacles`,
   `objects`), configurable, so the first real user needs no extra settings and others can rename.
3. Placing tiles rotated or flipped is in this step (`notes/plan.md`'s note): small packs need it.

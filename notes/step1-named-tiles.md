# Step 1: named tiles and pieces

Drafted 2026-11-24 by the planning chat, from `notes/plan.md`, step 1.

The problem: everything that uses a tileset refers to tiles by number. Neighbots' code and maps say "tile
105" for the well; a text layout, a generator or an agent can't work like that. Kenney's packs come as a
grid image (Tiny Town: 12 × 11 tiles of 16 px with 1 px between them, `Tilemap/tilemap.png`) with no
names at all, and the interesting things in them are often several tiles together: a house is a roof row
over a wall row with a door, a castle tower is a block of tiles. This step lets a project file name the
tiles of an existing grid image, give them properties, and name multi-tile pieces, so that step 2's maps
can be written in names.

## Criteria

- **C1** A tileset kind for an existing grid image, used as it is (nothing repacked, the image left where
  it is and referenced): tile size, spacing, margin and columns from the project file, or read from the
  image when they can be. It writes a `.tsx` that Tiled opens, matching Kenney's own `sampleSheet.tsx` for
  the same image apart from what this step adds.
- **C2** Names: the project file names tiles by column and row (or by id), each name unique in the
  tileset, written into the `.tsx` as a tile property Tiled shows (`name`), and readable back by the
  library (`tileset.tile("well")` gives its id and properties; a misspelled name is an error suggesting
  the nearest names).
- **C3** Properties: any tile may carry typed properties (`walkable = false`, `kind = "food_stall"`),
  written as Tiled custom properties with Tiled's types (string, int, float, bool), and a default for
  every tile (`walkable = true` unless said otherwise).
- **C4** Pieces: a name for a rectangle of tiles (a house, a tower, a tree two tiles tall), given as a
  region of the image or as rows of tile names, with an anchor (which tile of the piece a layout's
  character stands for: the door, say), readable by the library as a grid of tile ids. Where pieces are
  kept so Tiled and tyled both see them is this step's choice: say what was chosen and why (Tiled's own
  stamps, tileset properties, or a file of tyled's own beside the `.tsx`).
- **C5** A project file naming Kenney's Tiny Town as the worked example, under `examples/`: the ground
  tiles, roads, trees, the well, the target, the houses (pieces), the castle walls and gate (pieces), with
  `walkable` right for each. Kurt copies the pack into `examples/kenney/tiny-town/` (CC0, with its
  `License.txt`); if it isn't there, say so and use a small synthetic grid for the tests.
- **C6** Tests: a grid tileset's `.tsx` against a golden file; names and properties written and read back;
  a misspelled name; a piece read as its grid of ids, from a region and from rows of names; the Tiny Town
  project baking; and the six existing kinds' golden files unchanged.

## Decided

1. Kurt decided to take tyled from tilesets to maps (`notes/plan.md`).
2. The planning chat proposed names, properties and pieces as their own step before maps, so step 2's
   layouts are written in names from the start.

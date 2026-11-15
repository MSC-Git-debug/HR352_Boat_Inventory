# Hull Watertight Repair (Blender Add-on)

Blender add-on to **analyze, close holes and make boat hull meshes watertight**, designed for step-by-step intervention on complex meshes so you stay in control before anything destructive happens.

Tested on Blender 4.2 LTS (works with 2.80+).

## Install

1. Download `hull_watertight.py` from this folder.
2. In Blender: `Edit > Preferences > Add-ons > Install...` and select the file.
3. Enable **Mesh: Hull Watertight Repair**.
4. Open the sidebar in the 3D Viewport (`N`) → **Hull Fix** tab.

## Recommended workflow (intervene before it goes too far)

1. **Duplicate your hull object first** (`Shift+D`, `Esc`) and work on the copy.
2. **Analyze Mesh** — shows holes (boundary loops), non-manifold edges, islands, watertight status. Nothing is modified.
3. **Inspect** — `Select Hole Edges` / `Select Non-Manifold` highlight the problem areas so you can look at them before filling.
4. **Step by Step Repair** (in this order):
   - **Merge by Distance** — welds duplicated vertices; a small threshold (0.0001 m) often removes many "false" holes. Increase gradually if holes remain.
   - **Delete Loose** — removes stray vertices/edges.
   - **Delete Interior Faces** — removes hidden inner walls.
   - **Dissolve Degenerate** — cleans zero-length edges.
5. **Fill Holes** — close the remaining holes:
   - **Max Hole Size (edges)** protects big openings (cockpit, hatches): only holes with at most this many boundary edges get filled. `0` = fill everything.
   - **Only Selected** — fill only the holes you inspected/selected.
6. **Recalc Normals Outside** — makes normals consistent and outward-facing.
7. **Analyze Mesh** again — repeat steps 4–6 until **Watertight: YES**.

### One-Click

**Full Watertight Fix** runs the whole pipeline (each step individually toggleable in the panel) and reports holes/non-manifold counts before → after. Use it on a duplicate first, then review the result before replacing your original.

## Verification

`tests/test_hull_watertight.py` runs the add-on headless against meshes with known holes:

```bash
blender -b --factory-startup --python tests/test_hull_watertight.py
```

Covers: hole detection, fill, max-hole-size protection, merge-by-distance + loose geometry cleanup via the full pipeline, and selection helpers. All 11 checks pass on Blender 4.2.14.

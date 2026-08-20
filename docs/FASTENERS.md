# CubeBot fasteners

Hole census measured directly from the real STLs by cross-section sweeping
(slice each part on all three axes, classify internal voids by circularity and
corner count, stack consecutive slices into features). Diameters carry roughly
**±0.2 mm** because the exported meshes are decimated to ~10k triangles — the
Ø1.8 / 1.9 / 2.0 spread is almost certainly one nominal size.

## Holes, by part

    Servo Casing 1  x4   7x Ø1.8
    Servo Casing 2  x4   2x Ø1.8, 4x Ø2.3
    Servo Casing 3  x4   1x Ø2.3
    Leg-Body Conn.  x4   2x Ø4.8, 1x Ø7.5
    Leg             x4   2x Ø1.8, 1x Ø4.0, 1x Ø4.8, 2x Ø7.5
    Top Cover       x1   2x Ø1.8
    Bottom Cover    x1   2x Ø2.0, 4x Ø3.3, 4x Ø3.5, 12x Ø6.0
    Body Frame      x1   4x Ø1.9, 6x Ø2.0, 3x Ø3.1, 8x Ø3.3, 7x Ø3.5, 4x Ø6.0

## Totals

| Ø mm | holes | role | size |
|---|---|---|---|
| 1.8 | 46 | pilot | M2 |
| 1.9 | 4 | pilot | M2 |
| 2.0 | 8 | pilot | M2 |
| 2.3 | 20 | clearance | M2 |
| 3.1 | 3 | pilot (only 3 mm deep) | M3 |
| 3.3 | 12 | pilot | M3 |
| 3.5 | 11 | clearance | M3 |
| 4.0 | 4 | clearance | M4? |
| 4.8 | 12 | clearance | M4? |
| 6.0 / 7.0 / 7.5 | 29 | **not fasteners** — bearings, shafts, cable routes | |

**There are no nut traps anywhere in this design.** Every screw self-taps into a
plastic boss, so the pilot count is the screw count: **58 M2, 15 M3**.

## Versus the purchased BOM

| size | BOM bought | needed | shortfall |
|---|---|---|---|
| M2 | 46 (32×8, 10×10, 4×15) | 58 | **+12** |
| M3 | 4 (M3×10) | 15 | **+11** |
| M4 | 0 | 16? | **unresolved** |

Buy: **+12 M2×8, +12 M3×10, +6 M3×6**. The M3×6 is not a spare — three of the
Body Frame pilots are the Ø3.1 stepped holes at only **3 mm deep**, and a 10 mm
screw bottoms out in them.

## The M4 question — verify before ordering

Sixteen Ø4.0–4.8 holes sit **2 per Leg-Body Connector and 2 per Leg**, directly
beside Ø7.5 bores that are clearly bearing or servo-horn seats. That is the hip
pivot. They are more likely **pins or shoulder bolts than screws**, since a
threaded fastener biting plastic at a rotating joint is poor practice.

Open one Leg-Body Connector and check whether the Ø4.8 runs clean through or
lands in a boss. Through-hole beside a bearing seat -> dowel pin or shoulder
screw, not a machine screw.

## Caveat

Holes were counted in **isolated parts, not an assembly**, so which hole pairs
with which is inferred. Quantities are right to within a few; length assignment
beyond what the original BOM specifies is inference.

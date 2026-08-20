"""BOM-accurate mass model for the CubeBot trunk.

Total mass alone is not enough for locomotion RL. A uniform 534 g box has the
right weight and the wrong inertia: 188 g of that is four 18650 cells which sit
low in the case, and where they sit sets the CoM height, the pitch/roll inertia,
and therefore how the robot recovers from a push. The plan's own Phase 4
debugging order ends "...mass/CoM third", so it needs to be right before then.

Source of every number is tagged:
  MEASURED  - nothing yet. Put the six items in WEIGH_THESE on a scale.
  DATASHEET - manufacturer figure.
  TYPICAL   - representative part of that class; +/-30% is possible.
  DERIVED   - computed from CAD mesh volume x material model.

POSITIONS ARE ASSUMED. The BOM lists what is in the robot, not where. The
layout below is a physically sensible build (cells low for a low CoM, Pi on a
deck above them, camera forward) but it is not read from CAD. Correct the
`pos` column once the real layout is known -- it is the only thing standing
between this model and a genuinely accurate one.

Trunk frame: origin at the centre of the 125 x 105 x 82.4 mm case envelope.
x = fore(+)/aft(-), y = left(+)/right(-), z = up(+). Millimetres, grams.
"""
from __future__ import annotations

import numpy as np

# name, grams, (x, y, z) mm, source, rough size (mm) for the inertia of the item itself
COMPONENTS = [
    # --- power: heaviest cluster, deliberately low -------------------
    ("cell_18650_1",   47.0, (  0,  -30, -28), "TYPICAL",   (65, 18.5, 18.5)),
    ("cell_18650_2",   47.0, (  0,  -10, -28), "TYPICAL",   (65, 18.5, 18.5)),
    ("cell_18650_3",   47.0, (  0,   10, -28), "TYPICAL",   (65, 18.5, 18.5)),
    ("cell_18650_4",   47.0, (  0,   30, -28), "TYPICAL",   (65, 18.5, 18.5)),
    ("bms_4s",         10.0, (-45,    0, -14), "TYPICAL",   (50, 20, 4)),
    ("ubec_left",      10.0, (-45,   35, -14), "TYPICAL",   (30, 15, 10)),
    ("ubec_right",     10.0, (-45,  -35, -14), "TYPICAL",   (30, 15, 10)),
    ("power_switch",    5.0, (-58,    0,  10), "TYPICAL",   (20, 13, 13)),
    ("power_conn",      5.0, (-58,   20,  10), "TYPICAL",   (12, 12, 12)),
    ("usbc_conn",       5.0, (-58,  -20,  10), "TYPICAL",   (12, 12, 12)),

    # --- compute ------------------------------------------------------
    ("raspberry_pi5",  46.0, (  0,    0,   6), "DATASHEET", (85, 56, 12)),
    ("pico2",           3.0, ( 30,   35,  22), "DATASHEET", (51, 21, 4)),
    ("pcb_proto",      15.0, (  0,    0,  22), "TYPICAL",   (70, 50, 3)),
    ("gpio_header",     5.0, (  0,   25,  14), "TYPICAL",   (51, 5, 9)),
    ("pin_headers",     3.0, (  0,  -25,  22), "TYPICAL",   (40, 5, 9)),
    ("header_4pin",     1.0, ( 20,  -25,  22), "TYPICAL",   (10, 5, 9)),

    # --- sensing ------------------------------------------------------
    ("wt901_imu",       8.0, (  0,    0,  14), "TYPICAL",   (36, 16, 8)),
    ("camera_v3",       4.0, ( 55,    0,  12), "DATASHEET", (25, 24, 9)),

    # --- yaw servos: one per leg, at the hip mounts -------------------
    ("yaw_servo_FL",   13.4, ( 46.5,  38.5, -20), "DATASHEET", (23, 12, 29)),
    ("yaw_servo_FR",   13.4, ( 46.5, -38.5, -20), "DATASHEET", (23, 12, 29)),
    ("yaw_servo_BL",   13.4, (-46.5,  38.5, -20), "DATASHEET", (23, 12, 29)),
    ("yaw_servo_BR",   13.4, (-46.5, -38.5, -20), "DATASHEET", (23, 12, 29)),

    # --- structure: printed shells, from CAD volumes ------------------
    ("bottom_case",    56.2, (  0,    0, -36), "DERIVED",   (115, 93, 18)),
    ("top_case",       55.7, (  0,    0,  34), "DERIVED",   (125, 105, 40)),

    # --- distributed: wiring, connectors, fasteners -------------------
    ("wiring_harness", 10.0, (  0,    0,   0), "TYPICAL",   (100, 80, 60)),
    ("batt_connectors",12.0, (-30,    0, -20), "TYPICAL",   (40, 30, 15)),
    ("screws_m2x8",    16.0, (  0,    0,   0), "TYPICAL",   (110, 90, 70)),
    ("screws_m2x10",    5.5, (  0,    0,   0), "TYPICAL",   (110, 90, 70)),
    ("screws_m2x15",    3.0, (  0,    0,   0), "TYPICAL",   (110, 90, 70)),
    ("screws_m3x10",    4.4, (  0,    0, -36), "TYPICAL",   ( 90, 60, 10)),
]

# The six weighings that would collapse most of the remaining uncertainty,
# in descending order of how much they move the answer.
WEIGH_THESE = [
    ("printed bottom case", 56.2, "DERIVED from mesh volume x assumed 0.36 fill; the mesh is a solid block so this carries a guessed 0.65 correction. Worst-known number in the model."),
    ("printed top case",    55.7, "DERIVED from mesh volume x assumed 0.36 fill. Real infill is unknown."),
    ("one 18650 cell",      47.0, "x4 = 188 g, the single heaviest cluster. Cells vary 42-50 g."),
    ("one printed femur",   19.6, "x4, and it is the link whose inertia the shoulder servo actually fights."),
    ("assembled robot",    743.0, "The check that catches everything above at once."),
    ("one MG90S",           13.4, "x12. Clones vary."),
]


def _box_inertia(mass_g, size_mm):
    """Solid-box inertia about the item's own centre, kg.m^2."""
    m = mass_g / 1000.0
    a, b, c = (np.array(size_mm) / 1000.0)
    return np.diag([m * (b*b + c*c) / 12.0,
                    m * (a*a + c*c) / 12.0,
                    m * (a*a + b*b) / 12.0])


def trunk_inertial():
    """Total mass, CoM, and full inertia tensor of the trunk assembly.

    Parallel-axis every component onto the trunk frame, then shift the whole
    thing to the CoM -- which is what MuJoCo's <inertial> element expects.
    """
    total = sum(c[1] for c in COMPONENTS) / 1000.0
    pos = np.array([c[2] for c in COMPONENTS], dtype=float) / 1000.0
    mass = np.array([c[1] for c in COMPONENTS], dtype=float) / 1000.0
    com = (pos * mass[:, None]).sum(0) / total

    I = np.zeros((3, 3))
    for (name, g, p, src, size), m_kg in zip(COMPONENTS, mass):
        r = np.array(p, dtype=float) / 1000.0 - com
        I += _box_inertia(g, size)                      # own inertia
        I += m_kg * (np.dot(r, r) * np.eye(3) - np.outer(r, r))  # parallel axis
    return total, com, I


def report():
    total, com, I = trunk_inertial()
    print(f"{'component':20s}{'g':>8s}{'x':>7s}{'y':>7s}{'z':>7s}   source")
    print("-" * 66)
    for name, g, p, src, _ in COMPONENTS:
        print(f"{name:20s}{g:8.1f}{p[0]:7.0f}{p[1]:7.0f}{p[2]:7.0f}   {src}")
    print("-" * 66)
    print(f"{'TRUNK TOTAL':20s}{total*1000:8.1f}")
    print(f"\nCoM (trunk frame): x={com[0]*1000:+.1f}  y={com[1]*1000:+.1f}  z={com[2]*1000:+.1f} mm")
    print(f"Inertia diag (kg.m^2): {np.diag(I)}")
    off = np.array([I[0,1], I[0,2], I[1,2]])
    print(f"Off-diagonal         : {off}")
    from collections import Counter
    c = Counter(x[3] for x in COMPONENTS)
    gm = {k: sum(x[1] for x in COMPONENTS if x[3] == k) for k in c}
    print("\nmass by provenance:")
    for k in sorted(gm, key=lambda k: -gm[k]):
        print(f"  {k:10s} {gm[k]:6.1f} g  ({gm[k]/(total*1000)*100:.0f}%)  in {c[k]} items")


if __name__ == "__main__":
    report()

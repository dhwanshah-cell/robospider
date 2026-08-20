# CubeBot — simulation, CAD and analysis

12-DOF sprawled quadruped. Everything here is self-contained.

    sim/     the model — start here
    cad/     geometry, real and fake (read the warnings)
    docs/    derivations, handoff, fasteners
    tools/   the scripts that produced all of it
    data/    recorded takes and poses
    media/   gait and climb renders

## Quick start

    pip install mujoco
    cd sim && python view.py        # mjpython view.py on macOS
    python view.py --wiggle         # random policy across all 12 joints

`sim/cubebot.xml` is a MuJoCo model: primitive geoms only, **no mesh files
required**. `sim/cubebot.urdf` is the same robot for ROS/other tools.

| | |
|---|---|
| DOF | 12 (4 legs × yaw/pitch/knee) + free base |
| mass | **751.7 g** (±~120 g — see caveats) |
| stand height | 100 mm on four feet |
| timestep | 2 ms, `implicitfast` (MJX-compatible) |
| sensors | trunk framequat / gyro / accel / velocimeter + 4 foot touch |

Geometry: femur 48.00 mm, tibia 78.82 mm, reach 126.82 mm, foot ball r 8.5 mm.
Leg splay **FL +23.83° FR −23.83° BL +106.23° BR −106.23°** — the rear pair is
*not* a mirror of the front. Getting this wrong silently breaks every angle.

## Servos (4.8 V ratings)

| joint | servo | stall | speed |
|---|---|---|---|
| yaw | TowerPro SG90 | 1.8 kg·cm (0.1765 N·m) | 0.10 s/60° |
| pitch, knee | TowerPro SG92R | 2.5 kg·cm (0.2452 N·m) | 0.10 s/60° |

Position actuators with `kp = stall/8°`, `kv = stall/no-load-speed`, forcerange
clamped at stall — a joint asked for more than the servo can give will **lag**,
not magically deliver it.

Validated over standing, squatting, ±16° pitch, ±14° roll, all four tripod
stances, walking at 0.8 and 1.0 Hz, and a 144 mm wall-climb pose:

| joint | worst | RMS | saturated |
|---|---|---|---|
| yaw | 74–84% | 14% | **0** |
| pitch | 80–87% | 31% | **0** |
| knee | 64–74% | 12% | **0** |

Walk at **1.0 Hz, not 0.8** — load is static-hold dominated, so slower means
longer under load, not gentler.

## Caveats, stated plainly

**Mass carries ~±120 g of uncertainty.** Derived from CAD volumes plus
datasheet component masses; **nothing has been weighed**. The parts total
suggests it could reach ~875 g, which would put the pitch joint near its limit.

**Trunk component positions are an assumed layout**, not from CAD. The mass
model is real — 30 components parallel-axis'd, CoM 11.5 mm below the case
centre because the 18650s sit low — but where each item sits is a sensible guess.

**The URDF has no floating base.** Standard for URDF: the root link welds to the
world, so a loader will report only the leg mass until you add a free-flyer
joint. The MJCF has a proper free joint.

**`cad/stl-collision-proxies/` contains three files that are not real parts**
and an original URDF whose masses sum to 1.06 g. Both folders carry warning
files. Print from `cad/stl-real/`.

# CubeBot RL — HANDOFF

**Read this first**, then `docs/LEG_TORQUE_MATH.md`. Goal: a learned locomotion
policy, per `~/Downloads/TEMP/quadruped-rl-locomotion-plan.pdf`.

## Status

| | |
|---|---|
| **Servo config** | **SG90 yaw / SG92R pitch / SG92R knee** — validated, nothing saturates |
| **Robot mass** | **~750–875 g** — uncertain, see below |
| **Real CAD** | arrived from tnkr.ai; the old URDF meshes were partly fake |
| **RL** | Phase 0 local half done. Colab/MJX half NOT run. |

## THE BIG CORRECTION — the old meshes were not the robot

Everything before the tnkr.ai export used `cad/CubeBot_RL/.../meshes/*.stl`,
which are **URDF collision proxies**, not parts:

* `Bottom_case.stl` — 99% of its bounding box, a **solid slab**
* `Leg_middle_part.stl` — 99%, **solid slab**
* `Top_case.stl` — **12 triangles**, a bare cuboid
* and **12 servo casings + camera cover were missing entirely**

Real geometry is in `~/Downloads/TEMP/CAD/bom-export-20260819T105659/stl-files/`.
`Top_Case_HD.stl` turned out to be the **Body Frame** (volumes match to 0.024%)
and our copy is *higher* resolution than the export — keep it.

Consequence: **chassis 213 g (modelled) -> ~396 g (real), 1.86x.**
Robot 690 g -> **750–875 g**, depending on print fill. My rebuilt model landed
at 752 g but the parts total implies ~873 g; the parameter edits did not fully
propagate. **Weigh a printed Servo Casing 1 (predicted ~9.3 g) to settle it.**

## Servo decision — settled

Loads re-validated at the corrected mass, worst case anywhere:

| joint | servo | worst | RMS | saturated |
|---|---|---|---|---|
| yaw | SG90 1.8 kg·cm | 74–84% | 14% | **0** |
| pitch | SG92R 2.5 kg·cm | 80–87% | 31% | **0** |
| knee | SG92R 2.5 kg·cm | 64–74% | 12% | **0** |

**Run the gait at 1.0 Hz, not 0.8** — faster *and* lower load (static hold
dominates, so going slower just means longer under load).

* **MG996R does not fit.** 19.7 mm smallest dimension vs a 15.0 mm hip bracket
  and 15.5 mm femur. Micro format is a hard CAD constraint.
* **MG92B (3.1 kg·cm) is the ideal part but is unobtainable in India.**
* **SG92R is the substitute** — same 0.10 s/60° speed as SG90, +39% torque,
  9 g, ~Rs 152 at Robu. POM/carbon gears, not metal: buy spares for the knees.
* **Watch for SG92R counterfeits.** Genuine = 4 screws in the base and
  "TowerPro" moulded into the plastic. A relabelled SG90 puts you back at
  1.8 kg·cm, which FAILS the climb (116% of stall).

Walking loads the shoulder; climbing loads the knee. Sizing for one leaves you
short on the other.

## Tooling

    scripts/sim_joints.py    physics sim + IPC   (mjpython)
    scripts/joint_panel.py   control window      (python3, tkinter)

Two processes because macOS will not share a main thread between tkinter and
the MuJoCo viewer; they talk through `cmd.json` / `state.json` in the scratchpad.

    mjpython scripts/sim_joints.py --wall 0.1442 --from-pose pose_current.json \
             --yaw SG90 --pitch SG92R --knee SG92R --strip-factor 3.5
    python3 scripts/joint_panel.py

Panel: per-joint −/+ at a set deg/s, multi-select, LINK groups with per-member
sign, leg locks (shin-angle / foot-height, both exact closed forms), a d-pad
driving the crawl gait, and continuous recording with idle frames dropped
(~78% of a raw take is the robot standing still).

**Gear strip model**: a servo cannot strip its own gears by driving — the motor
tops out at stall. Failure is external back-drive. Proxy is
`|qfrc_actuator + qfrc_constraint|` vs `strip_factor × stall`. **`--strip-factor`
is a dial, not a measurement** (nylon ~2–3x, POM/carbon ~3–4x, metal 5x+), and
it models overload only, not fatigue. Peaks of 3.09x have been seen in posing.

## Printing (Creality K1C, 0.4 nozzle, Elegoo PLA+ 1.23 g/cm³)

Whole robot ~3.2 h of extrusion across **6 plates**, ~3.5–4 h with supports.

* **Layer 0.24** for casings/covers (0.16 -> 0.24 cuts layer count 33%)
* **Layer 0.20, 5 walls, 25% infill for the Leg and Leg-Body Connector.**
  In bending, walls carry the load and infill sits at the neutral axis:
  3->5 walls buys 21% stiffness, 15%->40% infill buys 4%.
* PLA+ is 39 MPa XY but **28 MPa Z** — orient the Leg so bending does not load
  the layer interface.
* Supports **on** globally (every part has 4–14% overhang), **"on build plate
  only"** ticked so it does not fill the 78 screw holes.

## Fasteners — you have already bought the BOM set

| size | owned | needed | **buy** |
|---|---|---|---|
| M2 | 46 (32×8, 10×10, 4×15) | 58 | **+12 × M2×8** |
| M3 | 4 (M3×10) | 15 | **+12 × M3×10, +6 × M3×6** |
| M4 | 0 | 16? | **verify first** |

M3 was under-ordered ~4x. The 3 × Ø3.1 pilots are only 3 mm deep, so a 10 mm
screw bottoms out — hence the M3×6.

**M4 is unresolved.** 16 holes of Ø4.0–4.8 sit next to Ø7.5 bores on the Leg and
Leg-Body Connector — that is the hip pivot, so they are more likely **pins or
shoulder bolts than screws**. Check whether the Ø4.8 runs clean through before
ordering. Total extra ~Rs 150–250.

There are **no nut traps anywhere**: every screw self-taps into plastic.

## Still open

1. **Weigh a printed part** — the last real uncertainty in the mass model.
2. **Resolve the M4 holes** — pins or screws.
3. **Phase 0 Colab/MJX half** — `notebooks/phase0_colab.ipynb`, never run.
4. **Phase 1 actuator characterisation** — the phase that decides whether any
   policy transfers. Bench one servo, fit a rate-limited model with 30–80 ms
   latency.
5. `legstudy/stairs.py` is **unvalidated and disagrees with everything** —
   delete or fix it.

## Leg statics — read `docs/LEG_TORQUE_MATH.md`

The equations behind every torque number here, with their validation:
knee torque = GRF x tibia x sin(shin angle) (correlation 0.998 against a
recorded take), the opposing pitch/knee moment-arm tradeoff and its optimum,
the exact FK used by the leg locks, the foot-radius convention that inflated
every early walking load, and the gear-strip model.

## Servo configuration — MIXED, and this is the committed choice

**All ratings are the 4.8 V column. Always.** (`electrical.supply_voltage_v: 4.8`.)

| joint | x4 | servo | gear | worst demand | % of stall | verdict |
|---|---|---|---|---|---|---|
| shoulder yaw | 4 | **SG90** 9 g | plastic | 0.0596 N.m | 33.8% | comfortable |
| shoulder pitch | 4 | **MG996R** 55 g | metal | 0.2019 N.m | **21.9%** | comfortable |
| knee | 4 | **MG90S** 13.4 g | metal | 0.0764 N.m | **43.3%** | OK — tightest joint |

Robot **0.892 kg**. Servos are 310 g, 35% of the machine. All-stall draw
10.6 A against 12 A of UBEC. Reproduce with `scripts/servo_audit.py`.

**Why not all-MG90S:** at 4.8 V the pitch joint needs 114% of MG90S stall — it
does not run hot, it *stalls*. That is what forces the mixed build.

**Cost is a wash.** ~INR 2,760 for twelve either way: what the SG90s save on
yaw pays for the MG996Rs on pitch. Same money, works instead of stalling.

**Do not put SG90 on the knee.** It is torque-identical to MG90S (both 1.8
kg.cm @ 4.8 V) and would save 18 g plus 11% of shoulder-pitch swing inertia,
but the knee is where footfall impact lands and plastic gears strip there. The
43.3% figure is also the tightest in the build. Metal, and keep spares.

**Speed is now the binding constraint, not torque.**

| joint | no-load | needed per Hz of gait | max gait |
|---|---|---|---|
| yaw SG90 | 10.47 rad/s | 1.94 | 3.78 Hz |
| **pitch MG996R** | **6.16 rad/s** | **4.71** | **0.92 Hz** |
| knee MG90S | 10.47 rad/s | 5.56 | 1.32 Hz |

Gait caps at **0.92 Hz = 6.4 cm/s** at the leg study's 70 mm step, set by the
MG996R. That is the price of the torque. Note the speed demand comes from that
assumed step profile — a Phase 2 policy that learns shorter, quicker steps
raises the ceiling proportionally, so treat 0.92 Hz as a limit on that profile,
not on locomotion.

If a mini digital servo turns up at >=5 kg.cm and <=0.12 s/60deg @ 4.8 V, it
beats the MG996R on every axis: half the mass, twice the gait speed, still 3x
the torque needed. Worth a look before the bracket is reprinted.

**Bracket:** MG996R is 40.7 x 19.7 x 42.9 mm against a 46 x 15 x 40 mm
`Part_1`. Reprint required (accepted). SG90 is a drop-in for MG90S.

## Known issue that will bite in Phase 4

At 0.743 kg the **squat manoeuvre already needs ~93% of MG90S stall torque**
(0.201 N.m of 0.216 N.m), and MG90S's 4.8 V rating is 0.176 N.m — at which the
same move *stalls*. The stance load is dominated by ground reaction, which is
14x the leg's self-weight, so lighter servos cannot fix it. Either the reward
must penalize deep squats, or the femur gets shorter, or the servo gets bigger.
This is the single most likely reason a trained policy fails on hardware.

## Next

**Phase 1 is the one that decides whether any of this transfers.** Bench-test
one MG90S (step response, max speed under load, deadband, stall), fit a
rate-limited position-tracking model with 30-80 ms latency, and implement it as
the sim actuator. A policy trained on ideal position servos will not walk on
real MG90S hardware. Deliverable: sim servo trace overlays bench trace within ~10%.

## Layout

    assets/cubebot_12dof.xml        generated MJX-ready model
    cubebot_rl/export_mjcf.py       generator (reads leg-study params.yaml)
    scripts/phase0_random_policy.py Phase 0 M1c local check
    notebooks/phase0_colab.ipynb    Phase 0 M1a/M1b/M1c on Colab + MJX GPU

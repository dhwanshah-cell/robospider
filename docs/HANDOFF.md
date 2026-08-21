# CubeBot — HANDOFF

**Read this first**, then `docs/LEG_TORQUE_MATH.md` for the derivations.
Repo: https://github.com/dhwanshah-cell/robospider (public)

---

## WHERE THINGS STAND — 21 Aug 2026

**All parts are printed. Assembly day. Demo is Saturday 22 Aug.**

| | |
|---|---|
| servos | **SG90 / MG90S class (1.8 kg·cm @4.8 V) on all 12** — what is in hand |
| robot mass | **~735 g — MEASURED, no longer an estimate** |
| sim validated at | 751.7 g (at/above real, so slightly conservative) |
| gait for the demo | **1.0 Hz, 55 mm step, +10 mm stance height** -> ~4 cm/s |
| blocker | **11 x M3 screws short** (see Fasteners) |

### The mass question is CLOSED
Printed parts weighed **~300 g including support**; backing out ~15% support gives
~255 g of parts and a **~735 g robot**. My earlier model assumed 0.85 effective
fill and predicted 397 g of parts / 873 g robot — **that was wrong**. Real fill is
**~0.55**, because 15% infill on thin-walled parts is far lighter than I credited.

The feared 873 g case (which would have put the pitch servos at their limit)
**does not happen**. Conversion for anything printed later at these settings:
**~0.67 g per cm³ of part volume**.

---

## SERVOS — decided and validated

Demo runs on the **SG90/MG90S** set already owned. Validated across standing,
squatting, ±16° body pitch, ±14° roll, all four tripod stances, walking at 0.8
and 1.0 Hz, and a 144 mm wall-climb pose:

| joint | worst | RMS | saturated |
|---|---|---|---|
| yaw | 74–84% | 14% | **0** |
| pitch | 80–87% | 31% | **0** |
| knee | 64–74% | 12% | **0** |

Nothing saturates. Margin on the shoulders is thin but real.

**Upgrade path, if climbing ever matters:** the knee needs **0.205 N·m** with a
foot loaded on a 144 mm wall, which an MG90S (1.8 kg·cm) **cannot** deliver —
116% of stall. **SG92R (2.5 kg·cm, ~Rs 152 at Robu, 9 g, same 0.10 s/60° speed)**
clears it at 84% and is the only in-stock micro-format part that does. MG92B
(3.1) would be ideal but is unobtainable in India.

**MG996R does not fit.** 19.7 mm smallest dimension against a **15.0 mm hip
bracket and 15.5 mm femur**. Micro format is a hard CAD constraint, not a
preference. Fitting one to the knee also roughly doubles shoulder swing inertia.

**Counterfeit warning:** genuine TowerPro has **4 screws in the base** and
"TowerPro" **moulded into the plastic**. A relabelled SG90 sold as SG92R puts you
straight back to 1.8 kg·cm.

---

## FOUR RESULTS THAT ARE COUNTER-INTUITIVE

Do not re-derive these; they are measured and documented.

1. **Walking loads the shoulder; climbing loads the knee.** Sizing for one leaves
   you short on the other.
2. **Slower is worse.** Shoulder load is static-hold dominated, so 0.8 Hz has
   *higher* RMS torque than 1.0 Hz and covers less ground. **Never slow the gait
   down to help it.**
3. **Stand tall, never crouch.** +10 mm stance is the single biggest load
   reduction; crouching 12 mm pushes pitch to 100% and it starts saturating.
4. **Walls beat infill for the leg.** In bending, stress is at the outer fibres
   and infill sits at the neutral axis: 3->5 perimeters buys 21% stiffness,
   15%->40% infill buys 4%.

---

## FASTENERS — there is a live shortfall

Measured from the real STLs. **No nut traps anywhere** — every screw self-taps
into plastic, so pilot count = screw count: **58 M2, 15 M3**.

| size | bought | needed | **buy** |
|---|---|---|---|
| M2 | 46 (32×8, 10×10, 4×15) | 58 | **+12 × M2×8** |
| M3 | **4** (M3×10) | **15** | **+12 × M3×10, +6 × M3×6** |
| M4 | 0 | 16? | **verify first** |

**M3×6 is not a spare** — three Body Frame pilots are the Ø3.1 stepped holes at
only **3 mm deep**; a 10 mm screw bottoms out.

**M4 unresolved.** 16 × Ø4.0–4.8 holes sit beside Ø7.5 bores on the Leg and
Leg-Body Connector — that is the hip pivot, so they are more likely **pins or
shoulder bolts than screws**. Check whether the Ø4.8 runs clean through.

---

## ASSEMBLY FACTS THAT BITE

**Leg mount angles are NOT mirrored front-to-rear:**

    FL  +23.83°     FR  -23.83°
    BL +106.23°     BR -106.23°

**All six leg parts are mirror-symmetric** (verified against a sampling noise
floor) — the four legs are **identical**, no left/right handing. Handedness comes
from the mount angles only.

**Zero-pose convention:** `ctrl = 0` means **femur HORIZONTAL, tibia VERTICAL**.
Neutral stance = body **103 mm** up, feet at **(±99.5, ±99.1) mm** — a near-square
199 × 198 mm footprint. If the footprint is not square and ~200 mm, a leg is
mounted wrong.

**Joint limits:** yaw ±91.7°, pitch ±80.2°, knee ±126.1°.

**Centre every servo BEFORE assembly** and mark the spline. A horn fitted
off-centre gives a joint whose range is wrong in a way that stays invisible until
the robot walks sideways.

**Power:** stagger servo startup in **groups of 3, 100 ms apart**. Twelve servos
at once draws a surge the 7 A UBEC folds back on. The 2200 µF cap absorbs
switching transients but does **not** extend the current budget (it buys
sub-milliseconds). Keep the Pi rail separate.

---

## TOOLING

    scripts/sim_joints.py    physics sim + IPC        (needs mjpython)
    scripts/joint_panel.py   control window           (python3, tkinter)

Two processes because macOS will not share a main thread between tkinter and the
MuJoCo viewer; they talk through `cmd.json` / `state.json`.

    mjpython scripts/sim_joints.py --wall 0.1442 --from-pose pose_current.json \
             --yaw SG90 --pitch SG92R --knee SG92R --strip-factor 3.5
    python3 scripts/joint_panel.py

Panel has per-joint ±  at a set deg/s, multi-select, LINK groups with per-member
sign, leg locks (shin-angle / foot-height, exact closed forms), a d-pad driving
the crawl gait, and continuous recording with idle frames dropped (~78% of a raw
take is the robot standing still).

**Gear-strip model:** a servo cannot strip its own gears by driving — the motor
tops out at stall. Failure is external back-drive. Proxy is
`|qfrc_actuator + qfrc_constraint|` vs `strip_factor × stall`. **`--strip-factor`
is a dial, not a measurement** (nylon ~2–3×, POM/carbon ~3–4×, metal 5×+) and it
models overload only, **not fatigue**.

---

## THINGS THAT ARE WRONG AND SHOULD NOT BE TRUSTED

**`cad/CubeBot_RL/.../meshes/*.stl` are URDF collision proxies, not parts.**
`Bottom_case.stl` and `Leg_middle_part.stl` are **solid slabs** (99% of bbox);
`Top_case.stl` is a **12-triangle cuboid**. Stored in metres. The real geometry is
in `~/Downloads/TEMP/CAD/bom-export-20260819T105659/stl-files/` and in the repo
under `cad/stl-real/`. `Top_Case_HD.stl` IS real and is the **Body Frame**.

**The original URDF's masses are unit-density artifacts** — every `<mass>` equals
the mesh volume in m³; the whole robot sums to **1.06 g**. Use `sim/cubebot.urdf`
from the repo instead (real masses, no mesh deps). Note URDF has **no floating
base**: a loader reports only leg mass until you add a free-flyer joint.

**`legstudy/stairs.py` is unvalidated**, has never been run by `run.py`, and
disagrees with every independent check. Delete or fix it.

**My hand-scripted climb trajectories failed at every height** for trajectory
reasons, not physical ones. Kinematic playback with no physics let feet pass
through a wall (41/41 frames, 54 mm deep). **Any climb claim must survive a
forward-dynamics replay with contacts** before it means anything.

---

## OPEN ITEMS

1. **Resolve the M4 holes** — pins or screws. Blocks final assembly.
2. **Phase 0 Colab/MJX half** — `notebooks/phase0_colab.ipynb`, written, never run.
   Needs a GPU runtime.
3. **Phase 1 actuator characterisation** — the phase that decides whether any RL
   policy transfers. Bench one servo: step response, max speed under load,
   deadband, stall. Fit a rate-limited position model with 30–80 ms latency.
4. **Push the corrected mass to the repo** — README and this file still said
   "±120 g, nothing weighed" before today's measurement.
5. **Semi-SLAM with preloaded images** — on the project checklist, not started.

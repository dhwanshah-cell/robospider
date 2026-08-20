# CubeBot leg statics — the equations, and what they imply

Everything here is derived from the CAD geometry and **checked against the
simulator**, not quoted from a textbook. Where a number is measured, the
measurement is given. Where something is assumed, it says so.

## Geometry (from the CAD, exact)

| | |
|---|---|
| femur (pitch axis → knee axis) | **48.00 mm** |
| tibia (knee axis → foot centre) | **78.82 mm** |
| tibia lateral offset | 17.00 mm |
| yaw → pitch offset | (25.0, 17.0, 7.5) mm |
| hip mounts | (±46.5, ±38.5, −23.2) mm |
| leg splay (mount yaw) | FL +23.83°, FR −23.83°, **BL +106.23°, BR −106.23°** |
| foot ball radius | 8.5 mm |
| total leg reach | 126.82 mm |
| nominal stand height | 103.0 mm |

The rear splay is **±106°, not mirrored ±156°**. A naively mirrored rig will not
match the robot.

## 1. Knee torque

The ground reaction at the foot is essentially vertical. The knee's moment arm
is the **horizontal** distance from the knee axis to the foot, which is the
tibia projected onto the horizontal:

```
    tau_knee  =  F_grf  ×  L_tibia  ×  sin(phi)

    phi = shin angle from vertical
```

* `phi = 0` (shin vertical) → arm 0 → **zero knee torque**. The force runs
  straight down the tibia through the knee axis.
* `phi = 90°` (shin horizontal) → arm = full 78.82 mm → **maximum**.

**Validated** against a recorded take: correlation between `sin(phi)` and the
measured horizontal knee→foot arm = **0.998**. Over that take the arm ranged
**6.9 → 80.6 mm**, a 12× swing — which is why the same servo read 70% of stall
at one moment and over 100% at another. The servo did not change; the geometry did.

## 2. Shoulder-pitch torque

Same logic, one link further out:

```
    tau_pitch  =  F_grf  ×  d_horizontal(pitch axis → foot)
```

The femur is the lever. This is why the 48 mm femur length sets the whole
shoulder-torque budget, and why shortening it is the only geometric lever on
stance load. Measured: in stance the ground reaction is **14×** the leg's own
self-weight, so self-weight is only ~7.7% of the shoulder load — lighter servos
cannot fix a stance-torque problem.

## 3. The two joints pull in opposite directions

```
    knee  wants the shin VERTICAL           arm = L_tibia · sin(phi)      -> 0
    pitch wants the foot UNDER THE HIP      arm = hip-to-foot horizontal  -> 0
```

They cannot both be satisfied: the knee lies **between** the hip and the foot,
so tucking the foot under the hip tilts the shin, and standing the shin upright
pushes the foot outboard.

Swept at 100 mm body height, one leg carrying a tripod share (2.26 N, 690 g
robot), SG92R (2.5 kg·cm) at both joints:

| foot x | shin | pitch arm | knee arm | pitch | knee | worst |
|---|---|---|---|---|---|---|
| 20 mm | 168° | 12.8 mm | 18.9 mm | 12% | 17% | **17%** |
| 36 | 164° | 5.0 | 24.3 | 5% | 22% | 22% |
| 52 | 163° | **2.9** | 27.4 | **3%** | 25% | 25% |
| 68 | 167° | 12.5 | 25.0 | 12% | 23% | 23% |
| 84 | 173° | 24.2 | **17.4** | 22% | **16%** | 22% |

Minimising **either** joint alone makes the other worse (see the 52 mm row).

### The rule

> **Balance the two moment arms; do not minimise either.**
> Optimum in this sweep: foot ~20 mm ahead of the body origin, body ~85 mm,
> arms 12.8 vs 18.5 mm, worst joint **17%**.

Good candidate for a Phase 2 reward term: penalise `max(pitch_arm, knee_arm)`
and let the policy discover the tradeoff.

**Caveats.** Static arms only — swing adds inertial load this ignores. And it
ignores stability: a 20 mm footprint is a tiny support polygon, and the walking
sweep found foot spreads below ~70% of nominal unwalkable (the robot topples
before the load benefit arrives).

## 4. Forward kinematics (planar, exact)

Vertical drop from the pitch axis to the foot centre:

```
    drop  =  L_femur · sin(q_pitch)  +  L_tibia · cos(q_pitch + q_knee)
```

Verified against MuJoCo FK to 0.01 mm. Two useful consequences, both exactly
solvable (one constraint, one free joint), both implemented in `joint_panel.py`:

**Shin-angle lock** — hold the shin's angle to the ground while driving the femur:

```
    delta_q_knee  =  - delta_q_pitch
```

Exact: shin angle held at 0.00° across the full range.

**Foot-height lock** — hold the foot at a constant height while driving the femur:

```
    q_knee  =  arccos( (drop_target - L_femur · sin(q_pitch)) / L_tibia )  -  q_pitch
```

Verified: foot drop held at 78.82 mm for q_pitch 0→40°, knee values matching a
MuJoCo bisection to 0.01°.

**You cannot lock the foot's full 3D position while driving a joint.** The leg
has 3 DOF; pinning a 3D point consumes all three and leaves nothing to drive.

## 5. Convention gotcha that cost real time

`leg_ik` targets the foot **site**, which sits at the **centre of the foot ball**.
Placing a foot target at the surface height (`z = 0` for the floor, `z = H` for a
tread) buries the ball one radius — **8.5 mm** — into the ground.

```
    correct:   z_target = surface_height + foot_radius
```

The leg study's own standing height already assumes this:
`z0 = -(hip_z + foot_z - foot_radius) = 103.0 mm`.

Getting this wrong made the servos press into the floor for the whole stance
phase and inflated every walking load — yaw by 78%, knee by 12%.

## 6. Servo reference (4.8 V column, always)

| servo | stall | s/60° | mass | smallest dim | fits leg parts? |
|---|---|---|---|---|---|
| SG90 | 1.8 kg·cm (0.1765 N·m) | 0.10 | 9.0 g | 11.8 mm | yes |
| MG90S | 1.8 (0.1765) | 0.10 | 13.4 g | 12.2 mm | yes |
| SG92R | 2.5 (0.2452) | 0.10 | 9.0 g | 12.2 mm | yes |
| MG92B | 3.1 (0.3040) | 0.10 | 13.8 g | 12.2 mm | yes (unobtainable in IN) |
| MG996R | 9.4 (0.9218) | 0.17 | 55.0 g | **19.7 mm** | **NO** |

**The hip bracket is 15.0 mm thick and the femur 15.5 mm.** The MG996R's 19.7 mm
smallest dimension does not fit either, in any orientation. Micro format is a
hard constraint of the current CAD, not a preference.

Emulated position servo (matches `params.yaml`):

```
    kp = stall / proportional_band      band = 8° = 0.1396 rad
    kv = stall / no_load_speed
    tau = clamp( kp·(cmd - q) - kv·qdot , ±stall )
```

Speed demand of the swing profile, per Hz of gait:
`yaw 1.94, pitch 4.71, knee 5.56 rad/s`. Usable ceiling ≈ 70% of no-load.

## 7. Gear stripping

A servo **cannot strip its own gears by driving** — the motor tops out at stall
and the train is built for that. Gears fail when something **external
back-drives** the output (a fall, a landing, a jammed leg) and the train must
react a torque far above stall. Stress proxy used in `sim_joints.py`:

```
    tau_gear  =  | qfrc_actuator + qfrc_constraint |     (per joint DOF)
    stripped  when  tau_gear > strip_factor × stall
```

`--strip-factor` is a **dial, not a measurement** — no trustworthy published
strip torque was found for these servos. Rough bands: nylon 2–3×, POM/carbon
3–4×, metal 5×+. Models overload failure only; **does not model fatigue**, which
is the other way POM gears die when run at 80% of stall for hours.

## 8. Measured loads, for reference

| case | binding joint | note |
|---|---|---|
| walking, all-SG90, 690 g | pitch 84% pk / 43% RMS | knee comfortable |
| walking, all-MG92B, 748 g | pitch 63% pk / 28% RMS | best build tested |
| wall climb, foot on 144 mm tread | **knee 0.205 N·m** | MG90S 116% (fails), SG92R 84%, MG92B 67% |
| yaw, every case tested | ≤68% pk, 5–27% RMS | SG90 is correctly sized |

**Walking loads the shoulder; climbing loads the knee.** Sizing for one leaves
you short on the other.

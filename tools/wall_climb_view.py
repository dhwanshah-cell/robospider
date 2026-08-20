#!/usr/bin/env python3
"""Interactive viewer: climbing a wall as tall as the robot (144 mm).

Kinematic playback between four poses, each certified by the statics solver
(reachable, inside joint limits, statically stable, every joint inside its own
servo limit). Phase C is the one that only became possible once the body was
allowed to stand up to 171 mm AND the supporting rear foot was freed to walk to
the wall base instead of being pinned at its neutral spot.

    mjpython scripts/wall_climb_view.py
"""
from __future__ import annotations
import sys, math, time
from pathlib import Path
import os, tempfile

def _runtime():
    p = Path(os.environ.get("CUBEBOT_RUNTIME", Path(tempfile.gettempdir())/"cubebot"))
    p.mkdir(parents=True, exist_ok=True)
    return p
import numpy as np

LEGSTUDY = Path.home() / "cubebot-legstudy"
sys.path.insert(0, str(LEGSTUDY)); sys.path.insert(0, str(Path.home() / "cubebot-rl"))
import mujoco
from legstudy.config import LegModel, Params
from legstudy import robot as rbt
from cubebot_rl.export_mjcf import retune

LEGS, JOINTS = rbt.LEGS, ("yaw", "pitch", "knee")
KGCM = 0.0980665
STALL = {"yaw": 1.8*KGCM, "pitch": 9.4*KGCM, "knee": 1.8*KGCM}
H, EDGE = 0.1442, 0.105


def main():
    from mujoco import viewer as mjv
    if sys.platform == "darwin" and getattr(mjv, "_MJPYTHON", None) is None:
        sys.exit("macOS: launch with mjpython, not python")

    p = Params(LEGSTUDY / "params.yaml")
    base = LegModel(p.variant_names[0], p)
    xml = retune(rbt.build_robot_mjcf(base, step_height=H, step_x=EDGE,
                                      with_stair=True, actuators="position",
                                      free_base=True))
    path = Path(str(Path(os.environ.get("CUBEBOT_RUNTIME", Path(tempfile.gettempdir())/"cubebot")))+"/wallview.xml")
    path.write_text(xml)
    r = rbt.Robot(path, base); m, d = r.m, r.d
    nf = rbt.neutral_footholds(base); R = base.foot_radius

    gnd = {lg: np.array([nf[lg][0], nf[lg][1], R]) for lg in LEGS}
    top = lambda x, lg, dz=0.0: np.array([x, nf[lg][1], H + R + dz])

    SEQ = [
        ({**gnd}, list(LEGS), rbt.BodyPose(x=0.010, z=0.105, pitch=math.radians(5)),
         "A  approach"),
        ({"FL": top(0.150,"FL"), "FR": top(0.150,"FR"),
          "BL": gnd["BL"], "BR": gnd["BR"]},
         list(LEGS), rbt.BodyPose(x=0.020, z=0.125, pitch=math.radians(-15)),
         "B  front feet on the wall"),
        ({"FL": top(0.125,"FL"), "FR": top(0.125,"FR"),
          "BL": top(0.110,"BL",0.012), "BR": np.array([-0.028, nf["BR"][1], R])},
         ["FL","FR","BR"], rbt.BodyPose(x=0.055, z=0.171, pitch=math.radians(-28)),
         "C  rear leg up (body raised to 171 mm)"),
        ({lg: top(EDGE + (0.045 if lg in ("FL","FR") else 0.005), lg) for lg in LEGS},
         list(LEGS), rbt.BodyPose(x=0.130, z=H+0.055, pitch=math.radians(5)),
         "D  all four on top"),
    ]

    keys = []
    print(f"wall {H*1000:.0f} mm (= the robot's own height), "
          f"leg reach {(base.femur_length+base.tibia_length)*1000:.1f} mm\n")
    for feet, sup, pose, lab in SEQ:
        q = {lg: r.leg_ik(pose, lg, feet[lg]) for lg in LEGS}
        sol = r.solve_loads(pose, q, sup)
        use = {j: max(abs(sol["tau"][lg][k]) for lg in LEGS)/STALL[j]
               for k, j in enumerate(JOINTS)}
        print(f"  {lab:40s} " + "  ".join(f"{j}={use[j]*100:3.0f}%" for j in JOINTS))
        keys.append((lab, pose, q))

    print("\nPlayback loops A -> B -> C -> D -> A.")
    print("Mouse: drag orbit, scroll zoom. Close the window to quit.")
    with mjv.launch_passive(m, d) as v:
        v.cam.distance, v.cam.azimuth, v.cam.elevation = 0.62, 90, -6
        v.cam.lookat[:] = [EDGE - 0.01, 0.0, H * 0.55]
        SEG, HOLD = 2.4, 1.2
        t0 = time.time()
        while v.is_running():
            t = (time.time() - t0) % (len(keys) * (SEG + HOLD))
            idx = int(t // (SEG + HOLD))
            local = t - idx * (SEG + HOLD)
            a = min(1.0, local / SEG)
            s = 0.5 - 0.5 * math.cos(math.pi * a)
            _, p0, q0 = keys[idx]
            _, p1, q1 = keys[(idx + 1) % len(keys)]
            pose = rbt.BodyPose(x=p0.x + (p1.x - p0.x) * s,
                                z=p0.z + (p1.z - p0.z) * s,
                                pitch=p0.pitch + (p1.pitch - p0.pitch) * s)
            q = {lg: q0[lg] + (q1[lg] - q0[lg]) * s for lg in LEGS}
            r.set_state(pose, q)
            v.cam.lookat[0] = float(d.qpos[0]) * 0.5 + (EDGE - 0.01) * 0.5
            v.sync()
            time.sleep(1/60)


if __name__ == "__main__":
    main()

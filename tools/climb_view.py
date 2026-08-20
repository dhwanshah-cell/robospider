#!/usr/bin/env python3
"""Interactive viewer for the stair climb.

KINEMATIC PLAYBACK, not a dynamic climb -- and deliberately so. Each keyframe
is a pose the statics solver has certified: reachable, inside joint limits,
statically stable, and within every joint's own servo limit. Playback walks
between those certified poses so you can see the geometry of the climb without
a hand-authored trajectory (mine failed) standing in the way.

    mjpython scripts/climb_view.py            # 70 mm -- the tallest it can climb
    mjpython scripts/climb_view.py 0.1442     # bot height -- stalls at phase B

Phase C is omitted automatically when no feasible pose exists, which is exactly
what happens at bot height: the robot reaches phase B and has nowhere to go.
"""
from __future__ import annotations
import json, sys, math, time
from pathlib import Path
import os, tempfile

def _runtime():
    p = Path(os.environ.get("CUBEBOT_RUNTIME", Path(tempfile.gettempdir())/"cubebot"))
    p.mkdir(parents=True, exist_ok=True)
    return p
import numpy as np

LEGSTUDY = Path.home() / "cubebot-legstudy"
sys.path.insert(0, str(LEGSTUDY))
sys.path.insert(0, str(Path.home() / "cubebot-rl"))
import mujoco
from legstudy.config import LegModel, Params
from legstudy import robot as rbt
from cubebot_rl.export_mjcf import retune

LEGS, JOINTS = rbt.LEGS, ("yaw", "pitch", "knee")
FRONT, REAR = ["FL", "FR"], ["BL", "BR"]
KGCM = 0.0980665
STALL = {"yaw": 1.8*KGCM, "pitch": 9.4*KGCM, "knee": 1.8*KGCM}

H    = float(sys.argv[1]) if len(sys.argv) > 1 else 0.070
EDGE = float(sys.argv[2]) if len(sys.argv) > 2 else 0.105


def main():
    from mujoco import viewer as mjv
    if sys.platform == "darwin" and getattr(mjv, "_MJPYTHON", None) is None:
        sys.exit("macOS: launch with mjpython, not python")

    p = Params(LEGSTUDY / "params.yaml")
    base = LegModel(p.variant_names[0], p)
    xml = retune(rbt.build_robot_mjcf(base, step_height=H, step_x=EDGE,
                                      with_stair=True, actuators="position",
                                      free_base=True))
    path = Path(str(Path(os.environ.get("CUBEBOT_RUNTIME", Path(tempfile.gettempdir())/"cubebot")))+"/climbview.xml")
    path.write_text(xml)
    r = rbt.Robot(path, base)
    m, d = r.m, r.d
    nf = rbt.neutral_footholds(base)
    hip = base.p["kinematics.hip_mount_xyz"]
    _, _, fz = base.neutral_foot_position()

    R = base.foot_radius     # leg_ik targets the ball CENTRE
    ground = {lg: np.array([nf[lg][0], nf[lg][1], R]) for lg in LEGS}
    onstep = {lg: np.array([EDGE + 0.045, nf[lg][1], H + R]) for lg in LEGS}
    PH = [
        ("A  approach", {**ground}, list(LEGS)),
        ("B  front feet up", {**{l: onstep[l] for l in FRONT},
                              **{l: ground[l] for l in REAR}}, list(LEGS)),
        ("C  rear leg up", {**{l: onstep[l] for l in FRONT},
                            "BL": np.array([EDGE+0.01, nf["BL"][1], H+R+0.015]),
                            "BR": ground["BR"]}, ["FL", "FR", "BR"]),
        ("D  all on top", {lg: np.array([EDGE + (0.045 if lg in FRONT else 0.005),
                                         nf[lg][1], H+R]) for lg in LEGS}, list(LEGS)),
    ]

    def search(feet, support):
        best = None
        for bx in np.arange(-0.05, EDGE + 0.16, 0.01):
            for bz in np.arange(0.055, 0.085 + H, 0.005):
                for pit in np.radians(np.arange(-35, 40, 5)):
                    pose = rbt.BodyPose(x=bx, z=bz, pitch=pit)
                    try:
                        q = {lg: r.leg_ik(pose, lg, feet[lg]) for lg in LEGS}
                    except ValueError:
                        continue
                    if r.joint_limit_margin(q) < 0:
                        continue
                    sol = r.solve_loads(pose, q, support)
                    if sol is None:
                        continue
                    use = {j: max(abs(sol["tau"][lg][k]) for lg in LEGS)/STALL[j]
                           for k, j in enumerate(JOINTS)}
                    sc = (0 if sol["feasible"] else 10) + max(use.values())
                    if best is None or sc < best[0]:
                        best = (sc, pose, q, use)
        return best

    print(f"step {H*1000:.0f} mm, edge x={EDGE*1000:.0f} mm, "
          f"leg reach {(base.femur_length+base.tibia_length)*1000:.0f} mm")

    # the pose search is ~11k statics solves per phase; cache it so the window
    # opens immediately on a re-run
    cache = Path(fstr(Path(os.environ.get("CUBEBOT_RUNTIME", Path(tempfile.gettempdir())/"cubebot")))+"/poses_{int(H*1000)}_{int(EDGE*1000)}.json")
    if cache.exists():
        raw = json.loads(cache.read_text())
        keys = [(k["name"], rbt.BodyPose(x=k["x"], z=k["z"], pitch=k["pitch"]),
                 {lg: np.array(k["q"][lg]) for lg in LEGS}) for k in raw["keys"]]
        blocked = raw["blocked"]
        for k in raw["keys"]:
            print(f"  {k['name']:18s} (cached)")
        if blocked:
            print(f"  {blocked:18s} NO FEASIBLE POSE -- the climb is blocked here")
        _run(m, d, r, keys, blocked, H, EDGE)
        return
    keys, blocked = [], None
    for name, feet, sup in PH:
        b = search(feet, sup)
        if b is None:
            print(f"  {name:18s} NO FEASIBLE POSE -- the climb is blocked here")
            blocked = name
            break                     # do NOT skip ahead: that would fake a climb
        _, pose, q, use = b
        print(f"  {name:18s} " + " ".join(f"{j}={use[j]*100:3.0f}%" for j in JOINTS))
        keys.append((name, pose, q))
    if len(keys) < 2:
        sys.exit("not enough feasible poses to animate")
    if blocked:
        print(f"\n  *** BLOCKED at '{blocked}'. Playback runs A -> {keys[-1][0].split()[0]} and\n"
              f"      reverses: the robot reaches as far as it physically can, then backs off.\n"
              f"      It never gets on top, because there is no pose that lets it. ***")

    cache.write_text(json.dumps({
        "blocked": blocked,
        "keys": [{"name": n, "x": p.x, "z": p.z, "pitch": p.pitch,
                  "q": {lg: list(map(float, q[lg])) for lg in LEGS}}
                 for n, p, q in keys]}))
    _run(m, d, r, keys, blocked, H, EDGE)


def _run(m, d, r, keys, blocked, H, EDGE):
    from mujoco import viewer as mjv
    import numpy as np
    print("\nMouse: drag orbit, scroll zoom. Close the window to quit.")
    with mjv.launch_passive(m, d) as v:
        v.cam.distance, v.cam.azimuth, v.cam.elevation = 0.55, 90, -8
        v.cam.lookat[:] = [EDGE - 0.02, 0.0, H * 0.5 + 0.04]
        SEG = 2.2          # seconds per keyframe transition
        HOLD = 1.0
        t0 = time.time()
        while v.is_running():
            order = (list(range(len(keys))) + list(range(len(keys) - 2, 0, -1))
                     if blocked else list(range(len(keys))))
            t = (time.time() - t0) % (len(order) * (SEG + HOLD))
            k = int(t // (SEG + HOLD))
            local = t - k * (SEG + HOLD)
            a = min(1.0, local / SEG)
            s = 0.5 - 0.5 * math.cos(math.pi * a)
            idx = order[k]
            nxt = order[(k + 1) % len(order)]
            n0, p0, q0 = keys[idx]
            n1, p1, q1 = keys[nxt]
            pose = rbt.BodyPose(x=p0.x + (p1.x - p0.x) * s,
                                z=p0.z + (p1.z - p0.z) * s,
                                pitch=p0.pitch + (p1.pitch - p0.pitch) * s)
            q = {lg: q0[lg] + (q1[lg] - q0[lg]) * s for lg in LEGS}
            r.set_state(pose, q)
            v.cam.lookat[0] = float(d.qpos[0]) + 0.04
            v.sync()
            time.sleep(1 / 60)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Replay a recorded take with DIFFERENT servos and watch what changes.

The take stores the commanded joint angles (ctrl) frame by frame. Feeding those
same commands to a robot fitted with different servos re-runs the physics: the
motion will NOT be identical, because the servos and the mass are different --
that divergence IS the result.

    mjpython scripts/replay_take.py --servo MG92B
    mjpython scripts/replay_take.py --servo MG90S     # the original, for contrast

Torque and saturation are printed live per joint type.
"""
from __future__ import annotations
import argparse, json, glob, math, os, sys, time
from pathlib import Path
import os, tempfile

def _runtime():
    p = Path(os.environ.get("CUBEBOT_RUNTIME", Path(tempfile.gettempdir())/"cubebot"))
    p.mkdir(parents=True, exist_ok=True)
    return p
import numpy as np

LEG = Path.home() / "cubebot-legstudy"
sys.path.insert(0, str(LEG)); sys.path.insert(0, str(Path.home() / "cubebot-rl"))
import mujoco
from legstudy.config import LegModel, Params
from legstudy import robot as rbt
from cubebot_rl.export_mjcf import retune
import cubebot_rl.mass_model as MM

KG = 0.0980665; BAND = math.radians(8.0)
LEGS, JN = rbt.LEGS, ("yaw", "pitch", "knee")
NAMES = [f"{l}_{j}" for l in LEGS for j in JN]
SP = Path(os.environ.get("CUBEBOT_RUNTIME", Path(tempfile.gettempdir())/"cubebot"))

# name -> (stall kg.cm @4.8V, s/60deg @4.8V, grams)
SERVO = {"MG90S": (1.8, 0.10, 13.4), "SG90": (1.8, 0.10, 9.0),
         "SG92R": (2.5, 0.10, 9.0),  "MG92B": (3.1, 0.10, 13.8),
         "MG996R": (9.4, 0.17, 55.0)}


def build(servo_g, wall):
    """params + MJCF with every joint carrying the same servo mass."""
    src = (LEG / "params.yaml").read_text()
    v = src.replace('    value: 0.055\n    source: spec\n    note: "The shoulder-PITCH servo is now an MG996R (55 g).',
                    f'    value: {servo_g/1000}\n    source: spec\n    note: "replay variant.')
    v = v.replace('{value: 0.0134, source: spec, note: "MG90S, 13.4 g."}',
                  f'{{value: {servo_g/1000}, source: spec, note: "replay variant."}}')
    v = v.replace('{value: 0.0134, source: spec, note: "Same MG90S as the baseline, just moved inboard."}',
                  f'{{value: {servo_g/1000}, source: spec, note: "replay variant."}}')
    pf = SP / f"replay_{servo_g}.yaml"; pf.write_text(v)
    base_c = list(MM.COMPONENTS)
    MM.COMPONENTS = [(n, servo_g if n.startswith("yaw_servo") else g, p, s, sz)
                     for (n, g, p, s, sz) in base_c]
    p = Params(pf); base = LegModel(p.variant_names[0], p)
    xml = retune(rbt.build_robot_mjcf(base, step_height=wall, step_x=0.105,
                                      with_stair=wall > 0, actuators="position",
                                      free_base=True))
    MM.COMPONENTS = base_c
    xf = SP / f"replay_{servo_g}.xml"; xf.write_text(xml)
    return xf, base


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--servo", default="MG92B", choices=list(SERVO))
    ap.add_argument("--take", default=None)
    ap.add_argument("--loop", action="store_true", default=True)
    a = ap.parse_args()
    from mujoco import viewer as mjv
    if sys.platform == "darwin" and getattr(mjv, "_MJPYTHON", None) is None:
        sys.exit("macOS: launch with mjpython")

    f = a.take or sorted(glob.glob(os.path.expanduser('~/cubebot-rl/results/take_*.json')),
                         key=os.path.getmtime)[-1]
    d0 = json.load(open(f)); F = d0["frames"]; DT = d0["dt"]; N = d0["joints"]
    kg, s60, gram = SERVO[a.servo]
    stall = kg * KG; noload = 1.047 / s60
    xf, base = build(gram, d0["wall_m"])
    m = mujoco.MjModel.from_xml_path(str(xf)); d = mujoco.MjData(m)
    aid = {n: m.actuator(f"act_{n}").id for n in NAMES}
    for n in NAMES:
        i = aid[n]; m.actuator_gainprm[i, 0] = stall / BAND
        m.actuator_biasprm[i, 1] = -stall / BAND; m.actuator_biasprm[i, 2] = -stall / noload
        m.actuator_forcerange[i] = [-stall, stall]

    C = np.array([fr["ctrl"] for fr in F]); Q = np.array([fr["qpos"] for fr in F])
    print(f"take {os.path.basename(f)}  {len(F)} frames, {len(F)*DT:.0f} s")
    print(f"servo: {a.servo}  {kg} kg.cm @4.8 V, {s60} s/60deg, {gram} g each")
    print(f"robot: {m.body_mass.sum()*1000:.0f} g   (recorded on the 892 g build)\n")
    print("the motion will diverge from the recording -- different servos, different physics.\n")

    with mjv.launch_passive(m, d) as v:
        v.cam.distance, v.cam.azimuth, v.cam.elevation = 0.62, 90, -8
        v.cam.lookat[:] = [0.09, 0.0, 0.09]
        while v.is_running():
            d.qpos[:] = Q[0]; d.qvel[:] = 0; mujoco.mj_forward(m, d)
            peak = {j: 0.0 for j in JN}; sat = {j: 0 for j in JN}; nfr = 0
            t0 = time.time()
            for k in range(len(F)):
                if not v.is_running():
                    break
                for n in NAMES:
                    d.ctrl[aid[n]] = float(C[k, N.index(n)])
                for _ in range(10):
                    mujoco.mj_step(m, d)
                nfr += 1
                for j in JN:
                    tq = max(abs(float(d.actuator_force[aid[f"{lg}_{j}"]])) for lg in LEGS)
                    peak[j] = max(peak[j], tq)
                    if tq >= stall * 0.999:
                        sat[j] += 1
                if k % 3 == 0:
                    v.cam.lookat[0] = float(d.qpos[0]) * 0.4 + 0.09 * 0.6
                    v.sync()
                    sys.stdout.write("\r  " + "  ".join(
                        f"{j}={peak[j]/stall*100:3.0f}%/{sat[j]/max(nfr,1)*100:4.1f}%sat" for j in JN)
                        + f"   z={d.qpos[2]*1000:5.1f}mm   frame {k}/{len(F)}   ")
                    sys.stdout.flush()
                lag = t0 + k * DT - time.time()
                if lag > 0:
                    time.sleep(lag)
            print(f"\n  pass done: " + "  ".join(
                f"{j} peak {peak[j]:.4f} N.m ({peak[j]/stall*100:.0f}%), "
                f"sat {sat[j]/max(nfr,1)*100:.1f}%" for j in JN))
            if not a.loop:
                break


if __name__ == "__main__":
    main()

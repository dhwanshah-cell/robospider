#!/usr/bin/env python3
"""Minimal standalone viewer for cubebot.xml. Only needs `pip install mujoco`.

    python view.py            # drop it on the floor and watch it stand
    mjpython view.py          # on macOS
    python view.py --wiggle   # random policy, proves all 12 joints actuate
"""
import argparse, sys, time
from pathlib import Path
import numpy as np, mujoco

XML = Path(__file__).with_name("cubebot.xml")
JOINTS = [f"{lg}_{j}" for lg in ("FL","FR","BL","BR") for j in ("yaw","pitch","knee")]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wiggle", action="store_true")
    a = ap.parse_args()
    from mujoco import viewer as mjv
    if sys.platform == "darwin" and getattr(mjv, "_MJPYTHON", None) is None:
        sys.exit("macOS: run with mjpython, not python")
    m = mujoco.MjModel.from_xml_path(str(XML)); d = mujoco.MjData(m)
    mujoco.mj_resetDataKeyframe(m, d, 0)
    aid = {n: m.actuator(f"act_{n}").id for n in JOINTS}
    print(f"{XML.name}: {m.body_mass.sum()*1000:.0f} g, nu={m.nu}, "
          f"{m.opt.timestep*1000:.0f} ms timestep")
    for j in ("yaw","pitch","knee"):
        i = aid[f"FL_{j}"]
        print(f"  {j:6s} forcerange ±{m.actuator_forcerange[i,1]:.4f} N.m")
    rng = np.random.default_rng(0)
    lo, hi = m.actuator_ctrlrange[:,0], m.actuator_ctrlrange[:,1]
    state = np.zeros(m.nu)
    with mjv.launch_passive(m, d) as v:
        v.cam.distance, v.cam.azimuth, v.cam.elevation = 0.8, 130, -15
        t0 = time.time(); sim = 0.0; k = 0
        while v.is_running():
            if a.wiggle and k % 10 == 0:
                state = 0.85*state + 0.15*rng.uniform(lo, hi)*0.6
                d.ctrl[:] = np.clip(state, lo, hi)
            mujoco.mj_step(m, d); sim += m.opt.timestep; k += 1
            if k % 10 == 0:
                v.cam.lookat[:] = [d.qpos[0], d.qpos[1], 0.06]
                v.sync()
                lag = t0 + sim - time.time()
                if lag > 0: time.sleep(lag)

if __name__ == "__main__":
    main()

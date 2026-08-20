#!/usr/bin/env python3
"""Phase 0 deliverable - a random policy twitches all 12 joints.

This is the toolchain smoke test the plan asks for, minus the Colab/MJX half:
it proves the CubeBot model loads, that all twelve position servos actuate, that
the sensor suite reads out, and that the retuned 2 ms / implicitfast physics is
stable under a policy that is doing something genuinely stupid.

    python scripts/phase0_random_policy.py            # headless, prints a report
    mjpython scripts/phase0_random_policy.py --view   # interactive window (macOS)
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
XML = ROOT / "assets" / "cubebot_12dof.xml"
DECIMATION = 10          # 2 ms physics x 10 = 50 Hz control, per the plan


def make_policy(model, rng, smooth=0.85):
    """Random walk in joint-target space, clipped to the real joint limits.

    White noise at 50 Hz would just buzz every joint against its stops and tell
    us nothing. A smoothed walk actually swings the legs through their range,
    which is what "twitches all 12 joints" is supposed to demonstrate.
    """
    lo, hi = model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1]
    state = np.zeros(model.nu)

    def step():
        nonlocal state
        target = rng.uniform(lo, hi) * 0.6          # stay off the hard stops
        state = smooth * state + (1.0 - smooth) * target
        return np.clip(state, lo, hi)

    return step


def run(seconds=6.0, seed=0, view=False):
    if not XML.exists():
        sys.exit(f"missing {XML}\nrun: python cubebot_rl/export_mjcf.py")

    model = mujoco.MjModel.from_xml_path(str(XML))
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, 0)
    mujoco.mj_forward(model, data)

    rng = np.random.default_rng(seed)
    policy = make_policy(model, rng)

    jnt_ids = [model.actuator_trnid[i, 0] for i in range(model.nu)]
    qadr = [model.jnt_qposadr[j] for j in jnt_ids]
    names = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, j) for j in jnt_ids]

    ctrl_hz = 1.0 / (model.opt.timestep * DECIMATION)
    n_ctrl = int(seconds * ctrl_hz)
    lo = np.full(model.nu, np.inf)
    hi = np.full(model.nu, -np.inf)
    trunk_z = []

    print(f"model      : {XML.name}")
    print(f"nq={model.nq} nv={model.nv} nu={model.nu} nsensordata={model.nsensordata}")
    print(f"mass       : {model.body_mass.sum()*1000:.1f} g")
    print(f"physics    : {model.opt.timestep*1000:.1f} ms, integrator="
          f"{mujoco.mjtIntegrator(model.opt.integrator).name}")
    print(f"control    : {ctrl_hz:.0f} Hz for {seconds:.0f} s "
          f"({n_ctrl} steps)\n")

    viewer = None
    if view:
        from mujoco import viewer as mj_viewer
        if sys.platform == "darwin" and getattr(mj_viewer, "_MJPYTHON", None) is None:
            sys.exit("macOS: launch with mjpython, not python")
        viewer = mj_viewer.launch_passive(model, data).__enter__()
        viewer.cam.distance, viewer.cam.azimuth = 0.9, 135
        viewer.cam.elevation, viewer.cam.lookat[:] = -20, [0, 0, 0.06]

    t0 = time.time()
    for k in range(n_ctrl):
        data.ctrl[:] = policy()
        for _ in range(DECIMATION):
            mujoco.mj_step(model, data)
        q = data.qpos[qadr]
        lo, hi = np.minimum(lo, q), np.maximum(hi, q)
        trunk_z.append(float(data.qpos[2]))
        if not np.all(np.isfinite(data.qpos)):
            sys.exit(f"DIVERGED at control step {k} - physics is unstable")
        if viewer is not None:
            viewer.sync()
            time.sleep(max(0.0, DECIMATION * model.opt.timestep -
                           (time.time() - t0) % (DECIMATION * model.opt.timestep)))
    wall = time.time() - t0

    print(f"{'joint':14s}{'min deg':>10s}{'max deg':>10s}{'swept':>10s}   moved?")
    print("-" * 56)
    ok = 0
    for i, n in enumerate(names):
        sweep = np.degrees(hi[i] - lo[i])
        moved = sweep > 1.0
        ok += moved
        print(f"{n:14s}{np.degrees(lo[i]):10.1f}{np.degrees(hi[i]):10.1f}"
              f"{sweep:10.1f}   {'yes' if moved else 'NO'}")

    touch = [data.sensor(f"{lg}_touch").data[0] for lg in ("FL", "FR", "BL", "BR")]
    print("-" * 56)
    print(f"trunk height: start {trunk_z[0]*1000:.1f} mm -> end {trunk_z[-1]*1000:.1f} mm")
    print(f"IMU quat    : {np.round(data.sensor('imu_quat').data, 3)}")
    print(f"IMU gyro    : {np.round(data.sensor('imu_gyro').data, 3)} rad/s")
    print(f"foot touch  : {np.round(touch, 3)} N")
    if not view:
        print(f"realtime    : {seconds/wall:.1f}x  ({wall:.2f}s wall for {seconds:.0f}s sim)")

    print()
    if ok == model.nu:
        print(f"PHASE 0 PASS - all {model.nu}/{model.nu} joints actuated, physics stable.")
    else:
        print(f"PHASE 0 FAIL - only {ok}/{model.nu} joints moved.")
    return ok == model.nu


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=6.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--view", action="store_true")
    a = ap.parse_args()
    sys.exit(0 if run(a.seconds, a.seed, a.view) else 1)

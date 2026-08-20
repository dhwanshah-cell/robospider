#!/usr/bin/env python3
"""Per-joint torque during ACTUAL WALKING, not standing and not free-air swing.

Everything measured so far missed the case that matters for the yaw servo:

  * static poses  -> robot standing still, no propulsion, feet carry pure
                     vertical load, so the yaw moment is nearly zero by
                     construction
  * swing arc     -> leg in free air, foot unloaded, so ground forces are zero

Walking is the union of the two: the foot is PLANTED and carries the ground
reaction while the body drives past it. The horizontal component of that
reaction acts at the foot, which sits ~78 mm out from the vertical yaw axis,
so it levers directly on the yaw servo. That is the load nobody has measured.

Gait: statically-stable crawl, duty 0.75, one leg in swing at a time. Feet are
pinned in world coordinates through stance -- which is exactly what a real
planted foot does -- so propulsion, drag and friction all appear on their own
rather than being modelled.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

LEGSTUDY = Path.home() / "cubebot-legstudy"
sys.path.insert(0, str(LEGSTUDY))
RL_XML = Path.home() / "cubebot-rl" / "assets" / "cubebot_12dof.xml"

import mujoco
from legstudy.config import LegModel, Params
from legstudy import robot as rbt

LEGS, JOINTS = rbt.LEGS, ("yaw", "pitch", "knee")
PHASE = {"FL": 0.0, "BR": 0.25, "FR": 0.5, "BL": 0.75}   # crawl order
DUTY = 0.75


def foot_targets(t, T, step, height, nf, v, R=0.0085):
    """World foot positions. Planted through stance, cycloid through swing."""
    out = {}
    for lg in LEGS:
        ph = ((t / T) - PHASE[lg]) % 1.0
        n = np.array([nf[lg][0], nf[lg][1], 0.0])
        # index of the current cycle, so the foot advances one step per cycle
        k = np.floor((t / T) - PHASE[lg])
        # centre the stance sweep on the hip: the body advances DUTY*step while
        # the foot is planted, so the foot must be placed +DUTY/2*step ahead at
        # touchdown. Getting this wrong shoves the robot backwards.
        plant = n[0] + step * (k + PHASE[lg]) + (DUTY / 2.0) * step
        if ph < DUTY:                       # STANCE: pinned in the world
            out[lg] = np.array([plant, n[1], R])   # ball CENTRE, so +radius
        else:                               # SWING: lift and reach one step on
            s = (ph - DUTY) / (1.0 - DUTY)
            x0 = plant
            x1 = x0 + step
            xs = x0 + (x1 - x0) * (s - np.sin(2 * np.pi * s) / (2 * np.pi))
            z = R + height * (1 - np.cos(2 * np.pi * s)) / 2
            out[lg] = np.array([xs, n[1], z])
    return out


def run(freq=0.9, step=0.070, height=0.030, cycles=4, unlimited=False, view=False):
    p = Params(LEGSTUDY / "params.yaml")
    base = LegModel(p.variant_names[0], p)
    r = rbt.Robot(RL_XML, base)
    m, d = r.m, r.d
    if unlimited:
        m.actuator_forcerange[:] = [-10.0, 10.0]

    nf = rbt.neutral_footholds(base)
    hip = base.p["kinematics.hip_mount_xyz"]
    _, _, fz = base.neutral_foot_position()
    z0 = -(hip[2] + fz - base.foot_radius)
    T, v = 1.0 / freq, step * freq * DUTY / DUTY   # body speed = step per cycle
    v = step / T

    mujoco.mj_resetDataKeyframe(m, d, 0)
    aid = {(lg, j): m.actuator(f"act_{lg}_{j}").id for lg in LEGS for j in JOINTS}

    # settle on the spot first
    pose = rbt.BodyPose(z=z0)
    q = {lg: r.leg_ik(pose, lg, np.array([nf[lg][0], nf[lg][1], 0.0085])) for lg in LEGS}
    for lg in LEGS:
        for k, j in enumerate(JOINTS):
            d.ctrl[aid[(lg, j)]] = q[lg][k]
    for _ in range(int(0.5 / m.opt.timestep)):
        mujoco.mj_step(m, d)

    viewer = None
    if view:
        from mujoco import viewer as mjv
        if sys.platform == "darwin" and getattr(mjv, "_MJPYTHON", None) is None:
            sys.exit("macOS: use mjpython")
        viewer = mjv.launch_passive(m, d).__enter__()
        viewer.cam.distance, viewer.cam.azimuth = 0.65, 130
        viewer.cam.elevation = -15
        viewer.cam.lookat[:] = [float(d.qpos[0]), float(d.qpos[1]), 0.06]

    dt = m.opt.timestep
    n = int(cycles * T / dt)
    peak = {(lg, j): 0.0 for lg in LEGS for j in JOINTS}
    peak_st = {j: 0.0 for j in JOINTS}      # stance-phase only
    peak_sw = {j: 0.0 for j in JOINTS}
    sat = {j: 0 for j in JOINTS}
    x0 = float(d.qpos[0])
    fell = False
    wall0 = time.time()

    for i in range(n):
        t = i * dt
        pose = rbt.BodyPose(x=v * t, z=z0)
        tgt = foot_targets(t, T, step, height, nf, v)
        for lg in LEGS:
            try:
                qq = r.leg_ik(pose, lg, tgt[lg])
            except ValueError:
                continue
            for k, j in enumerate(JOINTS):
                d.ctrl[aid[(lg, j)]] = qq[k]
        mujoco.mj_step(m, d)

        if t > T:                            # skip the first cycle
            for lg in LEGS:
                ph = ((t / T) - PHASE[lg]) % 1.0
                for j in JOINTS:
                    f = abs(float(d.actuator_force[aid[(lg, j)]]))
                    peak[(lg, j)] = max(peak[(lg, j)], f)
                    if ph < DUTY:
                        peak_st[j] = max(peak_st[j], f)
                    else:
                        peak_sw[j] = max(peak_sw[j], f)
                    lim = m.actuator_forcerange[aid[(lg, j)], 1]
                    if not unlimited and f > 0.98 * lim:
                        sat[j] += 1
        if d.qpos[2] < 0.4 * z0:
            fell = True
            break
        if viewer is not None and i % 10 == 0:
            # follow the robot, otherwise it simply walks out of frame
            viewer.cam.lookat[0] = float(d.qpos[0])
            viewer.cam.lookat[1] = float(d.qpos[1])
            viewer.cam.lookat[2] = 0.06
            viewer.sync()
            # pace to wall-clock, otherwise the whole run is over in a blink
            lag = wall0 + t - time.time()
            if lag > 0:
                time.sleep(lag)

    dist = float(d.qpos[0]) - x0
    return dict(peak=peak, stance=peak_st, swing=peak_sw, sat=sat, fell=fell,
                dist=dist, t=(i + 1) * dt, v=v, m=m, aid=aid, p=p,
                height=float(d.qpos[2]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--freq", type=float, default=0.9)
    ap.add_argument("--view", action="store_true")
    ap.add_argument("--cycles", type=int, default=4)
    a = ap.parse_args()

    SERVO = {"yaw": ("SG90", 0.1765), "pitch": ("MG996R", 0.9218),
             "knee": ("MG90S", 0.1765)}

    for unlimited in ((False,) if a.view else (True, False)):
        tag = "DEMAND (torque limit lifted)" if unlimited else "AS BUILT (real servo limits)"
        R = run(freq=a.freq, unlimited=unlimited, view=a.view and not unlimited, cycles=a.cycles)
        print(f"\n{'='*76}\n{tag}   gait {a.freq} Hz, crawl duty {DUTY}\n{'='*76}")
        print(f"  travelled {R['dist']*1000:6.1f} mm in {R['t']:.1f} s "
              f"= {R['dist']/R['t']*100:.1f} cm/s   (commanded {R['v']*100:.1f} cm/s)"
              f"{'   *** FELL OVER ***' if R['fell'] else ''}")
        print(f"\n  {'joint':7s}{'servo':9s}{'STANCE':>9s}{'swing':>9s}{'stall':>9s}"
              f"{'% used':>8s}   note")
        for j in JOINTS:
            nm, st = SERVO[j]
            pct = R['stance'][j] / st * 100
            note = "" if unlimited else (f"saturated {R['sat'][j]}x" if R['sat'][j] else "never saturated")
            print(f"  {j:7s}{nm:9s}{R['stance'][j]:9.4f}{R['swing'][j]:9.4f}{st:9.4f}"
                  f"{pct:7.1f}%   {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Which of the 12 servos actually need upgrading?

Each leg has three joints (yaw, pitch, knee) and they do completely different
jobs. Sizing all twelve to the worst one is how you end up carrying 12 heavy
servos when 4 would have done.

Static loads come from the leg study's quasi-static solver, which distributes
contact forces subject to unilateral contact and a linearised friction cone,
then substitutes them into all twelve joint rows. Dynamic loads come from a
forward sim with the torque limit lifted, so we see DEMAND rather than a
saturated actuator.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

LEGSTUDY = Path.home() / "cubebot-legstudy"
sys.path.insert(0, str(LEGSTUDY))
RL_XML = Path.home() / "cubebot-rl" / "assets" / "cubebot_12dof.xml"

import mujoco
from legstudy.config import LegModel, Params
from legstudy import robot as rbt

JOINTS = ("yaw", "pitch", "knee")

KGCM = 0.0980665
# Per-joint servo. 4.8 V column only, always.
# joint -> (name, stall N.m, no-load rad/s, grams, gear, stall A)
SERVO = {
    "yaw":   ("SG90",   1.8 * KGCM, 1.047 / 0.10,  9.0, "plastic", 0.55),
    "pitch": ("MG996R", 9.4 * KGCM, 1.047 / 0.17, 55.0, "metal",   1.50),
    "knee":  ("MG90S",  1.8 * KGCM, 1.047 / 0.10, 13.4, "metal",   0.60),
}
# rad/s of joint speed per Hz of gait, from the swing profile
SPEED_PER_HZ = {"yaw": 1.94, "pitch": 4.71, "knee": 5.56}
USABLE = 0.70          # a loaded servo never reaches its no-load speed
LEGS = rbt.LEGS


def build():
    p = Params(LEGSTUDY / "params.yaml")
    base = LegModel(p.variant_names[0], p)
    r = rbt.Robot(RL_XML, base)
    return p, base, r


def pose_cases(base, r):
    """(name, BodyPose, foot targets, support legs) over a realistic duty cycle."""
    nf = rbt.neutral_footholds(base)
    hip = base.p["kinematics.hip_mount_xyz"]
    _, _, fz = base.neutral_foot_position()
    z0 = -(hip[2] + fz - base.foot_radius)
    R = base.foot_radius          # leg_ik targets the ball CENTRE
    ground = {lg: np.array([nf[lg][0], nf[lg][1], R]) for lg in LEGS}

    cases = []
    cases.append(("stand (4 feet)", rbt.BodyPose(z=z0), ground, list(LEGS)))
    for dz, lab in [(-0.020, "squat low"), (+0.020, "stand tall")]:
        cases.append((f"{lab} (4 feet)", rbt.BodyPose(z=z0 + dz), ground, list(LEGS)))

    # tripod: lift one leg 30 mm, the other three carry everything
    for lift in LEGS:
        feet = dict(ground)
        feet[lift] = ground[lift] + np.array([0, 0, 0.030])   # already ball-centre
        sup = [l for l in LEGS if l != lift]
        cases.append((f"tripod, {lift} lifted", rbt.BodyPose(z=z0), feet, sup))
        cases.append((f"tripod+squat, {lift} lifted",
                      rbt.BodyPose(z=z0 - 0.020), feet, sup))

    for ang, lab in [(np.radians(16), "pitch +16"), (np.radians(-16), "pitch -16")]:
        cases.append((f"{lab} (4 feet)", rbt.BodyPose(z=z0, pitch=ang), ground, list(LEGS)))
    for ang, lab in [(np.radians(14), "roll +14"), (np.radians(-14), "roll -14")]:
        cases.append((f"{lab} (4 feet)", rbt.BodyPose(z=z0, roll=ang), ground, list(LEGS)))
    return cases


def static_audit(r, cases):
    """peak |tau| per (leg, joint) across every static case."""
    peak = {(lg, j): 0.0 for lg in LEGS for j in JOINTS}
    worst = {(lg, j): "" for lg in LEGS for j in JOINTS}
    rows = []
    for name, pose, feet, sup in cases:
        try:
            q = {lg: r.leg_ik(pose, lg, feet[lg]) for lg in LEGS}
        except ValueError:
            rows.append((name, None, "UNREACHABLE"))
            continue
        sol = r.solve_loads(pose, q, sup)
        if sol is None:
            rows.append((name, None, "no solution"))
            continue
        tau = sol["tau"]
        rows.append((name, tau, "feasible" if sol.get("feasible", True) else "INFEASIBLE"))
        for lg in LEGS:
            for k, j in enumerate(JOINTS):
                v = abs(float(tau[lg][k]))
                if v > peak[(lg, j)]:
                    peak[(lg, j)], worst[(lg, j)] = v, name
    return peak, worst, rows


def swing_audit(freqs=(1.0, 2.0, 3.0, 4.0)):
    """Dynamic demand via INVERSE DYNAMICS on the single-leg swing model.

    Not a forward sim. Lifting the torque clamp and reading actuator_force
    measures what an unlimited position servo would *command* (kp x tracking
    error), which at 4 Hz is enormous because the servo cannot track. Leaving
    the clamp on measures what a saturated servo *managed*, which is 0.216 by
    construction. Neither is the demand.

    Inverse dynamics asks the actual question: to follow this foot path exactly,
    what torque must each joint produce? The leg is in free air (this model has
    no floor), so this is pure swing.
    """
    from legstudy import kinematics as kin
    p = Params(LEGSTUDY / "params.yaml")
    base = LegModel(p.variant_names[0], p)

    m = mujoco.MjModel.from_xml_path(str(LEGSTUDY / "build" / "A_baseline_swing.xml"))
    d = mujoco.MjData(m)
    names = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, i) for i in range(m.njnt)]
    # shoulder_yaw / shoulder_pitch / knee  ->  yaw / pitch / knee
    idx = {j: names.index(n) for j, n in
           zip(JOINTS, ("shoulder_yaw", "shoulder_pitch", "knee"))}

    out = {}
    for f in freqs:
        N, T = 2000, 1.0 / f
        dt = T / N
        q = np.zeros((N, 3))
        for i in range(N):
            q[i] = kin.ik(base, kin.swing_arc(base, (i / N) % 1.0)[0])
        # central differences on the closed (periodic) loop
        v = (np.roll(q, -1, 0) - np.roll(q, 1, 0)) / (2 * dt)
        a = (np.roll(q, -1, 0) - 2 * q + np.roll(q, 1, 0)) / (dt * dt)

        peak = np.zeros(3)
        for i in range(N):
            d.qpos[:] = q[i]; d.qvel[:] = v[i]; d.qacc[:] = a[i]
            mujoco.mj_inverse(m, d)
            peak = np.maximum(peak, np.abs(d.qfrc_inverse))
        out[f] = {j: float(peak[idx[j]]) for j in JOINTS}
    return out


def main():
    p, base, r = build()
    stall = float(p["servo.stall_torque_nm"])
    print(f"servo   : {p['servo.model']}, stall {stall:.3f} N.m @ 6V")
    print(f"robot   : {p['trials.stance.body_mass_kg']} kg\n")

    cases = pose_cases(base, r)
    peak, worst, rows = static_audit(r, cases)
    sw = swing_audit()

    print("swing demand by frequency (inverse dynamics, leg in free air):")
    print(f"  {'Hz':>4s}" + "".join(f"{j:>10s}" for j in JOINTS))
    for f in sorted(sw):
        print(f"  {f:4.0f}" + "".join(f"{sw[f][j]:10.4f}" for j in JOINTS))
    print()

    print("=" * 78)
    print("PEAK TORQUE DEMAND PER JOINT  (worst over all static poses + swing)")
    print("=" * 78)
    print(f"{'joint':7s}{'servo':9s}{'static':>9s}{'swing4':>9s}{'WORST':>9s}"
          f"{'stall':>8s}{'% used':>8s}   verdict")
    print("-" * 78)
    summary = {}
    for j in JOINTS:
        nm, st_t, _, _, gear, _ = SERVO[j]
        stat = max(peak[(lg, j)] for lg in LEGS)
        stleg = max(LEGS, key=lambda lg: peak[(lg, j)])
        dy = sw[4.0][j]
        w = max(stat, dy)
        pct = w / st_t * 100
        v = ("comfortable" if pct < 35 else "OK" if pct < 50
             else "runs hot" if pct < 100 else "STALLS")
        summary[j] = (stat, dy, w, pct)
        print(f"{j:7s}{nm:9s}{stat:9.4f}{dy:9.4f}{w:9.4f}{st_t:8.4f}{pct:7.1f}%   {v}")
    print("-" * 78)

    print("\nSPEED — the gait ceiling (loaded servos reach ~70% of no-load):")
    caps = {}
    for j in JOINTS:
        nm, _, w_nl, _, _, _ = SERVO[j]
        caps[j] = USABLE * w_nl / SPEED_PER_HZ[j]
        print(f"  {j:7s}{nm:9s} no-load {w_nl:5.2f} rad/s, needs "
              f"{SPEED_PER_HZ[j]:.2f} rad/s per Hz -> max {caps[j]:.2f} Hz")
    lim = min(caps, key=caps.get)
    print(f"  => gait capped at {caps[lim]:.2f} Hz by the {lim.upper()} servo "
          f"= {0.070*caps[lim]*100:.1f} cm/s at a 70 mm step")

    amps = sum(4 * SERVO[j][5] for j in JOINTS)
    print(f"\nPOWER: all-stall {amps:.1f} A vs 12 A of UBEC "
          f"[{'OVER' if amps > 12 else 'ok'}]")
    mass = sum(4 * SERVO[j][3] for j in JOINTS)
    print(f"MASS : servos {mass:.0f} g of a {p['trials.stance.body_mass_kg']*1000:.0f} g robot "
          f"({mass/(p['trials.stance.body_mass_kg']*1000)*100:.0f}%)")

    print("\nper-leg static peak (N.m):")
    print(f"{'leg':6s}" + "".join(f"{j:>10s}" for j in JOINTS))
    for lg in LEGS:
        print(f"{lg:6s}" + "".join(f"{peak[(lg,j)]:10.4f}" for j in JOINTS))

    print("\nstatic cases:")
    for name, tau, status in rows:
        if tau is None:
            print(f"  {name:32s} {status}")
            continue
        mx = max(float(np.abs(v).max()) for v in tau.values())
        print(f"  {name:32s} max |tau| {mx:.4f} N.m  ({mx/stall*100:5.1f}% stall)  {status}")
    return summary, stall


if __name__ == "__main__":
    main()

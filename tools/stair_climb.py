#!/usr/bin/env python3
"""Can it climb a step as tall as it is? (144 mm = top of the case.)

Quasi-static climb from the leg study's stairs module: at every phase of the
haul it solves the contact forces subject to unilateral contact and a friction
cone, then reads all twelve joint torques. A height counts as climbable only if
EVERY instant is reachable, statically stable, and inside the per-joint torque
limit -- checked against each joint's own servo, not one global number.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np

LEGSTUDY = Path.home() / "cubebot-legstudy"
sys.path.insert(0, str(LEGSTUDY))
RL_XML = Path.home() / "cubebot-rl" / "assets" / "cubebot_12dof.xml"

from legstudy.config import LegModel, Params
from legstudy import robot as rbt
from legstudy import stairs

LEGS, JOINTS = rbt.LEGS, ("yaw", "pitch", "knee")
KGCM = 0.0980665
SERVO = {"yaw": ("SG90", 1.8*KGCM), "pitch": ("MG996R", 9.4*KGCM),
         "knee": ("MG90S", 1.8*KGCM)}
BOT_H = 0.1442


def assess(peak):
    """worst per-joint utilisation against that joint's own servo"""
    out = {}
    for j in JOINTS:
        t = max(peak[(lg, j)] for lg in LEGS)
        out[j] = (t, t / SERVO[j][1] * 100)
    return out


def main():
    p = Params(LEGSTUDY / "params.yaml")
    base = LegModel(p.variant_names[0], p)
    r = rbt.Robot(RL_XML, base)
    print(f"robot {p['trials.stance.body_mass_kg']} kg | bot height {BOT_H*1000:.0f} mm "
          f"| servos: " + ", ".join(f"{j}={SERVO[j][0]}({SERVO[j][1]:.3f})" for j in JOINTS))

    heights = [0.05, 0.075, 0.10, 0.125, BOT_H, 0.175, 0.20]
    for strat in ("naive", "smart"):
        print(f"\n{'='*74}\nSTRATEGY: {strat}\n{'='*74}")
        print(f"{'step mm':>8s}{'reach/stable':>14s}{'yaw %':>9s}{'pitch %':>9s}"
              f"{'knee %':>9s}   verdict")
        for h in heights:
            try:
                samples = stairs.run_climb(r, h, strat)
            except Exception as e:
                print(f"{h*1000:8.0f}{'ERROR':>14s}   {type(e).__name__}: {e}")
                continue
            infeasible = [s for s in samples
                          if s.result.get("loads") is None
                          or not s.result["loads"]["feasible"]]
            ok_geom = not infeasible
            peak = stairs.envelope(samples)
            a = assess(peak)
            over = [j for j in JOINTS if a[j][1] > 100]
            if not ok_geom:
                v = f"FAILS - unreachable/unstable ({len(infeasible)}/{len(samples)} phases)"
            elif over:
                v = "FAILS - torque: " + ",".join(over)
            else:
                v = "CLIMBS"
            star = " <-- BOT HEIGHT" if abs(h - BOT_H) < 1e-6 else ""
            print(f"{h*1000:8.0f}{('yes' if ok_geom else 'NO'):>14s}"
                  f"{a['yaw'][1]:8.0f}%{a['pitch'][1]:8.0f}%{a['knee'][1]:8.0f}%   {v}{star}")

    # detail at bot height, smart
    print(f"\n{'='*74}\nDETAIL @ {BOT_H*1000:.0f} mm, smart stance\n{'='*74}")
    samples = stairs.run_climb(r, BOT_H, "smart")
    peak = stairs.envelope(samples)
    a = assess(peak)
    for j in JOINTS:
        nm, st = SERVO[j]
        print(f"  {j:7s}{nm:9s} peak {a[j][0]:.4f} N.m / {st:.4f} = {a[j][1]:.0f}%")
    bad = [(s.phase, s.result.get('loads')) for s in samples
           if s.result.get("loads") is None or not s.result["loads"]["feasible"]]
    print(f"  phases total {len(samples)}, infeasible {len(bad)}")
    if bad:
        from collections import Counter
        print("  failing phases:", dict(Counter(ph for ph, _ in bad)))


if __name__ == "__main__":
    main()

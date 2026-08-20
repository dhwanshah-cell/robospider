#!/usr/bin/env python3
"""Layer 1 - author a reference motion by dragging feet, not typing joint angles.

Five mocap handles appear in the viewer: one per foot (red = front, blue = rear)
and one for the trunk (green). ctrl+drag them with the mouse. Inverse kinematics
solves each leg's three joints, and every pose is scored live against the real
hardware: reachability, joint limits, static stability (friction cone +
unilateral contact) and per-joint torque as a fraction of THAT joint's servo.

You never touch a joint angle. You place feet, which is how legged motion is
actually conceived -- and it is the part a human does better than any solver.

The keyframes you record become the reference trajectory for Layer 3 (RL). The
reference does NOT have to be physically perfect: DeepMimic-style tracking
learns the corrections. Author the intent; let RL find the achievable version.

    mjpython scripts/pose_author.py                    # flat ground
    mjpython scripts/pose_author.py --wall 0.1442      # with a wall to climb

Keys (focus the viewer window):
    R  record keyframe          U  undo last          C  clear all
    S  save to results/         L  load last save
    1-4 toggle FL/FR/BL/BR between STANCE and SWING (which feet bear load)
    T  print the full status table for the current pose
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
import os, tempfile

import numpy as np

LEGSTUDY = Path.home() / "cubebot-legstudy"
sys.path.insert(0, str(LEGSTUDY))
sys.path.insert(0, str(Path.home() / "cubebot-rl"))

import mujoco
from legstudy.config import LegModel, Params
from legstudy import robot as rbt
from cubebot_rl.export_mjcf import retune

LEGS, JOINTS = rbt.LEGS, ("yaw", "pitch", "knee")
KGCM = 0.0980665
SERVO = {"yaw": ("SG90", 1.8*KGCM), "pitch": ("MG996R", 9.4*KGCM),
         "knee": ("MG90S", 1.8*KGCM)}
OUT = Path.home() / "cubebot-rl" / "results"
HANDLE = {"FL": "1 0.35 0.35 0.9", "FR": "1 0.55 0.35 0.9",
          "BL": "0.35 0.6 1 0.9", "BR": "0.35 0.8 1 0.9"}


def build(wall: float):
    p = Params(LEGSTUDY / "params.yaml")
    base = LegModel(p.variant_names[0], p)
    xml = retune(rbt.build_robot_mjcf(
        base, step_height=wall, step_x=0.105, with_stair=wall > 0.0,
        actuators="position", free_base=True))
    root = ET.fromstring(xml)
    wb = root.find("worldbody")
    nf = rbt.neutral_footholds(base)
    R = base.foot_radius
    # start clear of the wall: the neutral footprint puts the front feet at
    # x=+99.5 mm and a wall face sits at 105 mm, so the default spawn clips
    back = -0.075 if wall > 0.0 else 0.0
    for lg in LEGS:                              # foot handles
        b = ET.SubElement(wb, "body", name=f"tgt_{lg}", mocap="true",
                          pos=f"{nf[lg][0] + back} {nf[lg][1]} {R}")
        ET.SubElement(b, "geom", type="sphere", size="0.010", mass="0",
                      rgba=HANDLE[lg], contype="0", conaffinity="0", group="1")
    b = ET.SubElement(wb, "body", name="tgt_body", mocap="true",
                      pos=f"{back} 0 0.103")
    ET.SubElement(b, "geom", type="box", size="0.012 0.012 0.006", mass="0",
                  rgba="0.35 1 0.45 0.9", contype="0", conaffinity="0", group="1")
    path = Path(str(Path(os.environ.get("CUBEBOT_RUNTIME", Path(tempfile.gettempdir())/"cubebot")))+"/author.xml")
    path.write_text(ET.tostring(root, encoding="unicode"))
    return path, base, p


def quat_to_rp(q):
    """mocap quaternion -> (roll, pitch) in BodyPose's convention."""
    w, x, y, z = q
    pitch = math.asin(max(-1.0, min(1.0, 2.0 * (w * y - z * x))))
    roll = math.atan2(2.0 * (w * x + y * z), 1.0 - 2.0 * (x * x + y * y))
    return roll, pitch


class Author:
    def __init__(self, wall):
        self.path, self.base, self.p = build(wall)
        self.r = rbt.Robot(self.path, self.base)
        self.m, self.d = self.r.m, self.r.d
        self.R = self.base.foot_radius
        self.wall = wall
        self.mid = {n: int(self.m.body(f"tgt_{n}").mocapid[0])
                    for n in list(LEGS) + ["body"]}
        self.stance = {lg: True for lg in LEGS}
        self.keys: list[dict] = []
        self.msg = ""
        self.last = None
        self.rgba0 = self.m.geom_rgba.copy()
        self.vis = [i for i in range(self.m.ngeom)
                    if (self.m.geom_group[i] in (2, 3)
                        or mujoco.mj_id2name(self.m, mujoco.mjtObj.mjOBJ_GEOM, i)
                        in ("trunk_col",))]

    # -- evaluate one pose ------------------------------------------
    def solve(self):
        res = self._solve()
        self.last = res
        return res

    def _solve(self):
        bp = self.d.mocap_pos[self.mid["body"]]
        roll, pitch = quat_to_rp(self.d.mocap_quat[self.mid["body"]])
        pose = rbt.BodyPose(x=float(bp[0]), y=float(bp[1]), z=float(bp[2]),
                            roll=roll, pitch=pitch)
        feet = {lg: np.array(self.d.mocap_pos[self.mid[lg]]) for lg in LEGS}
        try:
            q = {lg: self.r.leg_ik(pose, lg, feet[lg]) for lg in LEGS}
        except ValueError:
            return pose, feet, None, None, "UNREACHABLE"

        # place the robot FIRST: mj_forward runs collision detection, and a
        # kinematic tool will happily bury the body inside a wall unless we look
        self.r.set_state(pose, q)

        issues = []
        margin = self.r.joint_limit_margin(q)
        if margin < 0:
            issues.append(f"JOINT LIMIT by {abs(margin):.2f} rad")
        pen = self.penetration()
        if pen:
            issues.append(f"CLIPPING {pen[1]} by {pen[0]*1000:.0f} mm")

        use = None
        sup = [lg for lg in LEGS if self.stance[lg]]
        if not sup:
            issues.append("no stance feet")
        else:
            sol = self.r.solve_loads(pose, q, sup)
            if sol is None:
                issues.append("no load solution")
            else:
                use = {j: max(abs(sol["tau"][lg][k]) for lg in LEGS) / SERVO[j][1]
                       for k, j in enumerate(JOINTS)}
                over = [j for j in JOINTS if use[j] > 1.0]
                if not sol["feasible"]:
                    issues.append("UNSTABLE (friction cone)")
                if over:
                    issues.append("OVER TORQUE: " + ",".join(over))
        return pose, feet, q, use, ("OK" if not issues else " | ".join(issues))

    def paint(self, status, pen):
        """Tint the robot by validity -- the viewer has no text overlay, so the
        model itself has to be the readout."""
        self.m.geom_rgba[:] = self.rgba0
        if status == "OK":
            return
        bad = (1.0, 0.25, 0.2)
        for i in self.vis:                      # whole robot goes red
            self.m.geom_rgba[i, 0:3] = bad
        if pen:                                 # offenders go vivid + opaque
            for gid in pen[2]:
                self.m.geom_rgba[gid, 0:3] = (1.0, 0.0, 0.6)
                self.m.geom_rgba[gid, 3] = 1.0

    def penetration(self, tol=5e-4):
        """Worst geometry interpenetration in the current pose, if any."""
        worst, pair, ids = 0.0, None, ()
        for i in range(self.d.ncon):
            c = self.d.contact[i]
            if c.dist < -tol and -c.dist > worst:
                worst = -c.dist
                g1 = mujoco.mj_id2name(self.m, mujoco.mjtObj.mjOBJ_GEOM, c.geom1)
                g2 = mujoco.mj_id2name(self.m, mujoco.mjtObj.mjOBJ_GEOM, c.geom2)
                pair, ids = f"{g1}/{g2}", (c.geom1, c.geom2)
        return (worst, pair, ids) if pair else None

    # -- keyboard ----------------------------------------------------
    def key(self, code):
        c = chr(code) if 32 <= code < 127 else ""
        if c in "Rr":
            pose, feet, q, use, st = self.last or (None,)*5
            if q is None:
                self.msg = "cannot record: pose invalid"; return
            if st != "OK":
                self.msg = f"refused: {st[:34]}"; return
            self.keys.append(dict(
                body=[pose.x, pose.y, pose.z, pose.roll, pose.pitch],
                feet={lg: list(map(float, feet[lg])) for lg in LEGS},
                stance={lg: bool(self.stance[lg]) for lg in LEGS},
                q={lg: list(map(float, q[lg])) for lg in LEGS},
                use={j: float(use[j]) for j in JOINTS} if use else None,
                status=st))
            self.msg = f"recorded keyframe {len(self.keys)} [{st}]"
        elif c in "Uu" and self.keys:
            self.keys.pop(); self.msg = f"undo -> {len(self.keys)} keyframes"
        elif c in "Cc":
            self.keys.clear(); self.msg = "cleared"
        elif c in "Ss":
            OUT.mkdir(exist_ok=True)
            f = OUT / f"reference_motion_{int(self.wall*1000)}mm.json"
            f.write_text(json.dumps({"wall_m": self.wall, "keys": self.keys}, indent=1))
            self.msg = f"saved {len(self.keys)} keyframes -> {f.name}"
        elif c in "Ll":
            f = OUT / f"reference_motion_{int(self.wall*1000)}mm.json"
            if f.exists():
                self.keys = json.loads(f.read_text())["keys"]
                self.msg = f"loaded {len(self.keys)} keyframes"
        elif c in "1234":
            lg = LEGS[int(c) - 1]
            self.stance[lg] = not self.stance[lg]
            self.msg = f"{lg} -> {'STANCE' if self.stance[lg] else 'SWING'}"
        elif c in "Tt":
            pose, feet, q, use, st = self.last or (None,)*5
            if q is None:
                self.msg = "no valid pose"; return
            print(f"\n  body  x={pose.x*1000:+.0f} y={pose.y*1000:+.0f} z={pose.z*1000:.0f} mm "
                  f"roll={math.degrees(pose.roll):+.0f} pitch={math.degrees(pose.pitch):+.0f} deg")
            for lg in LEGS:
                print(f"  {lg}  " + "  ".join(
                    f"{j}={math.degrees(q[lg][k]):+7.1f}deg" for k, j in enumerate(JOINTS))
                    + f"   {'STANCE' if self.stance[lg] else 'swing '}")
            if use:
                print("  torque " + "  ".join(
                    f"{j}({SERVO[j][0]})={use[j]*100:.0f}%" for j in JOINTS))
            print(f"  status {st}\n")

    def run(self):
        from mujoco import viewer as mjv
        if sys.platform == "darwin" and getattr(mjv, "_MJPYTHON", None) is None:
            sys.exit("macOS: launch with mjpython, not python")
        print(__doc__)
        print(f"servos: " + ", ".join(f"{j}={SERVO[j][0]}" for j in JOINTS))
        print(f"robot {self.p['trials.stance.body_mass_kg']} kg"
              + (f", wall {self.wall*1000:.0f} mm" if self.wall else ", flat ground"))
        print("\nctrl+drag a handle to move it. Watch the status line.\n")
        with mjv.launch_passive(self.m, self.d, key_callback=self.key) as v:
            v.cam.distance, v.cam.azimuth, v.cam.elevation = 0.75, 120, -12
            v.cam.lookat[:] = [0.02, 0, 0.06]
            last_print = 0.0
            while v.is_running():
                pose, feet, q, use, st = self.solve()
                self.paint(st, self.penetration() if q is not None else None)
                if q is not None:
                    self.r.set_state(pose, q)
                now = time.time()
                if now - last_print > 0.25:
                    last_print = now
                    t = ("  ".join(f"{j}={use[j]*100:3.0f}%" for j in JOINTS)
                         if use else "     --      ")
                    sw = "".join(lg[0].lower() if not self.stance[lg] else lg[0]
                                 for lg in LEGS)
                    sys.stdout.write(
                        f"\r  [{len(self.keys):2d} keys] feet:{sw}  {t}  {st:44s} {self.msg:38s}")
                    sys.stdout.flush()
                v.sync()
                time.sleep(1/60)
        print()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--wall", type=float, default=0.0)
    a = ap.parse_args()
    Author(a.wall).run()

#!/usr/bin/env python3
"""Puppeteer the robot WITH physics running, and record what actually happened.

The earlier authoring tool was kinematic: it wrote joint angles straight into
qpos, so the body never responded, nothing collided, and dragging a foot just
stretched a leg until it turned red. Useless for authoring motion.

This runs the real simulation. mj_step every tick, gravity on, contacts on,
the actual SG90 / MG996R / MG90S torque and speed limits on the actuators.

  * You drag the four foot handles. They are TARGETS, not positions.
  * Each control tick, IK is solved from the robot's ACTUAL body pose (read out
    of qpos, not commanded) to your targets, and the result is written to the
    position servos.
  * Physics decides what happens next. Drag a foot up and that leg lifts; drag
    too far and the servo saturates and the robot sags or topples -- which is
    exactly the information you want.

So the robot cannot pass through the wall, cannot levitate, and cannot hold a
pose its servos cannot hold. Anything you record is physically achievable by
construction, because it already happened.

    mjpython scripts/puppet.py --wall 0.1442

Keys:  SPACE pause/run   R start/stop recording   S save   0 reset
       H hold current targets   T status table
"""
from __future__ import annotations

import argparse, json, math, sys, time
import xml.etree.ElementTree as ET
from pathlib import Path
import os, tempfile
import numpy as np

LEGSTUDY = Path.home() / "cubebot-legstudy"
sys.path.insert(0, str(LEGSTUDY)); sys.path.insert(0, str(Path.home() / "cubebot-rl"))
import mujoco
from legstudy.config import LegModel, Params
from legstudy import robot as rbt
from cubebot_rl.export_mjcf import retune

LEGS, JOINTS = rbt.LEGS, ("yaw", "pitch", "knee")
KGCM = 0.0980665
SERVO = {"yaw": ("SG90", 1.8*KGCM), "pitch": ("MG996R", 9.4*KGCM),
         "knee": ("MG90S", 1.8*KGCM)}
COL = {"FL": "1 0.35 0.35 0.85", "FR": "1 0.6 0.3 0.85",
       "BL": "0.3 0.6 1 0.85", "BR": "0.3 0.85 1 0.85"}
OUT = Path.home() / "cubebot-rl" / "results"
DECIM = 10


def build(wall):
    p = Params(LEGSTUDY / "params.yaml")
    base = LegModel(p.variant_names[0], p)
    xml = retune(rbt.build_robot_mjcf(base, step_height=wall, step_x=0.105,
                                      with_stair=wall > 0.0, actuators="position",
                                      free_base=True))
    root = ET.fromstring(xml); wb = root.find("worldbody")
    nf = rbt.neutral_footholds(base); R = base.foot_radius
    back = -0.075 if wall > 0.0 else 0.0
    for lg in LEGS:
        b = ET.SubElement(wb, "body", name=f"tgt_{lg}", mocap="true",
                          pos=f"{nf[lg][0]+back} {nf[lg][1]} {R}")
        ET.SubElement(b, "geom", type="sphere", size="0.009", mass="0",
                      rgba=COL[lg], contype="0", conaffinity="0", group="1")
    b = ET.SubElement(wb, "body", name="tgt_body", mocap="true",
                      pos=f"{back} 0 0.103")
    ET.SubElement(b, "geom", type="box", size="0.014 0.014 0.005", mass="0",
                  rgba="0.3 1 0.45 0.85", contype="0", conaffinity="0", group="1")
    f = Path(str(Path(os.environ.get("CUBEBOT_RUNTIME", Path(tempfile.gettempdir())/"cubebot")))+"/puppet.xml")
    f.write_text(ET.tostring(root, encoding="unicode"))
    return f, base, p, back


def body_pose_from_qpos(d):
    """The body pose PHYSICS produced -- not something we commanded."""
    x, y, z = d.qpos[0:3]
    w, qx, qy, qz = d.qpos[3:7]
    pitch = math.asin(max(-1.0, min(1.0, 2.0*(w*qy - qz*qx))))
    roll = math.atan2(2.0*(w*qx + qy*qz), 1.0 - 2.0*(qx*qx + qy*qy))
    return rbt.BodyPose(x=float(x), y=float(y), z=float(z), roll=roll, pitch=pitch)


class Puppet:
    def __init__(self, wall):
        self.path, self.base, self.p, self.back = build(wall)
        self.r = rbt.Robot(self.path, self.base)
        self.m, self.d = self.r.m, self.r.d
        self.wall = wall
        self.mid = {n: int(self.m.body(f"tgt_{n}").mocapid[0])
                    for n in list(LEGS) + ["body"]}
        self.aid = {(lg, j): self.m.actuator(f"act_{lg}_{j}").id
                    for lg in LEGS for j in JOINTS}
        self.run = True
        self.rec = False
        self.tape: list[dict] = []
        self.msg = "running"
        self.ik_fail = {lg: False for lg in LEGS}
        self.reset()

    def reset(self):
        mujoco.mj_resetDataKeyframe(self.m, self.d, 0)
        self.d.qpos[0] += self.back
        mujoco.mj_forward(self.m, self.d)
        nf = rbt.neutral_footholds(self.base)
        for lg in LEGS:
            self.d.mocap_pos[self.mid[lg]] = [nf[lg][0] + self.back, nf[lg][1],
                                              self.base.foot_radius]
        self.d.mocap_pos[self.mid["body"]] = [self.back, 0.0, 0.103]
        self.tape.clear(); self.rec = False
        self.msg = "reset"

    def control(self):
        """IK from the DESIRED body pose (green handle) to the dragged foot
        targets -> servo commands. Solving from the ACTUAL pose instead makes
        the controller chase its own sag: the robot sinks, IK re-solves to the
        sunk pose, and nothing ever pushes back."""
        bp = self.d.mocap_pos[self.mid["body"]]
        bq = self.d.mocap_quat[self.mid["body"]]
        w, qx, qy, qz = bq
        pitch = math.asin(max(-1.0, min(1.0, 2.0*(w*qy - qz*qx))))
        roll = math.atan2(2.0*(w*qx + qy*qz), 1.0 - 2.0*(qx*qx + qy*qy))
        pose = rbt.BodyPose(x=float(bp[0]), y=float(bp[1]), z=float(bp[2]),
                            roll=roll, pitch=pitch)
        for lg in LEGS:
            tgt = np.array(self.d.mocap_pos[self.mid[lg]])
            try:
                q = self.r.leg_ik(pose, lg, tgt)
                self.ik_fail[lg] = False
            except ValueError:
                self.ik_fail[lg] = True      # hold last command for this leg
                continue
            lo = self.m.actuator_ctrlrange[[self.aid[(lg, j)] for j in JOINTS], 0]
            hi = self.m.actuator_ctrlrange[[self.aid[(lg, j)] for j in JOINTS], 1]
            q = np.clip(q, lo, hi)
            for k, j in enumerate(JOINTS):
                self.d.ctrl[self.aid[(lg, j)]] = q[k]

    def stats(self):
        use = {j: max(abs(float(self.d.actuator_force[self.aid[(lg, j)]]))
                      for lg in LEGS) / SERVO[j][1] for j in JOINTS}
        feet_down = sum(1 for i in range(self.d.ncon)
                        if "foot" in (mujoco.mj_id2name(self.m, mujoco.mjtObj.mjOBJ_GEOM,
                                                        self.d.contact[i].geom1) or "")
                        or "foot" in (mujoco.mj_id2name(self.m, mujoco.mjtObj.mjOBJ_GEOM,
                                                        self.d.contact[i].geom2) or ""))
        return use, feet_down

    def key(self, code):
        c = chr(code) if 32 <= code < 127 else ""
        if code == 32:
            self.run = not self.run; self.msg = "running" if self.run else "PAUSED"
        elif c in "Rr":
            self.rec = not self.rec
            self.msg = f"RECORDING ({len(self.tape)} frames)" if self.rec else \
                       f"stopped, {len(self.tape)} frames"
        elif c in "Ss":
            OUT.mkdir(exist_ok=True)
            f = OUT / f"puppet_motion_{int(self.wall*1000)}mm.json"
            f.write_text(json.dumps({"wall_m": self.wall, "dt": self.m.opt.timestep*DECIM,
                                     "joints": [f"{lg}_{j}" for lg in LEGS for j in JOINTS],
                                     "frames": self.tape}, indent=0))
            self.msg = f"saved {len(self.tape)} frames -> {f.name}"
        elif c in "0":
            self.reset()
        elif c in "Tt":
            use, fd = self.stats()
            pose = body_pose_from_qpos(self.d)
            print(f"\n  body z={pose.z*1000:6.1f} mm  pitch={math.degrees(pose.pitch):+6.1f} "
                  f"roll={math.degrees(pose.roll):+6.1f} deg   feet in contact: {fd}")
            print("  torque " + "  ".join(
                f"{j}({SERVO[j][0]})={use[j]*100:3.0f}%" for j in JOINTS))
            print("  IK unreachable: " +
                  (", ".join(l for l in LEGS if self.ik_fail[l]) or "none") + "\n")

    def go(self):
        from mujoco import viewer as mjv
        if sys.platform == "darwin" and getattr(mjv, "_MJPYTHON", None) is None:
            sys.exit("macOS: launch with mjpython")
        print(__doc__)
        print(f"robot {self.p['trials.stance.body_mass_kg']} kg, "
              f"{'wall %.0f mm' % (self.wall*1000) if self.wall else 'flat ground'}\n")
        dt = self.m.opt.timestep
        with mjv.launch_passive(self.m, self.d, key_callback=self.key) as v:
            v.cam.distance, v.cam.azimuth, v.cam.elevation = 0.8, 120, -12
            v.cam.lookat[:] = [0.0, 0, 0.06]
            t_wall = time.time(); sim_t = 0.0; last = 0.0
            while v.is_running():
                if self.run:
                    for _ in range(DECIM):
                        mujoco.mj_step(self.m, self.d)
                        sim_t += dt
                    self.control()
                    if self.rec:
                        self.tape.append({
                            "t": round(sim_t, 4),
                            "qpos": [round(float(x), 5) for x in self.d.qpos],
                            "ctrl": [round(float(x), 5) for x in self.d.ctrl]})
                else:
                    mujoco.mj_forward(self.m, self.d)
                v.cam.lookat[0] = float(self.d.qpos[0])
                v.sync()
                now = time.time()
                if now - last > 0.25:
                    last = now
                    use, fd = self.stats()
                    p = body_pose_from_qpos(self.d)
                    sys.stdout.write(
                        f"\r  z={p.z*1000:5.1f}mm pitch={math.degrees(p.pitch):+5.0f} "
                        f"contacts:{fd}  " +
                        "  ".join(f"{j}={use[j]*100:3.0f}%" for j in JOINTS) +
                        f"  {'REC ' + str(len(self.tape)) if self.rec else '    '}"
                        f"  {self.msg:34s}")
                    sys.stdout.flush()
                lag = t_wall + sim_t - time.time()
                if lag > 0:
                    time.sleep(lag)
        print()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--wall", type=float, default=0.1442)
    Puppet(ap.parse_args().wall).go()

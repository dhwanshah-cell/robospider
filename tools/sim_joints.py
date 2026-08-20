#!/usr/bin/env python3
"""Simulator half of the joint-control rig. Run this FIRST, then joint_panel.py.

Reads commanded joint angles from cmd.json, drives the position servos with
them, steps real physics (gravity, contacts, the actual SG90/MG996R/MG90S
torque and speed limits), and writes actual state back to state.json for the
panel to display.

Recording is continuous while the panel's REC box is ticked: every control tick
appends qpos + ctrl to the take. Because the take is produced by stepping
physics, everything in it is achievable by construction -- it already happened.

    mjpython scripts/sim_joints.py --wall 0.1442
"""
from __future__ import annotations
import argparse, json, math, os, sys, time
from pathlib import Path
import os, tempfile
import numpy as np

LEGSTUDY = Path.home() / "cubebot-legstudy"
sys.path.insert(0, str(LEGSTUDY)); sys.path.insert(0, str(Path.home() / "cubebot-rl"))
import mujoco
from legstudy.config import LegModel, Params
from legstudy import robot as rbt
from cubebot_rl.export_mjcf import retune
from cubebot_rl.gait import Crawl

SP = Path(os.environ.get("CUBEBOT_RUNTIME", Path(tempfile.gettempdir())/"cubebot"))
CMD, STATE = SP / "cmd.json", SP / "state.json"
OUT = Path.home() / "cubebot-rl" / "results"
LEGS, JOINTS = rbt.LEGS, ("yaw", "pitch", "knee")
NAMES = [f"{lg}_{j}" for lg in LEGS for j in JOINTS]
KGCM = 0.0980665
STALL = {"yaw": 1.8*KGCM, "pitch": 9.4*KGCM, "knee": 1.8*KGCM}
DECIM = 10


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wall", type=float, default=0.1442)
    ap.add_argument("--from-take", action="store_true",
                    help="start parked in the final pose of the latest take")
    ap.add_argument("--servo", default=None,
                    help="override every joint: MG90S|SG90|SG92R|MG92B|MG996R")
    ap.add_argument("--yaw", default=None, help="servo for the yaw joints")
    ap.add_argument("--pitch", default=None, help="servo for the pitch joints")
    ap.add_argument("--knee", default=None, help="servo for the knee joints")
    ap.add_argument("--from-pose", default=None,
                    help="park in a pose json from results/")
    ap.add_argument("--strip-factor", type=float, default=0.0,
                    help="gear strips when transmitted torque exceeds N x stall "
                         "(0 = disabled). Nylon ~2-3x, POM/carbon ~3-4x, metal ~5x+")
    a = ap.parse_args()
    from mujoco import viewer as mjv
    if sys.platform == "darwin" and getattr(mjv, "_MJPYTHON", None) is None:
        sys.exit("macOS: launch with mjpython")

    p = Params(LEGSTUDY / "params.yaml")
    base = LegModel(p.variant_names[0], p)
    xml = retune(rbt.build_robot_mjcf(base, step_height=a.wall, step_x=0.105,
                                      with_stair=a.wall > 0, actuators="position",
                                      free_base=True))
    path = SP / "simjoints.xml"; path.write_text(xml)
    m = mujoco.MjModel.from_xml_path(str(path)); d = mujoco.MjData(m)
    back = -0.075 if a.wall > 0 else 0.0
    aid = {n: m.actuator(f"act_{n}").id for n in NAMES}
    jid = {n: m.joint(n).qposadr[0] for n in NAMES}

    # optional: park in the pose a recorded take ended in, so you can pick up
    # authoring exactly where the climb left off
    START = None
    if a.from_pose:
        pj = json.load(open(os.path.expanduser(f"~/cubebot-rl/results/{a.from_pose}")))
        START = ("pose", pj, a.from_pose)
    elif a.from_take:
        import glob
        tk = sorted(glob.glob(os.path.expanduser("~/cubebot-rl/results/take_*.json")),
                    key=os.path.getmtime)[-1]
        tj = json.load(open(tk))
        START = (np.array(tj["frames"][-1]["qpos"]), np.array(tj["frames"][-1]["ctrl"]),
                 tj["joints"], os.path.basename(tk))

    KGc = 0.0980665
    SPECS = {"MG90S": (1.8, 0.10), "SG90": (1.8, 0.10), "SG92R": (2.5, 0.10),
             "MG92B": (3.1, 0.10), "MG996R": (9.4, 0.17)}
    per = {"yaw": a.yaw or a.servo, "pitch": a.pitch or a.servo, "knee": a.knee or a.servo}
    if any(per.values()):
        band = math.radians(8.0)
        for n in NAMES:
            sv = per[n.split("_")[1]]
            if not sv:
                continue
            kg, s60 = SPECS[sv]
            st = kg * KGc; nl = 1.047 / s60
            i = aid[n]; m.actuator_gainprm[i, 0] = st / band
            m.actuator_biasprm[i, 1] = -st / band; m.actuator_biasprm[i, 2] = -st / nl
            m.actuator_forcerange[i] = [-st, st]
        for j in ("yaw", "pitch", "knee"):
            if per[j]:
                print(f"  {j:6s} -> {per[j]:7s} {SPECS[per[j]][0]} kg.cm @4.8 V, "
                      f"{SPECS[per[j]][1]} s/60deg")

    def reset():
        mujoco.mj_resetDataKeyframe(m, d, 0)
        d.qpos[0] += back
        if START is not None and START[0] == "pose":
            pj = START[1]
            d.qpos[2] = pj["body"]["z_mm"] / 1000.0
            h = math.radians(pj["body"]["pitch_deg"]) / 2
            d.qpos[3:7] = [math.cos(h), 0.0, math.sin(h), 0.0]
            for n in NAMES:
                d.qpos[jid[n]] = math.radians(pj["angles_deg"][n])
                d.ctrl[aid[n]] = math.radians(pj["commanded_deg"][n])
        elif START is not None:
            d.qpos[:] = START[0]
            for n in NAMES:
                d.ctrl[aid[n]] = float(START[1][START[2].index(n)])
        mujoco.mj_forward(m, d)

    hip = base.p["kinematics.hip_mount_xyz"]
    _, _, fz = base.neutral_foot_position()
    z0 = -(hip[2] + fz - base.foot_radius)
    gait = Crawl(base, z0)
    r = rbt.Robot(path, base)
    r.m, r.d = m, d                       # share the live model/data
    driving = False

    reset()
    SP.mkdir(parents=True, exist_ok=True)
    seed = {n: math.degrees(float(d.ctrl[aid[n]])) for n in NAMES}
    CMD.write_text(json.dumps({"seq": 0, "targets_deg": seed,
                               "recording": False, "save": False, "reset": False,
                               "drive": [0, 0, 0], "gait_hz": 0.8}))
    if START is not None:
        print(f"parked in {START[2] if START[0]=='pose' else START[3]}")
    tape, seen, msg = [], -1, "ready"
    # --- gear stripping -------------------------------------------------
    # A servo cannot strip its own gears by driving: the motor tops out at stall.
    # Gears fail when something EXTERNAL back-drives the output -- a fall, a
    # landing impact, a leg jammed against the wall. The gear train then has to
    # react a torque far above stall. So the stress proxy is the torque the
    # output shaft actually transmits: what the actuator applies PLUS the
    # constraint (contact) load projected onto that joint.
    dofadr = {n: int(m.joint(n).dofadr[0]) for n in NAMES}
    jstall = {n: float(m.actuator_forcerange[aid[n], 1]) for n in NAMES}
    stripped = set()
    gear_peak = {n: 0.0 for n in NAMES}
    dropped = 0
    last_ctrl = np.zeros(len(NAMES))
    # motion gate: a take of the robot standing still is dead weight in a
    # tracking reward, so only frames where something is actually happening
    # get kept. "Happening" = a command changed, or the robot is still moving.
    CTRL_EPS = 2e-4          # rad, ~0.01 deg of commanded change
    VEL_EPS = 0.015          # rad/s or m/s, below this it has settled
    print(f"robot {p['trials.stance.body_mass_kg']} kg, "
          f"{'wall %.0f mm' % (a.wall*1000) if a.wall else 'flat'}")
    print("now start:  python3 scripts/joint_panel.py\n")

    dt = m.opt.timestep
    with mjv.launch_passive(m, d) as v:
        v.cam.distance, v.cam.azimuth, v.cam.elevation = 0.8, 120, -12
        t0 = time.time(); sim_t = 0.0; last = 0.0
        while v.is_running():
            try:
                cmd = json.loads(CMD.read_text())
            except Exception:
                cmd = None
            if cmd:
                if cmd.get("reset") and cmd["seq"] != seen:
                    reset(); tape.clear(); dropped = 0; msg = "reset"
                    for n in list(stripped):
                        m.actuator_forcerange[aid[n]] = [-jstall[n], jstall[n]]
                    stripped.clear(); gear_peak = {n: 0.0 for n in NAMES}
                if cmd.get("save_pose") and cmd["seq"] != seen:
                    OUT.mkdir(exist_ok=True)
                    pf = OUT / "pose_climb.json"
                    pf.write_text(json.dumps({
                        "note": cmd.get("pose_note", ""),
                        "wall_m": a.wall, "servo": a.servo,
                        "robot_g": float(m.body_mass.sum()*1000),
                        "joints": NAMES,
                        "qpos": [float(x) for x in d.qpos],
                        "ctrl": [float(x) for x in d.ctrl],
                        "angles_deg": {n: math.degrees(float(d.qpos[jid[n]])) for n in NAMES},
                        "body": {"z_mm": float(d.qpos[2])*1000}}, indent=1))
                    msg = f"saved pose -> {pf.name}"
                if cmd.get("save") and cmd["seq"] != seen:
                    OUT.mkdir(exist_ok=True)
                    f = OUT / f"take_{int(a.wall*1000)}mm.json"
                    f.write_text(json.dumps({"wall_m": a.wall, "dt": dt*DECIM,
                                             "joints": NAMES, "frames": tape}))
                    msg = (f"saved {len(tape)} frames -> {f.name} "
                           f"({dropped} idle frames dropped)")
                seen = cmd["seq"]
                dv = cmd.get("drive", [0, 0, 0])
                gait.freq = float(cmd.get("gait_hz", 0.8))
                if any(dv):
                    if not driving:      # entering drive: start the gait here
                        gait.reset(float(d.qpos[0]), float(d.qpos[1]))
                        driving = True
                    pose, yaw, feet, _ = gait.update(dt * DECIM, *dv)
                    try:
                        qq = gait.ik(r, pose, yaw, feet)
                        for lg in LEGS:
                            for k, j in enumerate(JOINTS):
                                n = f"{lg}_{j}"
                                lo, hi = m.actuator_ctrlrange[aid[n]]
                                d.ctrl[aid[n]] = float(np.clip(qq[lg][k], lo, hi))
                        msg = "driving"
                    except ValueError:
                        msg = "gait IK unreachable"
                else:
                    driving = False
                    for n in NAMES:
                        qd = math.radians(float(cmd["targets_deg"].get(n, 0.0)))
                        lo, hi = m.actuator_ctrlrange[aid[n]]
                        d.ctrl[aid[n]] = float(np.clip(qd, lo, hi))

            for _ in range(DECIM):
                mujoco.mj_step(m, d); sim_t += dt
                if a.strip_factor > 0:
                    for n in NAMES:
                        if n in stripped:
                            continue
                        k = dofadr[n]
                        tq = abs(float(d.qfrc_actuator[k]) + float(d.qfrc_constraint[k]))
                        if tq > gear_peak[n]:
                            gear_peak[n] = tq
                        if tq > a.strip_factor * jstall[n]:
                            stripped.add(n)
                            m.actuator_forcerange[aid[n]] = [-1e-6, 1e-6]
                            msg = (f"GEAR STRIPPED: {n} saw {tq:.3f} N.m "
                                   f"= {tq/jstall[n]:.1f}x stall")
                            print("\n  *** " + msg + " -- that joint is now free ***")
            if cmd and cmd.get("recording"):
                cnow = np.array([d.ctrl[aid[n]] for n in NAMES])
                cmd_moved = float(np.abs(cnow - last_ctrl).max()) > CTRL_EPS
                still_moving = float(np.abs(d.qvel).max()) > VEL_EPS
                if cmd_moved or still_moving:
                    tape.append({"t": round(sim_t, 4),
                                 "qpos": [round(float(x), 5) for x in d.qpos],
                                 "ctrl": [round(float(x), 5) for x in d.ctrl]})
                    last_ctrl = cnow
                else:
                    dropped += 1

            v.cam.lookat[:] = [float(d.qpos[0]), float(d.qpos[1]), 0.06]
            v.sync()

            now = time.time()
            if now - last > 0.1:
                last = now
                use = [max(abs(float(d.actuator_force[aid[f"{lg}_{j}"]]))
                           for lg in LEGS) / STALL[j] * 100 for j in JOINTS]
                nc = sum(1 for i in range(d.ncon)
                         if "foot" in str(mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM,
                                                            d.contact[i].geom1))
                         or "foot" in str(mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM,
                                                            d.contact[i].geom2)))
                w, qx, qy, qz = d.qpos[3:7]
                pitch = math.degrees(math.asin(max(-1, min(1, 2*(w*qy - qz*qx)))))
                st = {"actual_deg": {n: math.degrees(float(d.qpos[jid[n]])) for n in NAMES},
                      "z_mm": float(d.qpos[2])*1000, "pitch_deg": pitch,
                      "contacts": nc, "use": use, "frames": len(tape),
                      "dropped": dropped, "msg": msg,
                      "servo": {j: (per[j] or "params") for j in JOINTS},
                      "stall": {j: float(m.actuator_forcerange[aid[f"FL_{j}"], 1]) for j in JOINTS},
                      "stripped": sorted(stripped),
                      "gear_worst": (max(gear_peak.items(), key=lambda kv: kv[1] / jstall[kv[0]])
                                     if a.strip_factor > 0 else None),
                      "gear_worst_x": (max(gear_peak[n] / jstall[n] for n in NAMES)
                                       if a.strip_factor > 0 else 0.0)}
                tmp = STATE.with_suffix(".tmp")
                tmp.write_text(json.dumps(st)); os.replace(tmp, STATE)
            lag = t0 + sim_t - time.time()
            if lag > 0:
                time.sleep(lag)


if __name__ == "__main__":
    main()

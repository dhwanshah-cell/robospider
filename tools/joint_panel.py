#!/usr/bin/env python3
"""Joint control panel - the window you drive the robot from.

Runs as its OWN process (plain python3, tkinter). macOS will not let tkinter and
the MuJoCo viewer share a main thread, so this talks to the simulator through two
small JSON files in the scratchpad:

    cmd.json    <- written here: commanded joint angles + flags
    state.json  -> written by the sim: actual angles, torque, contacts, frames

Start the simulator first (scripts/sim_joints.py), then this.

Features
  * every joint gets - / + press-and-hold buttons, moving at the rate you set
  * tick any set of joints and drive them together with the SELECTED - / +
  * LINK builds a named group with a per-member sign, so "both rear knees, same
    direction" or "mirror the front legs" is one control
  * recording runs continuously while armed; SAVE writes the whole take
"""
from __future__ import annotations
import json, math, os, tkinter as tk
from pathlib import Path
import os, tempfile
from tkinter import ttk

SP = Path(os.environ.get("CUBEBOT_RUNTIME", Path(tempfile.gettempdir())/"cubebot"))
CMD, STATE = SP / "cmd.json", SP / "state.json"
LEGS = ("FL", "FR", "BL", "BR")
JOINTS = ("yaw", "pitch", "knee")
NAMES = [f"{lg}_{j}" for lg in LEGS for j in JOINTS]
LIMITS = {"yaw": 91.7, "pitch": 80.2, "knee": 126.1}
FEMUR, TIBIA = 48.0, 78.82        # mm, verified against the MJCF
LOCKS = ("free", "shin angle", "foot height")
SERVO = {"yaw": "SG90", "pitch": "MG996R", "knee": "MG90S"}


class Panel:
    def __init__(self, root):
        self.root = root
        root.title("CubeBot - joint control")
        self.target = {n: 0.0 for n in NAMES}          # degrees
        self.sel = {n: tk.BooleanVar(value=False) for n in NAMES}
        self.groups: list[dict] = []
        self.rate = tk.DoubleVar(value=25.0)           # deg/s
        self.drive = [0.0, 0.0, 0.0]                   # vx, vy, wz
        self.gait_hz = tk.DoubleVar(value=0.8)
        self.drv_lbl = None
        # per-leg compensation: drive the femur and let the knee hold something
        # fixed relative to the ground. Both are exact -- one constraint, one
        # free joint -- and verified against MuJoCo forward kinematics.
        self.lock = {lg: tk.StringVar(value="free") for lg in LEGS}
        self.recording = tk.BooleanVar(value=True)
        self._held = None
        self._seq = 0
        self._drop_ref = {}
        self._adopted = False
        self.actual = {}
        self.status = "waiting for simulator..."
        self._build()
        self._tick()
        self._poll_state()

    # ---------- ui ----------
    def _build(self):
        top = ttk.Frame(self.root, padding=6); top.grid(row=0, column=0, sticky="ew")
        ttk.Label(top, text="rate deg/s").grid(row=0, column=0)
        ttk.Spinbox(top, from_=1, to=200, increment=5, width=5,
                    textvariable=self.rate).grid(row=0, column=1, padx=(2, 12))
        ttk.Checkbutton(top, text="REC", variable=self.recording,
                        command=self._push).grid(row=0, column=2, padx=4)
        ttk.Button(top, text="Save take", command=lambda: self._push(save=True)
                   ).grid(row=0, column=3, padx=4)
        ttk.Button(top, text="Reset pose", command=self._reset).grid(row=0, column=4, padx=4)
        ttk.Button(top, text="Zero all", command=self._zero).grid(row=0, column=5, padx=4)

        body = ttk.Frame(self.root, padding=(6, 0)); body.grid(row=1, column=0, sticky="nsew")
        hdr = ("sel", "joint", "servo", "", "", "cmd", "actual", "limit")
        for c, h in enumerate(hdr):
            ttk.Label(body, text=h, font=("", 10, "bold")).grid(row=0, column=c, padx=2)
        self.lbl_cmd, self.lbl_act, self.lbl_servo = {}, {}, {}
        for i, n in enumerate(NAMES, start=1):
            j = n.split("_")[1]
            ttk.Checkbutton(body, variable=self.sel[n]).grid(row=i, column=0)
            ttk.Label(body, text=n, width=10).grid(row=i, column=1, sticky="w")
            lb = ttk.Label(body, text=SERVO[j], width=8, foreground="#666")
            lb.grid(row=i, column=2, sticky="w")
            self.lbl_servo[n] = lb
            self._pm(body, i, 3, [n])
            self.lbl_cmd[n] = ttk.Label(body, text="0.0", width=7)
            self.lbl_cmd[n].grid(row=i, column=5)
            self.lbl_act[n] = ttk.Label(body, text="-", width=7, foreground="#0a6")
            self.lbl_act[n].grid(row=i, column=6)
            ttk.Label(body, text=f"±{LIMITS[j]:.0f}", width=6, foreground="#888"
                      ).grid(row=i, column=7)

        sel = ttk.LabelFrame(self.root, text="selected joints", padding=6)
        sel.grid(row=2, column=0, sticky="ew", padx=6, pady=4)
        self._pm(sel, 0, 0, None)                       # None => whatever is ticked
        ttk.Button(sel, text="LINK selected into a group",
                   command=self._link).grid(row=0, column=2, padx=10)
        ttk.Button(sel, text="clear ticks", command=self._untick).grid(row=0, column=3)

        lk = ttk.LabelFrame(self.root, text="leg lock  (what the knee holds while you drive the pitch)",
                            padding=6)
        lk.grid(row=6, column=0, sticky="ew", padx=6, pady=4)
        for i, lg in enumerate(LEGS):
            ttk.Label(lk, text=lg, width=4).grid(row=0, column=2*i, padx=(8, 2))
            ttk.Combobox(lk, values=LOCKS, textvariable=self.lock[lg], width=11,
                         state="readonly").grid(row=0, column=2*i+1)
        ttk.Button(lk, text="all shin", command=lambda: self._lock_all("shin angle")
                   ).grid(row=1, column=0, columnspan=2, pady=(4,0))
        ttk.Button(lk, text="all foot height", command=lambda: self._lock_all("foot height")
                   ).grid(row=1, column=2, columnspan=2, pady=(4,0))
        ttk.Button(lk, text="all free", command=lambda: self._lock_all("free")
                   ).grid(row=1, column=4, columnspan=2, pady=(4,0))

        dr = ttk.LabelFrame(self.root, text="drive  (standard crawl gait)", padding=6)
        dr.grid(row=3, column=0, sticky="ew", padx=6, pady=4)
        pad = ttk.Frame(dr); pad.grid(row=0, column=0)
        mk = lambda t, r, c, v: ttk.Button(pad, text=t, width=7,
                                           command=lambda: self._drive(v)
                                           ).grid(row=r, column=c, padx=1, pady=1)
        mk("turn L", 0, 0, (0, 0, 1));   mk("FWD", 0, 1, (1, 0, 0));  mk("turn R", 0, 2, (0, 0, -1))
        mk("left",   1, 0, (0, 1, 0));   mk("STOP", 1, 1, (0, 0, 0)); mk("right",  1, 2, (0, -1, 0))
        mk("back",   2, 1, (-1, 0, 0))
        side = ttk.Frame(dr); side.grid(row=0, column=1, padx=14)
        ttk.Label(side, text="gait Hz").grid(row=0, column=0)
        ttk.Spinbox(side, from_=0.2, to=1.4, increment=0.1, width=5,
                    textvariable=self.gait_hz, command=self._push).grid(row=0, column=1)
        ttk.Label(side, text="servo cap ≈0.92 Hz", foreground="#a60").grid(row=1, column=0, columnspan=2)
        self.drv_lbl = ttk.Label(side, text="stopped", foreground="#06a")
        self.drv_lbl.grid(row=2, column=0, columnspan=2, pady=(4, 0))
        ttk.Button(side, text="sync targets from robot",
                   command=self._sync).grid(row=3, column=0, columnspan=2, pady=(4, 0))

        self.gbox = ttk.LabelFrame(self.root, text="groups", padding=6)
        self.gbox.grid(row=4, column=0, sticky="ew", padx=6, pady=4)
        self.slbl = ttk.Label(self.root, text="", padding=6, foreground="#333")
        self.slbl.grid(row=5, column=0, sticky="w")

    def _pm(self, parent, r, c, names):
        for k, (txt, sgn) in enumerate((("−", -1.0), ("+", +1.0))):
            b = ttk.Button(parent, text=txt, width=3)
            b.grid(row=r, column=c + k, padx=1)
            b.bind("<ButtonPress-1>", lambda e, n=names, s=sgn: self._hold(n, s))
            b.bind("<ButtonRelease-1>", lambda e: self._release())

    def _hold(self, names, sgn):
        # remember the foot height each leg had when a drag starts, so the
        # foot-height lock holds THAT value rather than drifting
        self._drop_ref = {lg: self._foot_drop(self.target[f"{lg}_pitch"],
                                              self.target[f"{lg}_knee"]) for lg in LEGS}
        self._held = (names, sgn)

    def _release(self):
        self._held = None

    def _link(self):
        mem = [n for n in NAMES if self.sel[n].get()]
        if len(mem) < 2:
            self.status = "tick at least two joints to link"; return
        g = {"name": "+".join(m.replace("_", "") for m in mem)[:28],
             "members": mem, "sign": {m: 1.0 for m in mem}}
        self.groups.append(g); self._redraw_groups()
        self.status = f"linked {len(mem)} joints"

    def _redraw_groups(self):
        for w in self.gbox.winfo_children():
            w.destroy()
        for gi, g in enumerate(self.groups):
            ttk.Label(self.gbox, text=g["name"], width=30).grid(row=gi, column=0, sticky="w")
            self._pm(self.gbox, gi, 1, g["members"])
            for mi, mem in enumerate(g["members"]):
                b = ttk.Button(self.gbox, text=f"{mem} {'+' if g['sign'][mem]>0 else '−'}",
                               width=11,
                               command=lambda gg=g, mm=mem: self._flip(gg, mm))
                b.grid(row=gi, column=3 + mi, padx=1)
            ttk.Button(self.gbox, text="x", width=2,
                       command=lambda gg=g: self._drop(gg)).grid(row=gi, column=12, padx=6)

    def _lock_all(self, mode):
        for lg in LEGS: self.lock[lg].set(mode)
        self.status = f"leg lock -> {mode}"

    def _foot_drop(self, qp, qk):
        """mm from the pitch axis down to the foot (planar, exact)."""
        return FEMUR*math.sin(math.radians(qp)) + TIBIA*math.cos(math.radians(qp+qk))

    def _apply_lock(self, leg, dpitch):
        """Compensate the knee after the pitch moved by dpitch degrees."""
        mode = self.lock[leg].get()
        if mode == "free" or abs(dpitch) < 1e-9:
            return
        kn = f"{leg}_knee"; pt = f"{leg}_pitch"
        if mode == "shin angle":
            new = self.target[kn] - dpitch            # exact: shin holds its ground angle
        else:
            drop = self._drop_ref.get(leg)
            if drop is None:
                return
            qp = self.target[pt]
            c = (drop - FEMUR*math.sin(math.radians(qp))) / TIBIA
            if abs(c) > 1.0:
                self.status = f"{leg}: foot-height lock out of reach"; return
            new = math.degrees(math.acos(c)) - qp
        self.target[kn] = max(-LIMITS["knee"], min(LIMITS["knee"], new))

    def _drive(self, v):
        self.drive = list(map(float, v))
        moving = any(self.drive)
        if self.drv_lbl:
            names = {(1,0,0):"forward",(-1,0,0):"back",(0,1,0):"left",
                     (0,-1,0):"right",(0,0,1):"turn L",(0,0,-1):"turn R"}
            self.drv_lbl.config(text=names.get(tuple(v), "stopped"))
        if not moving:
            self._sync()          # hand control back with the pose it ended in
        self._push()

    def _sync(self):
        """Copy the robot's ACTUAL angles into the manual targets, so taking over
        after a drive does not snap the legs back to a stale setpoint."""
        if self.actual:
            for n in NAMES:
                if n in self.actual:
                    self.target[n] = float(self.actual[n])
            self.status = "targets synced from robot"
            self._push()

    def _flip(self, g, mem):
        g["sign"][mem] *= -1.0; self._redraw_groups()

    def _drop(self, g):
        self.groups.remove(g); self._redraw_groups()

    def _untick(self):
        for n in NAMES: self.sel[n].set(False)

    def _zero(self):
        for n in NAMES: self.target[n] = 0.0
        self._push()

    def _reset(self):
        self._zero(); self._push(reset=True)

    # ---------- loop ----------
    def _tick(self):
        dt = 0.04
        if self._held:
            names, sgn = self._held
            step = self.rate.get() * dt * sgn
            if names is None:
                names = [n for n in NAMES if self.sel[n].get()]
                signs = {n: 1.0 for n in names}
            else:
                g = next((g for g in self.groups
                          if g["members"] == names), None)
                signs = g["sign"] if g else {n: 1.0 for n in names}
            for n in names:
                lim = LIMITS[n.split("_")[1]]
                before = self.target[n]
                self.target[n] = max(-lim, min(lim, before + step * signs.get(n, 1.0)))
                if n.endswith("_pitch"):
                    self._apply_lock(n.split("_")[0], self.target[n] - before)
            self._push()
        for n in NAMES:
            self.lbl_cmd[n].config(text=f"{self.target[n]:+.1f}")
        self.root.after(int(dt * 1000), self._tick)

    def _push(self, save=False, reset=False):
        self._seq += 1
        payload = {"seq": self._seq,
                   "targets_deg": self.target,
                   "drive": self.drive,
                   "gait_hz": float(self.gait_hz.get()),
                   "recording": bool(self.recording.get()),
                   "save": save, "reset": reset}
        tmp = CMD.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload))
        os.replace(tmp, CMD)

    def _poll_state(self):
        try:
            st = json.loads(STATE.read_text())
            self.actual = st.get("actual_deg", {})
            sv = st.get("servo") or {}
            for n in NAMES:                      # label what is actually fitted
                j = n.split("_")[1]
                if sv.get(j) and self.lbl_servo.get(n):
                    self.lbl_servo[n].config(text=sv[j])
            if not self._adopted and self.actual:
                # never yank the robot to zero just because a panel connected
                for n in NAMES:
                    if n in self.actual:
                        self.target[n] = float(self.actual[n])
                self._adopted = True
                self.status = "adopted the robot's current pose"
            for n in NAMES:
                if n in self.actual:
                    self.lbl_act[n].config(text=f"{self.actual[n]:+.1f}")
            self.slbl.config(
                text=f"body z={st.get('z_mm',0):.0f} mm  pitch={st.get('pitch_deg',0):+.0f}°  "
                     f"contacts={st.get('contacts',0)}  "
                     f"torque yaw/pitch/knee = {st.get('use',[0,0,0])[0]:.0f}/"
                     f"{st.get('use',[0,0,0])[1]:.0f}/{st.get('use',[0,0,0])[2]:.0f}%  "
                     f"frames={st.get('frames',0)} (idle dropped {st.get('dropped',0)})   "
                     f"gear {st.get('gear_worst_x',0):.1f}x"
                     + (f"  STRIPPED:{','.join(st.get('stripped',[]))}" if st.get('stripped') else "")
                     + f"   {st.get('msg','')}   {self.status}")
        except Exception:
            self.slbl.config(text=f"waiting for simulator...   {self.status}")
        self.root.after(120, self._poll_state)


if __name__ == "__main__":
    SP.mkdir(parents=True, exist_ok=True)
    root = tk.Tk()
    Panel(root)
    root.mainloop()

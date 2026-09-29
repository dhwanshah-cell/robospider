#!/usr/bin/env python3
"""Drive the hexapod's USC-32 servo controller from a laptop over USB serial.

Same kinematics and tripod gait as the Android app (android/). Paste the app's
"For python/hexapod.py" calibration block over the settings below.

    pip install pyserial
    python python/hexapod.py --port /dev/ttyUSB0      # Windows: --port COM5
    python python/hexapod.py --dry-run                # print commands only

Commands: w/s forward/back, a/d left/right, q/e turn, then an optional number of
cycles (e.g. "w 4"); "stand", "center", "quit".
"""
import argparse
import math
import sys
import time

# ---- Calibration: replace with the block the app shows (long-press to copy) ----
COXA, FEMUR, TIBIA = 30.0, 85.0, 90.0
STRIDE = 60.0
# channels per leg (coxa, femur, tibia)
LEGS = {
    "RF": (1, 2, 3), "RM": (4, 5, 6), "RR": (7, 8, 9),
    "LF": (10, 11, 12), "LM": (13, 14, 15), "LR": (16, 17, 18),
}
DIR = {"RF": (1, 1, 1), "RM": (1, 1, 1), "RR": (1, 1, 1), "LF": (1, -1, 1), "LM": (1, -1, 1), "LR": (1, -1, 1)}
TRIM = {"RF": (0, 0, 0), "RM": (0, 0, 0), "RR": (0, 0, 0), "LF": (0, 0, 0), "LM": (0, 0, 0), "LR": (0, 0, 0)}
# ---------------------------------------------------------------------------------

MOUNT_DEG = {"RF": -45, "RM": -90, "RR": -135, "LF": 45, "LM": 90, "LR": 135}
PHASE_OFFSET = {"RF": 0.0, "RR": 0.0, "LM": 0.0, "RM": 0.5, "LF": 0.5, "LR": 0.5}
MOUNT_RADIUS = 60.0
US_PER_DEG = 2000.0 / 180.0
MIN_US, MAX_US = 0, 5000


def ik(x, y, z):
    """Joint angles (deg) for a foot at x, y, z in the leg frame, or None if out of reach."""
    coxa = math.atan2(y, x)
    r = math.hypot(x, y) - COXA
    d = math.hypot(r, z)
    if d > FEMUR + TIBIA - 0.5 or d < abs(FEMUR - TIBIA) + 0.5:
        return None
    clamp = lambda v: max(-1.0, min(1.0, v))
    femur = math.atan2(z, r) + math.acos(clamp((FEMUR**2 + d * d - TIBIA**2) / (2 * FEMUR * d)))
    knee = math.acos(clamp((FEMUR**2 + TIBIA**2 - d * d) / (2 * FEMUR * TIBIA)))
    return math.degrees(coxa), math.degrees(femur), math.degrees(knee) - 90.0


def pose(fwd=0.0, left=0.0, turn=0.0, phase=0.0, previous=None):
    """{channel: pulse} for all 18 servos at gait phase 0..1."""
    out = dict(previous or {})
    reach = COXA + FEMUR
    lift = max(15.0, min(40.0, 0.3 * TIBIA))
    half = STRIDE / 2
    max_turn = half / (MOUNT_RADIUS + reach)
    norm = max(1.0, math.hypot(fwd, left))
    moving = fwd or left or turn
    for leg, chans in LEGS.items():
        a = math.radians(MOUNT_DEG[leg])
        mx, my = MOUNT_RADIUS * math.cos(a), MOUNT_RADIUS * math.sin(a)
        nx, ny = mx + reach * math.cos(a), my + reach * math.sin(a)
        s, up = 0.0, 0.0
        if moving:
            t = (phase + PHASE_OFFSET[leg]) % 1.0
            if t < 0.5:
                s, up = -1 + 4 * t, lift * math.sin(math.pi * 2 * t)
            else:
                s = 1 - 4 * (t - 0.5)
        th = s * turn * max_turn
        fx = nx * math.cos(th) - ny * math.sin(th) + s * half * fwd / norm - mx
        fy = nx * math.sin(th) + ny * math.cos(th) + s * half * left / norm - my
        lx = fx * math.cos(a) + fy * math.sin(a)
        ly = -fx * math.sin(a) + fy * math.cos(a)
        angles = ik(lx, ly, -TIBIA + up)
        if angles is None:
            continue
        for j, ch in enumerate(chans):
            us = 1500 + DIR[leg][j] * angles[j] * US_PER_DEG + TRIM[leg][j]
            out[ch] = int(round(max(MIN_US, min(MAX_US, us))))
    return out


class Usc32:
    def __init__(self, port, baud, dry_run):
        self.ser = None
        self.baud = baud
        if not dry_run:
            import serial  # pyserial

            self.ser = serial.Serial(port, baud, timeout=1)

    def send(self, pulses, ms):
        line = "".join(f"#{ch}P{us}" for ch, us in sorted(pulses.items())) + f"T{ms}"
        if self.ser:
            self.ser.write((line + "\r\n").encode("ascii"))
        else:
            print(line)

    def tick_ms(self):
        return max(60, round((18 * 11 + 8) * 10_000 / self.baud * 1.25))


def walk(link, cycles, **drive):
    tick = link.tick_ms()
    cycle_ms = max(1000.0, tick * 8.0)
    steps = int(cycles * cycle_ms / tick)
    p = pose()
    for k in range(steps):
        p = pose(phase=(k * tick / cycle_ms) % 1.0, previous=p, **drive)
        link.send(p, tick + 20)
        time.sleep(tick / 1000)
    link.send(pose(), 300)


MOVES = {
    "w": dict(fwd=1), "s": dict(fwd=-1), "a": dict(left=1), "d": dict(left=-1),
    "q": dict(turn=1), "e": dict(turn=-1),
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", default="/dev/ttyUSB0")
    ap.add_argument("--baud", type=int, default=9600)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    link = Usc32(args.port, args.baud, args.dry_run)
    link.send(pose(), 500)
    print("w/s/a/d/q/e [cycles], stand, center, quit")
    for raw in sys.stdin if not sys.stdin.isatty() else iter(lambda: input("> "), None):
        cmd = raw.split()
        if not cmd:
            continue
        if cmd[0] in ("quit", "exit"):
            break
        if cmd[0] == "stand":
            link.send(pose(), 500)
        elif cmd[0] == "center":
            link.send({ch: 1500 for chans in LEGS.values() for ch in chans}, 500)
        elif cmd[0] in MOVES:
            walk(link, float(cmd[1]) if len(cmd) > 1 else 2, **MOVES[cmd[0]])
        else:
            print("?", cmd[0])


if __name__ == "__main__":
    main()

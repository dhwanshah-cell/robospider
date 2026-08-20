"""Omnidirectional crawl gait generator.

Generalises the validated forward crawl (duty 0.75, one leg swinging at a time,
feet pinned in world through stance) to any heading plus turning.

Turning needs care: legstudy's BodyPose carries only x/y/z/roll/pitch -- there is
no yaw. Rather than hack the dataclass, the body yaw is applied by pre-rotating
the foot target into the body's yawed frame before calling leg_ik, which is
mathematically identical and leaves the leg study untouched.
"""
from __future__ import annotations
import math
import numpy as np

# Swing blend profiles. The 3rd derivative of joint angle is JERK; a profile
# that only zeroes VELOCITY at the endpoints (cosine, cubic smoothstep) still
# steps ACCELERATION discontinuously there, which is an impulse of jerk the
# gearbox and the servo current both feel. The quintic zeroes velocity AND
# acceleration at both ends -- the classic minimum-jerk trajectory.
BLENDS = {
    "linear":    lambda s: s,
    "cubic":     lambda s: 3*s**2 - 2*s**3,                 # C1
    "cosine":    lambda s: 0.5 - 0.5*math.cos(math.pi*s),   # C1
    "quintic":   lambda s: 10*s**3 - 15*s**4 + 6*s**5,      # C2, min-jerk
}
from legstudy import robot as rbt

LEGS = rbt.LEGS
PHASE = {"FL": 0.0, "BR": 0.25, "FR": 0.5, "BL": 0.75}   # crawl order
DUTY = 0.75


def _rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


class Crawl:
    """Body path + foot targets for a commanded (vx, vy, wz)."""

    def __init__(self, base, z0, step=0.055, height=0.028, freq=0.8, blend='cosine'):
        self.base = base
        self.nf = {lg: np.array([*rbt.neutral_footholds(base)[lg][:2], 0.0])
                   for lg in LEGS}
        self.R = base.foot_radius
        self.z0 = z0
        self.step, self.height, self.freq = step, height, freq
        self.blend = BLENDS[blend] if isinstance(blend, str) else blend
        self.reset()

    def reset(self, x=0.0, y=0.0, yaw=0.0):
        self.p = np.array([x, y], dtype=float)
        self.yaw = yaw
        self.t = 0.0
        self.plant = {lg: self._nominal(lg, self.p, self.yaw) for lg in LEGS}
        self.prev_ph = {lg: 0.0 for lg in LEGS}

    def _nominal(self, lg, p, yaw):
        w = _rz(yaw) @ self.nf[lg]
        return np.array([p[0] + w[0], p[1] + w[1], self.R])

    def update(self, dt, vx, vy, wz):
        """Advance the body and return (desired pose, yaw, foot targets, stance)."""
        moving = (vx, vy, wz) != (0.0, 0.0, 0.0)
        T = 1.0 / self.freq
        v = self.step / T                      # one step per cycle
        if moving:
            head = np.array([vx, vy], dtype=float)
            n = np.linalg.norm(head)
            if n > 1e-9:
                head = head / n
                self.p = self.p + _rz(self.yaw)[:2, :2] @ head * v * dt
            # NOTE the sign: rotating the footholds one way drags the planted
            # body the other. Measured, not assumed -- wz=+1 must yaw the body
            # CCW (left), so the foothold rotation is negated.
            self.yaw -= wz * (self.step / (0.11 * T)) * dt
            self.t += dt

        feet, stance = {}, {}
        u = np.array([vx, vy], dtype=float)
        nu = np.linalg.norm(u)
        u = u / nu if nu > 1e-9 else np.zeros(2)
        lead = _rz(self.yaw)[:2, :2] @ (u * v * T * DUTY * 0.5)   # land half a stance ahead

        for lg in LEGS:
            if not moving:
                feet[lg] = self.plant[lg]; stance[lg] = True
                continue
            ph = ((self.t / T) - PHASE[lg]) % 1.0
            # TOUCHDOWN is an event, not a sample: detecting it by "s > 0.995"
            # means a 1.6 ms window polled every 20 ms, which almost never fires
            # and leaves the foot planted while the body walks away from it.
            if self.prev_ph[lg] >= DUTY and ph < DUTY:
                self.plant[lg] = self._nominal(lg, self.p + lead, self.yaw)
            self.prev_ph[lg] = ph

            if ph < DUTY:
                feet[lg] = self.plant[lg]; stance[lg] = True
            else:
                s_ = (ph - DUTY) / (1.0 - DUTY)
                nxt = self._nominal(lg, self.p + lead, self.yaw - wz * 0.25)
                a = self.blend(s_)
                f = self.plant[lg] * (1 - a) + nxt * a
                # lift arc: sin gives zero vertical velocity at both ends
                f[2] = self.R + self.height * math.sin(math.pi * s_)
                feet[lg] = f; stance[lg] = False

        pose = rbt.BodyPose(x=float(self.p[0]), y=float(self.p[1]), z=self.z0)
        return pose, self.yaw, feet, stance

    def ik(self, robot, pose, yaw, feet):
        """Joint angles, with body yaw folded into the target."""
        out = {}
        origin = np.array([pose.x, pose.y, pose.z])
        for lg in LEGS:
            tgt = origin + _rz(-yaw) @ (np.asarray(feet[lg]) - origin)
            out[lg] = robot.leg_ik(pose, lg, tgt)
        return out

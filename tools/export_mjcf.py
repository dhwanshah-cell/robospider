"""Phase 0 - export an MJX-ready CubeBot MJCF from the leg-study parameters.

The leg study builds a 12-DOF MJCF tuned for stiff, quasi-static torque
measurement: 10 kHz timestep, `implicit` integrator, no sensors. None of that
survives contact with an RL training loop, so this module regenerates the model
and retunes it:

  * timestep 1e-4 -> 2e-3, integrator `implicit` -> `implicitfast`
    (MJX supports Euler / implicitfast / RK4 only -- `implicit` would not load
    under MJX at all)
  * adds the sensor suite the policy observes: IMU framequat + gyro +
    accelerometer on the trunk, and one touch sensor per foot
  * adds contact friction and MJX-friendly solver settings

Everything upstream of this (link masses, joint limits, servo gains) still comes
from ~/cubebot-legstudy/params.yaml, so the RL model and the torque study can
never silently disagree about the hardware.
"""
from __future__ import annotations

import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

LEGSTUDY = Path.home() / "cubebot-legstudy"
OUT = Path(__file__).resolve().parent.parent / "assets" / "cubebot_12dof.xml"

# RL physics. 2 ms physics x 10 substeps = 50 Hz control, matching the plan's
# action rate and the MG90S's ~50 Hz useful command rate.
TIMESTEP = 0.002
DECIMATION = 10
FEET = ["FL", "FR", "BL", "BR"]

# Per-joint servo, 4.8 V column only. The leg study emits ONE global <position>
# default, which silently gave all twelve joints the shoulder servo's limit --
# a yaw joint that can pull 0.92 N.m is a fiction the policy would exploit.
# joint -> (name, stall N.m, no-load rad/s)
SERVO = {
    "yaw":   ("SG90",   1.8 * 0.0980665, 1.047 / 0.10),
    "pitch": ("MG996R", 9.4 * 0.0980665, 1.047 / 0.17),
    "knee":  ("MG90S",  1.8 * 0.0980665, 1.047 / 0.10),
}
BAND_RAD = math.radians(8.0)          # servo.proportional_band_deg


def _leg_study_mjcf() -> str:
    sys.path.insert(0, str(LEGSTUDY))
    from legstudy.config import LegModel, Params
    from legstudy import robot as rbt

    p = Params(LEGSTUDY / "params.yaml")
    base = LegModel(p.variant_names[0], p)
    return rbt.build_robot_mjcf(base, actuators="position", free_base=True,
                                with_stair=False), p


def retune(xml: str) -> str:
    root = ET.fromstring(xml)

    # --- physics -----------------------------------------------------
    opt = root.find("option")
    opt.set("timestep", str(TIMESTEP))
    opt.set("integrator", "implicitfast")   # MJX-compatible
    opt.set("solver", "Newton")
    opt.set("iterations", "4")
    opt.set("ls_iterations", "8")

    # --- offscreen framebuffer (needed to render video frames) --------
    vis = root.find("visual")
    if vis is None:
        vis = ET.SubElement(root, "visual")
    g = vis.find("global")
    if g is None:
        g = ET.SubElement(vis, "global")
    g.set("offwidth", "1920")
    g.set("offheight", "1080")

    # --- the trunk MUST collide -------------------------------------
    # The leg study builds trunk_col with contype=0/conaffinity=0 because its
    # study only ever loaded the legs. Left alone, the body passes straight
    # through a step and any climb "succeeds" for the wrong reason.
    trunk_geom = root.find(".//geom[@name='trunk_col']")
    trunk_geom.set("contype", "1")
    trunk_geom.set("conaffinity", "1")
    # ...but the trunk box geometrically encloses the hip brackets and clips the
    # femur capsules, so switching it on alone spawns permanent self-contacts.
    # Exclude the leg bodies explicitly: trunk-vs-world stays live, which is the
    # only thing we actually need.
    contact = root.find("contact")
    if contact is None:
        contact = ET.SubElement(root, "contact")
    for leg in FEET:
        for part in ("hip", "femur", "tibia"):
            ET.SubElement(contact, "exclude", body1="trunk", body2=f"{leg}_{part}")

    # --- contact model ------------------------------------------------
    default = root.find("default")
    geom_def = default.find("geom")
    if geom_def is None:
        geom_def = ET.SubElement(default, "geom")
    geom_def.set("friction", "0.8 0.02 0.001")
    geom_def.set("condim", "3")
    geom_def.set("solref", "0.008 1")

    # --- per-joint actuator limits and gains -------------------------
    for act in root.find("actuator"):
        j = act.get("name").rsplit("_", 1)[1]          # act_FL_pitch -> pitch
        nm, stall, w_nl = SERVO[j]
        act.set("forcerange", f"{-stall:.6g} {stall:.6g}")
        act.set("kp", f"{stall / BAND_RAD:.6g}")
        act.set("kv", f"{stall / w_nl:.6g}")

    # --- BOM-accurate trunk inertial ---------------------------------
    # The leg study lumps the whole trunk into one uniform box: right mass,
    # wrong inertia and wrong CoM. Replace it with the real component layout.
    from .mass_model import trunk_inertial, COMPONENTS
    trunk = root.find(".//body[@name='trunk']")
    total, com, I = trunk_inertial()

    col = trunk.find("geom[@name='trunk_col']")
    col.set("mass", "0")                       # inertia now comes from <inertial>
    inertial = ET.Element("inertial")
    inertial.set("pos", " ".join(f"{v:.9g}" for v in com))
    inertial.set("mass", f"{total:.9g}")
    # MuJoCo fullinertia order: ixx iyy izz ixy ixz iyz
    inertial.set("fullinertia", " ".join(f"{v:.9g}" for v in
                 [I[0,0], I[1,1], I[2,2], I[0,1], I[0,2], I[1,2]]))
    trunk.insert(0, inertial)

    # visual-only component boxes (group 4) so the layout is inspectable
    for name, g, pos_mm, src, size_mm in COMPONENTS:
        if g < 3.0:
            continue
        ET.SubElement(trunk, "geom", name=f"cmp_{name}", type="box",
                      size=" ".join(f"{v/2000:.5g}" for v in size_mm),
                      pos=" ".join(f"{v/1000:.5g}" for v in pos_mm),
                      group="4", mass="0", contype="0", conaffinity="0",
                      rgba="0.92 0.41 0.20 0.45")

    # --- IMU site on the trunk ---------------------------------------
    if trunk.find("site[@name='imu']") is None:
        ET.SubElement(trunk, "site", name="imu", pos="0 0 0",
                      size="0.008", rgba="0 1 0 0.6")

    # --- foot sites must enclose the ball so touch registers ----------
    for leg in FEET:
        site = root.find(f".//site[@name='{leg}_foot_site']")
        site.set("size", "0.0095")          # foot ball is r=8.5mm

    # --- sensors the policy observes ---------------------------------
    sensor = ET.SubElement(root, "sensor")
    ET.SubElement(sensor, "framequat", name="imu_quat",
                  objtype="site", objname="imu")
    ET.SubElement(sensor, "gyro", name="imu_gyro", site="imu")
    ET.SubElement(sensor, "accelerometer", name="imu_acc", site="imu")
    ET.SubElement(sensor, "velocimeter", name="trunk_vel", site="imu")
    for leg in FEET:
        ET.SubElement(sensor, "touch", name=f"{leg}_touch",
                      site=f"{leg}_foot_site")

    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode")


def main() -> None:
    xml, p = _leg_study_mjcf()
    out = retune(xml)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(out)
    print(f"wrote {OUT}")
    print(f"  servo      : {p['servo.model']}")
    print(f"  robot mass : {p['trials.stance.body_mass_kg']} kg")
    print(f"  timestep   : {TIMESTEP}s x {DECIMATION} = "
          f"{1/(TIMESTEP*DECIMATION):.0f} Hz control")
    from .mass_model import trunk_inertial
    t, com, I = trunk_inertial()
    print(f"  trunk      : {t*1000:.1f} g, CoM ({com[0]*1000:+.1f},"
          f"{com[1]*1000:+.1f},{com[2]*1000:+.1f}) mm from case centre")


if __name__ == "__main__":
    main()

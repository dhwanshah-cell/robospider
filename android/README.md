# Hexapod SAR — Android controller for the USC-32

Phone app that drives the hexapod's 18 servos through a **USC-32** servo controller
over a USB-OTG cable, walks it with a tripod gait, and runs a simple search-and-rescue
patrol that looks and listens for people and sends alerts through [ntfy](https://ntfy.sh).

## Install

1. Get the APK: from this repo's **Actions** tab (artifact `hexapod-sar-apk`), or build it:
   `cd android && ./gradlew assembleDebug` → `app/build/outputs/apk/debug/app-debug.apk`.
2. With the phone plugged into a computer (USB debugging on):
   `adb install -r app-debug.apk`.
   Or copy the APK to the phone and tap it (allow "install unknown apps").

## Wiring

USC-32 channels, each leg in coxa / femur / tibia order:

| Leg | Channels |
|---|---|
| RF right front | S1 S2 S3 |
| RM right middle | S4 S5 S6 |
| RR right rear | S7 S8 S9 |
| LF left front | S10 S11 S12 |
| LM left middle | S13 S14 S15 |
| LR left rear | S16 S17 S18 |

Phone → USB-OTG adapter → USC-32 USB port. Plugging it in offers to open the app;
otherwise tap **Connect**. Pick the baud rate your board uses (9600 or 115200).
Commands are the USC-32 text protocol, e.g. `#1P1500#2P1600T200`.

## Using it

- **Status card**: USB state, baud, and the last commands sent. With no board plugged
  in the app runs *dry*: every command is only shown.
- **Search & rescue**: camera person detector (EfficientDet-Lite0) and sound classifier
  (YAMNet), both on the phone. **Start patrol** walks forward / turns at random; when it
  sees a person or hears speech, shouting, crying, knocking etc. it stops and sends an
  alert with a photo and the phone's location. Rescuers install the ntfy app and
  subscribe to the topic shown. Alerts that can't be sent are saved and resent later.
- **Hold to walk**: tripod gait while held, stands on release. **Stand** is the IK
  neutral pose; **Center all** sends 1500 µs to every servo.
- **Self-level**: with the phone upright on the robot (rear camera forward), leans the
  body against the tilt the phone measures.
- **Leg cards**: every servo, 0–5000 µs slider, ±10 µs, 1500, direction flip and trim.
- **Calibration**: link lengths and step length, Save / Reset, and a block to paste into
  [`python/hexapod.py`](../python/hexapod.py) to drive the robot from a laptop.

Calibrating: **Center all** → fit the horns (coxa straight out, femur level, tibia
straight down) → **Stand**. A joint moving the wrong way: flip its **dir**. Small
offsets: **trim** (≈11 µs per degree). Tap **Save**.

> Most servos only accept roughly 500–2500 µs. The sliders go 0–5000 as asked, but
> pulses outside your servos' range can make them buzz or strain against their stops.

Safety: first runs on a box with the legs in the air and a hand on the power switch.
There is no obstacle sensing, so patrol only in a clear area.

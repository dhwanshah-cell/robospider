package com.robospider.hexapod

import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.acos
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.hypot
import kotlin.math.roundToInt
import kotlin.math.sin
import kotlin.math.sqrt
import kotlin.math.tan

/** Which way the hold-to-walk pad is pushing: forward/left in [-1, 1], turn > 0 is counter-clockwise. */
data class Drive(val fwd: Double = 0.0, val left: Double = 0.0, val turn: Double = 0.0) {
    val idle get() = fwd == 0.0 && left == 0.0 && turn == 0.0

    companion object {
        val FWD = Drive(fwd = 1.0)
        val BACK = Drive(fwd = -1.0)
        val LEFT = Drive(left = 1.0)
        val RIGHT = Drive(left = -1.0)
        val TURN_L = Drive(turn = 1.0)
        val TURN_R = Drive(turn = -1.0)
    }
}

/**
 * Leg inverse kinematics and a tripod gait.
 *
 * Zero pose (every servo at 1500 + trim) is the calibration pose: coxa straight out,
 * femur level, tibia straight down. Standing uses exactly that pose, so a well-trimmed
 * robot stands with all pulses near 1500.
 */
object Kinematics {
    /** ≈11 µs per degree: 500..2500 µs spans 180°. */
    const val US_PER_DEG = 2000.0 / 180.0

    /** Coxa pivots sit on a circle of this radius around the body centre (mm). */
    private const val MOUNT_RADIUS = 60.0

    // Tripod groups: RF, RR, LM swing together; RM, LF, LR swing together.
    private val PHASE_OFFSET = doubleArrayOf(0.0, 0.5, 0.0, 0.5, 0.0, 0.5)

    private fun rad(d: Double) = d * PI / 180.0
    private fun deg(r: Double) = r * 180.0 / PI

    /** Joint angles in degrees (coxa, femur, tibia) for a foot at (x, y, z) in the leg frame, or null if out of reach. */
    fun ik(x: Double, y: Double, z: Double, c: Calibration): DoubleArray? {
        val lf = c.femur.toDouble()
        val lt = c.tibia.toDouble()
        val coxa = atan2(y, x)
        val r = hypot(x, y) - c.coxa
        val d = hypot(r, z)
        if (d > lf + lt - 0.5 || d < abs(lf - lt) + 0.5) return null
        val femur = atan2(z, r) + acos(((lf * lf + d * d - lt * lt) / (2 * lf * d)).coerceIn(-1.0, 1.0))
        val knee = acos(((lf * lf + lt * lt - d * d) / (2 * lf * lt)).coerceIn(-1.0, 1.0))
        return doubleArrayOf(deg(coxa), deg(femur), deg(knee) - 90.0)
    }

    fun pulse(angleDeg: Double, channelIndex: Int, c: Calibration): Int =
        (1500 + c.dir[channelIndex] * angleDeg * US_PER_DEG + c.trim[channelIndex]).roundToInt().coerceIn(Legs.MIN_US, Legs.MAX_US)

    /**
     * All 18 pulses for gait [phase] (0..1, one full tripod cycle) under [drive].
     * [pitchDeg]/[rollDeg] tilt the body (nose up / left side up) for self-levelling.
     * Legs that can't reach their target keep the pulses from [previous].
     */
    fun pose(
        c: Calibration,
        drive: Drive,
        phase: Double,
        previous: IntArray,
        pitchDeg: Double = 0.0,
        rollDeg: Double = 0.0,
    ): IntArray {
        val out = previous.copyOf()
        val reach = (c.coxa + c.femur).toDouble()
        val height = c.tibia.toDouble()
        val lift = (0.3 * c.tibia).coerceIn(15.0, 40.0)
        val half = c.step / 2.0
        val footRadius = MOUNT_RADIUS + reach
        val maxTurn = half / footRadius
        // Diagonal walking shouldn't take longer strides than straight walking.
        val norm = sqrt(drive.fwd * drive.fwd + drive.left * drive.left).coerceAtLeast(1.0)

        for (leg in 0 until 6) {
            val a = rad(Legs.ALL[leg].mountDeg)
            val mx = MOUNT_RADIUS * cos(a)
            val my = MOUNT_RADIUS * sin(a)
            // Neutral foot in the body frame.
            val nx = mx + reach * cos(a)
            val ny = my + reach * sin(a)

            // s runs -1 → +1 through the swing (foot in the air), +1 → -1 through the stance.
            var s = 0.0
            var up = 0.0
            if (!drive.idle) {
                val t = (phase + PHASE_OFFSET[leg]).mod(1.0)
                if (t < 0.5) {
                    s = -1 + 4 * t
                    up = lift * sin(PI * 2 * t)
                } else {
                    s = 1 - 4 * (t - 0.5)
                }
            }
            val th = s * drive.turn * maxTurn
            var fx = nx * cos(th) - ny * sin(th) + s * half * drive.fwd / norm
            var fy = nx * sin(th) + ny * cos(th) + s * half * drive.left / norm
            // Lower a foot to raise that corner of the body.
            val fz = -height + up - fx * tan(rad(pitchDeg)) - fy * tan(rad(rollDeg))

            // Into the leg frame: origin at the coxa pivot, x straight out.
            fx -= mx
            fy -= my
            val lx = fx * cos(a) + fy * sin(a)
            val ly = -fx * sin(a) + fy * cos(a)

            val angles = ik(lx, ly, fz, c) ?: continue
            for (j in 0 until 3) out[leg * 3 + j] = pulse(angles[j], leg * 3 + j, c)
        }
        return out
    }
}

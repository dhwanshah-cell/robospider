package com.robospider.hexapod

import android.content.Context
import kotlin.random.Random

/** One leg: its name, UI colour, and the direction its coxa points out of the body. */
data class LegInfo(val code: String, val name: String, val color: Long, val mountDeg: Double)

object Legs {
    // Body frame: x forward, y left, angles counter-clockwise from forward.
    val ALL = listOf(
        LegInfo("RF", "Right front", 0xFFFFC53D, -45.0),
        LegInfo("RM", "Right middle", 0xFF22D3EE, -90.0),
        LegInfo("RR", "Right rear", 0xFF22C55E, -135.0),
        LegInfo("LF", "Left front", 0xFFC6E03A, 45.0),
        LegInfo("LM", "Left middle", 0xFFF472B6, 90.0),
        LegInfo("LR", "Left rear", 0xFFC4A1FF, 135.0),
    )
    val JOINTS = listOf("coxa", "femur", "tibia")

    /** Slider and command limits, in µs. */
    const val MIN_US = 0
    const val MAX_US = 5000

}

enum class Gait(val label: String) {
    /** Three legs up at a time: fast. */
    TRIPOD("Tripod"),

    /** One pair up at a time, then the body slides (the old app's gait): slow, four feet always down. */
    CRAWL("Crawl"),
}

/**
 * Everything the Calibration and Walking settings save.
 * dir and trim are per servo: index i = channel S(i+1), whichever leg is wired there.
 */
data class Calibration(
    val coxa: Int = 30,
    val femur: Int = 85,
    val tibia: Int = 90,
    val step: Int = 60,
    val dir: List<Int> = DEFAULT_DIR,
    val trim: List<Int> = List(18) { 0 },
    /** true: S10-12 left front, S16-18 left rear. false: the other way round (the old app's wiring). */
    val leftFrontFirst: Boolean = true,
    val gait: Gait = Gait.CRAWL,
    /** Foot lift during a step, mm. */
    val lift: Int = 25,
    /** One full gait cycle, ms. */
    val cycleMs: Int = 1600,
    /** Counter-turn while walking, tenths of a degree per cycle; + turns left. Fixes drift. */
    val driftTenths: Int = 0,
) {
    companion object {
        // Left-side femurs (S11, S14, S17) are mirrored, so they turn the other way.
        val DEFAULT_DIR = List(18) { i -> if (i >= 9 && i % 3 == 1) -1 else 1 }
    }

    /** Servo index (0..17, = channel - 1) for leg [leg] (index into Legs.ALL), joint [joint] (0..2). */
    fun servo(leg: Int, joint: Int): Int {
        val base = when (leg) {
            3 -> if (leftFrontFirst) 9 else 15 // LF
            5 -> if (leftFrontFirst) 15 else 9 // LR
            else -> leg * 3
        }
        return base + joint
    }

    fun channel(leg: Int, joint: Int) = servo(leg, joint) + 1

    /** Paste-ready settings for python/hexapod.py. */
    fun pythonExport(): String {
        fun tuple(v: List<Int>, leg: Int) = "(${v[servo(leg, 0)]}, ${v[servo(leg, 1)]}, ${v[servo(leg, 2)]})"
        val sb = StringBuilder()
        sb.appendLine("COXA, FEMUR, TIBIA = $coxa.0, $femur.0, $tibia.0")
        sb.appendLine("STRIDE = $step.0")
        sb.appendLine("# channels per leg (coxa, femur, tibia): replace the tuples in LEGS")
        Legs.ALL.forEachIndexed { i, l ->
            sb.appendLine("#   ${l.code}: (${channel(i, 0)}, ${channel(i, 1)}, ${channel(i, 2)})")
        }
        sb.appendLine("DIR = {" + Legs.ALL.indices.joinToString(", ") { "\"${Legs.ALL[it].code}\": ${tuple(dir, it)}" } + "}")
        sb.append("TRIM = {" + Legs.ALL.indices.joinToString(", ") { "\"${Legs.ALL[it].code}\": ${tuple(trim, it)}" } + "}")
        return sb.toString()
    }
}

/** App settings in SharedPreferences. */
class Settings(context: Context) {
    private val prefs = context.getSharedPreferences("hexapod", Context.MODE_PRIVATE)

    fun loadCalibration(): Calibration {
        val d = Calibration()
        fun ints(key: String, def: List<Int>) =
            prefs.getString(key, null)?.split(",")?.mapNotNull { it.trim().toIntOrNull() }
                ?.takeIf { it.size == 18 } ?: def
        return Calibration(
            coxa = prefs.getInt("coxa", d.coxa),
            femur = prefs.getInt("femur", d.femur),
            tibia = prefs.getInt("tibia", d.tibia),
            step = prefs.getInt("step", d.step),
            dir = ints("dir", d.dir),
            trim = ints("trim", d.trim),
            leftFrontFirst = prefs.getBoolean("leftFrontFirst", d.leftFrontFirst),
            gait = runCatching { Gait.valueOf(prefs.getString("gait", null) ?: "") }.getOrDefault(d.gait),
            lift = prefs.getInt("lift", d.lift),
            cycleMs = prefs.getInt("cycleMs", d.cycleMs),
            driftTenths = prefs.getInt("driftTenths", d.driftTenths),
        )
    }

    fun saveCalibration(c: Calibration) {
        prefs.edit()
            .putInt("coxa", c.coxa).putInt("femur", c.femur).putInt("tibia", c.tibia).putInt("step", c.step)
            .putString("dir", c.dir.joinToString(","))
            .putString("trim", c.trim.joinToString(","))
            .putBoolean("leftFrontFirst", c.leftFrontFirst)
            .putString("gait", c.gait.name)
            .putInt("lift", c.lift).putInt("cycleMs", c.cycleMs).putInt("driftTenths", c.driftTenths)
            .apply()
    }

    var baud: Int
        get() = prefs.getInt("baud", 9600)
        set(v) = prefs.edit().putInt("baud", v).apply()

    var ntfyServer: String
        get() = prefs.getString("ntfyServer", null) ?: "https://ntfy.sh"
        set(v) = prefs.edit().putString("ntfyServer", v).apply()

    /** A random topic per install, so strangers don't share it by accident. */
    var ntfyTopic: String
        get() = prefs.getString("ntfyTopic", null) ?: run {
            val chars = "abcdefghijkmnpqrstuvwxyz23456789"
            val t = "hexapod-sar-alert-" + (1..4).map { chars[Random.nextInt(chars.length)] }.joinToString("")
            prefs.edit().putString("ntfyTopic", t).apply()
            t
        }
        set(v) = prefs.edit().putString("ntfyTopic", v).apply()
}

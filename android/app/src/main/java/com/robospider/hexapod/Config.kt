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

    /** USC-32 channel for leg [leg] (0..5), joint [joint] (0..2): S1..S18. */
    fun channel(leg: Int, joint: Int) = leg * 3 + joint + 1
}

/** Everything the Calibration card saves. Index i = channel S(i+1). */
data class Calibration(
    val coxa: Int = 30,
    val femur: Int = 85,
    val tibia: Int = 90,
    val step: Int = 60,
    val dir: List<Int> = DEFAULT_DIR,
    val trim: List<Int> = List(18) { 0 },
) {
    companion object {
        // Left-side femurs are mirrored, so they turn the other way.
        val DEFAULT_DIR = List(6) { leg -> listOf(1, if (leg >= 3) -1 else 1, 1) }.flatten()
    }

    /** Paste-ready settings for python/hexapod.py. */
    fun pythonExport(): String {
        fun tuple(v: List<Int>, leg: Int) = "(${v[leg * 3]}, ${v[leg * 3 + 1]}, ${v[leg * 3 + 2]})"
        val sb = StringBuilder()
        sb.appendLine("COXA, FEMUR, TIBIA = $coxa.0, $femur.0, $tibia.0")
        sb.appendLine("STRIDE = $step.0")
        sb.appendLine("# channels per leg (coxa, femur, tibia): replace the tuples in LEGS")
        Legs.ALL.forEachIndexed { i, l ->
            sb.appendLine("#   ${l.code}: (${Legs.channel(i, 0)}, ${Legs.channel(i, 1)}, ${Legs.channel(i, 2)})")
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
        )
    }

    fun saveCalibration(c: Calibration) {
        prefs.edit()
            .putInt("coxa", c.coxa).putInt("femur", c.femur).putInt("tibia", c.tibia).putInt("step", c.step)
            .putString("dir", c.dir.joinToString(","))
            .putString("trim", c.trim.joinToString(","))
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

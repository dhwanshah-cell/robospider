package com.robospider.hexapod

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class KinematicsTest {
    private val cal = Calibration()
    private val drives = listOf(Drive.FWD, Drive.BACK, Drive.LEFT, Drive.RIGHT, Drive.TURN_L, Drive.TURN_R)

    private fun phases() = (0 until 64).map { it / 64.0 }

    @Test
    fun standingIsTheCalibrationPose() {
        val p = Kinematics.pose(cal, Drive(), 0.0, IntArray(18))
        assertArrayEquals(IntArray(18) { 1500 }, p)
    }

    @Test
    fun trimShiftsTheStandingPulse() {
        val c = cal.copy(trim = List(18) { if (it == 4) -110 else 0 })
        assertEquals(1390, Kinematics.pose(c, Drive(), 0.0, IntArray(18))[4])
    }

    @Test
    fun everyGaitPoseIsReachable() {
        for (gait in Gait.entries) for (d in drives) for (t in phases()) {
            // A zeroed "previous" pose would leak through for any unreachable leg.
            val p = Kinematics.pose(cal.copy(gait = gait), d, t, IntArray(18))
            assertTrue("$gait $d t=$t: ${p.toList()}", p.all { it in 800..2200 })
        }
    }

    @Test
    fun forwardWalkIsMirrorSymmetric() {
        // Walking straight needs each left leg to do exactly the mirror of its right partner
        // when it is at the same point of its own step: coxa angles opposite (pulses sum to 3000,
        // both dir +1), femur angles equal (left dir -1, so pulses also sum to 3000), tibia equal.
        val pairs = listOf(0 to 3, 1 to 4, 2 to 5) // RF/LF, RM/LM, RR/LR
        val crawlSlot = intArrayOf(0, 1, 2, 2, 1, 0)
        for (gait in Gait.entries) {
            val c = cal.copy(gait = gait)
            for ((r, l) in pairs) for (t in phases()) {
                val t2 = when (gait) {
                    Gait.TRIPOD -> (t + 0.5).mod(1.0) // every mirror pair is in opposite tripods
                    Gait.CRAWL -> {
                        val seg = t * 4
                        when {
                            seg >= 3 -> t // body shift: all legs together
                            seg >= crawlSlot[r] && seg < crawlSlot[r] + 1 -> t + (crawlSlot[l] - crawlSlot[r]) / 4.0
                            else -> continue // the right leg is waiting; its partner may not be
                        }
                    }
                }
                val right = Kinematics.pose(c, Drive.FWD, t, IntArray(18))
                val left = Kinematics.pose(c, Drive.FWD, t2, IntArray(18))
                val msg = "$gait ${Legs.ALL[r].code}/${Legs.ALL[l].code} t=$t"
                assertEquals("coxa $msg", 3000.0, (right[c.servo(r, 0)] + left[c.servo(l, 0)]).toDouble(), 1.0)
                assertEquals("femur $msg", 3000.0, (right[c.servo(r, 1)] + left[c.servo(l, 1)]).toDouble(), 1.0)
                assertEquals("tibia $msg", right[c.servo(r, 2)].toDouble(), left[c.servo(l, 2)].toDouble(), 1.0)
            }
        }
    }

    @Test
    fun crawlLiftsOnePairAtATime() {
        val c = cal.copy(gait = Gait.CRAWL)
        val stand = Kinematics.pose(c, Drive(), 0.0, IntArray(18))
        // Mid-way through quarter 0 only RF and LR femurs leave their standing pulse by much.
        val p = Kinematics.pose(c, Drive.FWD, 0.125, IntArray(18))
        val lifted = (0 until 6).filter { leg -> kotlin.math.abs(p[c.servo(leg, 1)] - stand[c.servo(leg, 1)]) > 150 }
        assertEquals(listOf(0, 5), lifted)
    }

    @Test
    fun driftCorrectionTurnsTheBody() {
        val straight = Kinematics.pose(cal, Drive.FWD, 0.9, IntArray(18))
        val corrected = Kinematics.pose(cal.copy(driftTenths = 30), Drive.FWD, 0.9, IntArray(18))
        assertTrue(straight[0] != corrected[0])
        // Standing still ignores it.
        assertArrayEquals(
            Kinematics.pose(cal, Drive(), 0.0, IntArray(18)),
            Kinematics.pose(cal.copy(driftTenths = 30), Drive(), 0.0, IntArray(18)),
        )
    }

    @Test
    fun channelOrderMatchesTheBoard() {
        assertEquals(listOf("RF", "RM", "RR", "LF", "LM", "LR"), Legs.ALL.map { it.code })
        assertEquals(1, cal.channel(0, 0))
        assertEquals(10, cal.channel(3, 0)) // LF on S10
        assertEquals(18, cal.channel(5, 2)) // LR tibia on S18
        val oldWiring = cal.copy(leftFrontFirst = false)
        assertEquals(16, oldWiring.channel(3, 0)) // LF on S16
        assertEquals(10, oldWiring.channel(5, 0)) // LR on S10
    }

    @Test
    fun pythonExportListsChannels() {
        val text = cal.pythonExport()
        assertTrue(text.contains("#   LF: (10, 11, 12)"))
        assertTrue(text.contains("#   LR: (16, 17, 18)"))
        assertTrue(text.contains("\"LF\": (1, -1, 1)"))
    }
}

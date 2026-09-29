package com.robospider.hexapod

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class KinematicsTest {
    private val cal = Calibration()

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
        for (d in listOf(Drive.FWD, Drive.BACK, Drive.LEFT, Drive.RIGHT, Drive.TURN_L, Drive.TURN_R)) {
            var t = 0.0
            while (t < 1.0) {
                // A zeroed "previous" pose would leak through for any unreachable leg.
                val p = Kinematics.pose(cal, d, t, IntArray(18))
                assertTrue("unreachable at $d t=$t: ${p.toList()}", p.all { it in 800..2200 })
                t += 0.05
            }
        }
    }

    @Test
    fun liftedFootRaisesTheFemur() {
        // Phase 0.25 is mid-swing for RF (group A): femur (S2) moves off 1500, tibia stays sane.
        val p = Kinematics.pose(cal, Drive.FWD, 0.25, IntArray(18))
        assertTrue(p[1] > 1500)
        // RM (group B) is mid-stance: foot on the ground at full height.
        assertNotNull(Kinematics.ik(cal.coxa + cal.femur.toDouble(), 0.0, -cal.tibia.toDouble(), cal))
    }

    @Test
    fun channelOrderMatchesTheBoard() {
        assertEquals(listOf("RF", "RM", "RR", "LF", "LM", "LR"), Legs.ALL.map { it.code })
        assertEquals(1, Legs.channel(0, 0))
        assertEquals(10, Legs.channel(3, 0))
        assertEquals(18, Legs.channel(5, 2))
    }

    @Test
    fun pythonExportListsChannels() {
        val text = cal.pythonExport()
        assertTrue(text.contains("#   LF: (10, 11, 12)"))
        assertTrue(text.contains("#   LR: (16, 17, 18)"))
        assertTrue(text.contains("\"LF\": (1, -1, 1)"))
    }
}

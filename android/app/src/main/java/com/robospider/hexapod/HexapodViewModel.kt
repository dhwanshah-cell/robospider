package com.robospider.hexapod

import android.app.Application
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.math.atan2
import kotlin.math.roundToInt
import kotlin.random.Random

class HexapodViewModel(app: Application) : AndroidViewModel(app), SensorEventListener {
    private val settings = Settings(app)
    private val main = Handler(Looper.getMainLooper())

    // ---- USB link -------------------------------------------------------------------
    var connected by mutableStateOf(false); private set
    var linkStatus by mutableStateOf("No USB device seen — dry run"); private set
    var usbDetails by mutableStateOf(""); private set
    var baud by mutableStateOf(settings.baud); private set
    val log = mutableStateListOf<String>()

    private val link = Usc32Link(app) { e ->
        main.post {
            when (e) {
                is Usc32Link.Event.Status -> {
                    connected = e.connected
                    linkStatus = e.text
                }
                is Usc32Link.Event.Devices -> usbDetails = e.text
                is Usc32Link.Event.Sent -> {
                    log.add(0, (if (e.dryRun) "dry   " else "sent  ") + e.line)
                    while (log.size > 3) log.removeAt(log.lastIndex)
                }
            }
        }
    }.also { it.setBaud(settings.baud) }

    fun connect() = link.connect()
    fun refreshUsb() = link.refresh()
    fun setBaudRate(b: Int) {
        baud = b
        settings.baud = b
        link.setBaud(b)
    }

    // ---- Servos and calibration -----------------------------------------------------
    val pulses = mutableStateListOf<Int>().apply { addAll(List(18) { 1500 }) }
    var cal by mutableStateOf(settings.loadCalibration()); private set
    private var savedCal by mutableStateOf(cal)
    val unsaved get() = cal != savedCal

    /** True while the servos hold an IK pose (stand/walk), so calibration edits re-send it. */
    private var posed = false

    private fun sendPose(p: IntArray, ms: Int) {
        for (i in 0 until 18) if (pulses[i] != p[i]) pulses[i] = p[i]
        link.send(p.withIndex().joinToString("") { (i, v) -> "#${i + 1}P$v" } + "T$ms", "pose")
    }

    private fun sendJoint(i: Int, ms: Int = 100) = link.send("#${i + 1}P${pulses[i]}T$ms", "j$i")

    fun setJoint(i: Int, value: Int) {
        stopMotion()
        pulses[i] = value.coerceIn(Legs.MIN_US, Legs.MAX_US)
        sendJoint(i)
    }

    fun nudgeJoint(i: Int, delta: Int) = setJoint(i, pulses[i] + delta)

    fun centerAll() {
        stopMotion()
        sendPose(IntArray(18) { 1500 }, 500)
    }

    fun stand() {
        stopMotion()
        posed = true
        sendPose(standPose(), 500)
    }

    fun nudgeTrim(i: Int, delta: Int) {
        cal = cal.copy(trim = cal.trim.toMutableList().also { it[i] = (it[i] + delta).coerceIn(-500, 500) })
        // Move the servo by the same amount so the effect is visible right away.
        pulses[i] = (pulses[i] + delta).coerceIn(Legs.MIN_US, Legs.MAX_US)
        sendJoint(i)
    }

    fun flipDir(i: Int) {
        cal = cal.copy(dir = cal.dir.toMutableList().also { it[i] = -it[i] })
        resendIfPosed()
    }

    fun setLengths(coxa: Int = cal.coxa, femur: Int = cal.femur, tibia: Int = cal.tibia, step: Int = cal.step) {
        cal = cal.copy(
            coxa = coxa.coerceIn(5, 200), femur = femur.coerceIn(10, 300),
            tibia = tibia.coerceIn(10, 300), step = step.coerceIn(0, 200),
        )
        resendIfPosed()
    }

    fun setWalking(
        gait: Gait = cal.gait,
        lift: Int = cal.lift,
        cycleMs: Int = cal.cycleMs,
        driftTenths: Int = cal.driftTenths,
    ) {
        cal = cal.copy(
            gait = gait, lift = lift.coerceIn(5, 60), cycleMs = cycleMs.coerceIn(400, 6000),
            driftTenths = driftTenths.coerceIn(-150, 150),
        )
    }

    /** Which left leg is wired to S10-12. Dir and trim stay with the servo channel. */
    fun setLeftFrontFirst(on: Boolean) {
        cal = cal.copy(leftFrontFirst = on)
        resendIfPosed()
    }

    fun saveCalibration() {
        settings.saveCalibration(cal)
        savedCal = cal
    }

    fun resetCalibration() {
        cal = Calibration()
        resendIfPosed()
    }

    private fun resendIfPosed() {
        if (posed && drive == null && !patrol) sendPose(standPose(), 200)
    }

    private fun standPose() =
        Kinematics.pose(cal, Drive(), 0.0, pulses.toIntArray(), levelPitch, levelRoll)

    // ---- Walking ----------------------------------------------------------------------
    var mode by mutableStateOf("manual"); private set
    private var drive: Drive? = null
    private var phase = 0.0

    fun startDrive(d: Drive) {
        patrol = false
        drive = d
        posed = true
        mode = "walking"
    }

    fun stopDrive() {
        if (drive == null) return
        drive = null
        phase = 0.0
        mode = "manual"
        sendPose(standPose(), 300)
    }

    private fun stopMotion() {
        drive = null
        patrol = false
        posed = false
        phase = 0.0
        if (mode != "manual") mode = "manual"
    }

    /** One update interval: long enough for a full 18-servo line to go out at this baud. */
    private fun tickMs(): Int = maxOf(60, (link.wireMs(18 * 11 + 8) * 1.25).roundToInt())

    // ---- Patrol -----------------------------------------------------------------------
    var patrol by mutableStateOf(false); private set
    private var segment = Drive.FWD
    private var segmentCycles = 0.0
    private var holdUntil = 0L
    private var lastAlertAt = 0L
    private var personHits = 0

    fun togglePatrol() {
        if (patrol) {
            stopMotion()
            sendPose(standPose(), 400)
            return
        }
        drive = null
        patrol = true
        posed = true
        mode = "patrol"
        segment = Drive.FWD
        segmentCycles = 4.0
        holdUntil = 0
    }

    private fun nextSegment() {
        if (segment == Drive.FWD) {
            segment = if (Random.nextBoolean()) Drive.TURN_L else Drive.TURN_R
            segmentCycles = Random.nextInt(1, 4).toDouble()
        } else {
            segment = Drive.FWD
            segmentCycles = 4.0
        }
    }

    // ---- Detection & alerts -------------------------------------------------------------
    var personScore by mutableStateOf(0f); private set
    var fps by mutableStateOf(0f); private set
    var soundLabel by mutableStateOf("—"); private set
    var soundScore by mutableStateOf(0f); private set
    var alertStatus by mutableStateOf(""); private set
    var ntfyServer by mutableStateOf(settings.ntfyServer); private set
    var ntfyTopic by mutableStateOf(settings.ntfyTopic); private set

    private val alerts = AlertSender(app)
    val personDetector = PersonDetector(app) { score, f ->
        main.post {
            personScore = score
            fps = f
            personHits = if (score >= 0.5f) personHits + 1 else 0
            if (personHits >= 2) onSighting("Person seen by camera (%d%%)".format((score * 100).roundToInt()))
        }
    }
    private val sound = SoundListener(app) { label, score ->
        main.post {
            soundLabel = label
            soundScore = score
            if (score >= 0.35f && label in SoundListener.HUMAN_SOUNDS) {
                onSighting("Heard: $label (%d%%)".format((score * 100).roundToInt()))
            }
        }
    }

    fun startListening() = sound.start()
    fun stopListening() = sound.stop()

    fun updateNtfy(server: String = ntfyServer, topic: String = ntfyTopic) {
        ntfyServer = server
        ntfyTopic = topic
        settings.ntfyServer = server
        settings.ntfyTopic = topic
    }

    private fun onSighting(what: String) {
        if (!patrol) return
        val now = SystemClock.elapsedRealtime()
        if (now < holdUntil || now - lastAlertAt < 60_000) return
        lastAlertAt = now
        holdUntil = now + 20_000
        mode = "alert!"
        sendPose(standPose(), 300)
        sendAlert("Hexapod SAR: possible survivor", what)
    }

    fun testAlert() = sendAlert("Hexapod SAR test alert", "Test alert from the hexapod app")

    private fun sendAlert(title: String, what: String) {
        alertStatus = "Sending alert…"
        val server = ntfyServer
        val topic = ntfyTopic
        viewModelScope.launch {
            val (err, waiting) = withContext(Dispatchers.IO) {
                val a = alerts.compose(title, what, personDetector.snapshotJpeg())
                alerts.send(server, topic, a) to alerts.pendingCount
            }
            val time = SimpleDateFormat("HH:mm:ss", Locale.US).format(Date())
            alertStatus = if (err == null) {
                "Alert sent $time" + if (waiting > 0) " · $waiting saved alerts still waiting" else ""
            } else {
                "Alert NOT sent ($err); saved on phone" + if (waiting > 1) " ($waiting waiting)" else ""
            }
        }
    }

    // ---- Self-level ---------------------------------------------------------------------
    var selfLevel by mutableStateOf(false); private set
    var tiltText by mutableStateOf("tilt: mount the phone upright on the robot"); private set
    private var pitch = 0.0
    private var roll = 0.0
    private var upright = false
    private var levelPitch = 0.0
    private var levelRoll = 0.0
    private val sensors = app.getSystemService(android.content.Context.SENSOR_SERVICE) as SensorManager

    fun setSelfLevelOn(on: Boolean) {
        selfLevel = on
        if (on) {
            val s = sensors.getDefaultSensor(Sensor.TYPE_GRAVITY) ?: sensors.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
            if (s == null) {
                tiltText = "tilt: this phone has no tilt sensor"
                selfLevel = false
                return
            }
            sensors.registerListener(this, s, SensorManager.SENSOR_DELAY_GAME)
        } else {
            sensors.unregisterListener(this)
            levelPitch = 0.0
            levelRoll = 0.0
            resendIfPosed()
        }
    }

    override fun onSensorChanged(e: SensorEvent) {
        // Phone upright, screen facing the back of the robot, rear camera forward.
        val (gx, gy, gz) = Triple(e.values[0].toDouble(), e.values[1].toDouble(), e.values[2].toDouble())
        upright = gy > 7.0
        if (!upright) {
            tiltText = "tilt: mount the phone upright on the robot"
            return
        }
        pitch = Math.toDegrees(atan2(-gz, gy)) // nose up is positive
        roll = Math.toDegrees(atan2(-gx, gy)) // left side up is positive
        tiltText = "tilt: pitch %+.1f°  roll %+.1f°   correcting %+.1f° / %+.1f°"
            .format(pitch, roll, levelPitch, levelRoll)
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}

    // ---- Control loop -------------------------------------------------------------------
    init {
        link.refresh()
        // Pick up a board plugged in (or unplugged) while the app is open.
        viewModelScope.launch {
            while (true) {
                delay(2000)
                if (!connected) link.refresh()
            }
        }
        viewModelScope.launch {
            while (true) {
                val tick = tickMs()
                // Enough command frames per cycle for a smooth step: a crawl needs twice a tripod's.
                val cycleMs = maxOf(cal.cycleMs.toDouble(), tick * if (cal.gait == Gait.CRAWL) 16.0 else 8.0)
                val now = SystemClock.elapsedRealtime()

                if (selfLevel && upright && posed) {
                    levelPitch = (levelPitch - 0.3 * pitch).coerceIn(-12.0, 12.0)
                    levelRoll = (levelRoll - 0.3 * roll).coerceIn(-12.0, 12.0)
                }

                val d = drive
                when {
                    d != null -> {
                        phase = (phase + tick / cycleMs).mod(1.0)
                        sendPose(Kinematics.pose(cal, d, phase, pulses.toIntArray(), levelPitch, levelRoll), tick + 20)
                    }
                    patrol && now >= holdUntil -> {
                        if (mode != "patrol") mode = "patrol"
                        phase += tick / cycleMs
                        if (phase >= segmentCycles) {
                            phase = 0.0
                            nextSegment()
                        }
                        sendPose(Kinematics.pose(cal, segment, phase.mod(1.0), pulses.toIntArray(), levelPitch, levelRoll), tick + 20)
                    }
                    selfLevel && upright && posed -> {
                        val p = standPose()
                        if ((0 until 18).any { kotlin.math.abs(p[it] - pulses[it]) >= 4 }) sendPose(p, tick + 20)
                    }
                }
                delay(tick.toLong())
            }
        }
    }

    override fun onCleared() {
        sensors.unregisterListener(this)
        sound.stop()
        personDetector.close()
        link.dispose()
    }
}

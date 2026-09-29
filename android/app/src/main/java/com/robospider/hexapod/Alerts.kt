package com.robospider.hexapod

import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationManager
import androidx.core.content.ContextCompat
import java.io.File
import java.net.HttpURLConnection
import java.net.URI
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Sends alerts to an ntfy topic (https://ntfy.sh): rescuers install the ntfy app and
 * subscribe to the topic. Alerts that can't be sent are saved on the phone and resent
 * with the next alert that gets through.
 */
class AlertSender(private val context: Context) {
    private val dir = File(context.filesDir, "alerts").apply { mkdirs() }

    val pendingCount get() = dir.listFiles { f -> f.name.endsWith(".txt") }?.size ?: 0

    data class Alert(val title: String, val message: String, val jpeg: ByteArray?, val click: String?)

    /** Build an alert with the time and, if the phone knows it, the location. */
    fun compose(title: String, what: String, jpeg: ByteArray?): Alert {
        val time = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).format(Date())
        val loc = lastLocation()
        val where = loc?.let { "%.6f,%.6f (±%.0f m)".format(Locale.US, it.latitude, it.longitude, it.accuracy) }
        val msg = buildString {
            append(what)
            append("\nTime: ").append(time)
            append("\nLocation: ").append(where ?: "unknown")
        }
        val click = loc?.let { "https://maps.google.com/?q=%.6f,%.6f".format(Locale.US, it.latitude, it.longitude) }
        return Alert(title, msg, jpeg, click)
    }

    /** Blocking: call off the main thread. Returns null on success, else the error name. */
    fun send(server: String, topic: String, alert: Alert): String? {
        val err = post(server, topic, alert)
        if (err == null) flushPending(server, topic) else save(alert)
        return err
    }

    private fun post(server: String, topic: String, a: Alert): String? {
        return try {
            val url = URI(server.trim().trimEnd('/') + "/" + topic.trim()).toURL()
            val c = url.openConnection() as HttpURLConnection
            c.connectTimeout = 8000
            c.readTimeout = 15000
            c.doOutput = true
            c.setRequestProperty("Title", ascii(a.title))
            c.setRequestProperty("Priority", "urgent")
            c.setRequestProperty("Tags", "rotating_light,robot")
            a.click?.let { c.setRequestProperty("Click", it) }
            val body: ByteArray
            if (a.jpeg != null) {
                // The photo is the body; the text goes in a header.
                c.requestMethod = "PUT"
                c.setRequestProperty("Filename", "hexapod.jpg")
                c.setRequestProperty("Message", ascii(a.message).replace("\n", "\\n"))
                body = a.jpeg
            } else {
                c.requestMethod = "POST"
                body = a.message.toByteArray()
            }
            c.setFixedLengthStreamingMode(body.size)
            c.outputStream.use { it.write(body) }
            val code = c.responseCode
            c.disconnect()
            if (code in 200..299) null else "HTTP $code"
        } catch (e: Exception) {
            e.javaClass.simpleName
        }
    }

    private fun save(a: Alert) {
        val base = "alert-" + System.currentTimeMillis()
        File(dir, "$base.txt").writeText(listOf(a.title, a.click ?: "", a.message).joinToString("\n"))
        a.jpeg?.let { File(dir, "$base.jpg").writeBytes(it) }
    }

    fun flushPending(server: String, topic: String) {
        val files = dir.listFiles { f -> f.name.endsWith(".txt") }?.sortedBy { it.name } ?: return
        for (txt in files) {
            val lines = txt.readLines()
            if (lines.size < 3) {
                txt.delete()
                continue
            }
            val jpg = File(dir, txt.nameWithoutExtension + ".jpg")
            val a = Alert(
                title = lines[0] + " (delayed)",
                message = lines.drop(2).joinToString("\n"),
                jpeg = if (jpg.exists()) jpg.readBytes() else null,
                click = lines[1].ifEmpty { null },
            )
            if (post(server, topic, a) != null) return
            txt.delete()
            jpg.delete()
        }
    }

    @SuppressLint("MissingPermission")
    private fun lastLocation(): Location? {
        val fine = ContextCompat.checkSelfPermission(context, android.Manifest.permission.ACCESS_FINE_LOCATION)
        val coarse = ContextCompat.checkSelfPermission(context, android.Manifest.permission.ACCESS_COARSE_LOCATION)
        if (fine != PackageManager.PERMISSION_GRANTED && coarse != PackageManager.PERMISSION_GRANTED) return null
        val lm = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
        return listOf(LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER, LocationManager.PASSIVE_PROVIDER)
            .mapNotNull { runCatching { lm.getLastKnownLocation(it) }.getOrNull() }
            .maxByOrNull { it.time }
    }

    private fun ascii(s: String) = s.map { if (it.code in 32..126 || it == '\n') it else '?' }.joinToString("")
}

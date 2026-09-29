package com.robospider.hexapod

import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.hardware.usb.UsbDevice
import android.hardware.usb.UsbManager
import android.os.Build
import androidx.core.content.ContextCompat
import com.hoho.android.usbserial.driver.CdcAcmSerialDriver
import com.hoho.android.usbserial.driver.UsbSerialDriver
import com.hoho.android.usbserial.driver.UsbSerialPort
import com.hoho.android.usbserial.driver.UsbSerialProber

/**
 * Serial link to the USC-32 over USB-OTG.
 *
 * The USC-32 takes plain text lines: `#<ch>P<pulse µs>T<ms>\r\n`, several servos in one
 * line as `#1P1500#2P1600T200\r\n`. With nothing plugged in, lines are only logged
 * (dry run).
 *
 * Writes go through a single background thread. Each send has a key; a newer send with
 * the same key replaces an older one still waiting, so slow baud rates drop stale poses
 * instead of queueing them up.
 */
class Usc32Link(private val context: Context, private val onEvent: (Event) -> Unit) {

    sealed interface Event {
        data class Status(val connected: Boolean, val text: String) : Event
        data class Sent(val line: String, val dryRun: Boolean) : Event
    }

    private val usb = context.getSystemService(Context.USB_SERVICE) as UsbManager
    private val permissionAction = context.packageName + ".USB_PERMISSION"
    private var port: UsbSerialPort? = null
    var baud = 9600
        private set

    private val lock = Object()
    private val pending = LinkedHashMap<String, String>()
    private val writer = Thread(::writeLoop, "usc32-writer").apply { isDaemon = true; start() }

    private val receiver = object : BroadcastReceiver() {
        override fun onReceive(ctx: Context, intent: Intent) {
            when (intent.action) {
                permissionAction -> {
                    if (intent.getBooleanExtra(UsbManager.EXTRA_PERMISSION_GRANTED, false)) connect()
                    else status(false, "USB permission denied — tap Connect to ask again")
                }
                UsbManager.ACTION_USB_DEVICE_DETACHED -> {
                    if (port != null) {
                        close()
                        status(false, "USC-32 unplugged — dry run")
                    } else refresh()
                }
                UsbManager.ACTION_USB_DEVICE_ATTACHED -> connect()
            }
        }
    }

    init {
        val filter = IntentFilter().apply {
            addAction(permissionAction)
            addAction(UsbManager.ACTION_USB_DEVICE_DETACHED)
            addAction(UsbManager.ACTION_USB_DEVICE_ATTACHED)
        }
        ContextCompat.registerReceiver(context, receiver, filter, ContextCompat.RECEIVER_NOT_EXPORTED)
    }

    val connected get() = port != null

    private fun status(connected: Boolean, text: String) = onEvent(Event.Status(connected, text))

    private fun findDriver(): UsbSerialDriver? {
        UsbSerialProber.getDefaultProber().findAllDrivers(usb).firstOrNull()?.let { return it }
        // Unknown chip: most boards without a USB-serial bridge speak plain CDC-ACM.
        return usb.deviceList.values.firstOrNull()?.let { CdcAcmSerialDriver(it) }
    }

    /** Update the status line without opening anything. */
    fun refresh() {
        if (port != null) return
        val d = findDriver()
        if (d == null) status(false, "No USB device seen — dry run")
        else status(false, "${describe(d.device)} found — tap Connect")
    }

    fun setBaud(value: Int) {
        baud = value
        port?.let {
            try {
                it.setParameters(baud, 8, UsbSerialPort.STOPBITS_1, UsbSerialPort.PARITY_NONE)
                status(true, "Connected: ${describe(it.driver.device)} @ $baud")
            } catch (e: Exception) {
                status(true, "Baud change failed: ${e.javaClass.simpleName}")
            }
        }
    }

    fun connect() {
        if (port != null) return
        val driver = findDriver() ?: return status(false, "No USB device seen — dry run")
        val device = driver.device
        if (!usb.hasPermission(device)) {
            val flags = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) PendingIntent.FLAG_MUTABLE else 0
            val intent = Intent(permissionAction).setPackage(context.packageName)
            usb.requestPermission(device, PendingIntent.getBroadcast(context, 0, intent, flags))
            return status(false, "Allow USB access in the popup")
        }
        val conn = usb.openDevice(device) ?: return status(false, "Couldn't open ${describe(device)}")
        try {
            val p = driver.ports[0]
            p.open(conn)
            p.setParameters(baud, 8, UsbSerialPort.STOPBITS_1, UsbSerialPort.PARITY_NONE)
            try {
                p.dtr = true
                p.rts = true
            } catch (_: Exception) {
                // Not every chip has modem lines.
            }
            port = p
            status(true, "Connected: ${describe(device)} @ $baud")
        } catch (e: Exception) {
            conn.close()
            status(false, "Open failed (${e.javaClass.simpleName}) — dry run")
        }
    }

    fun close() {
        try {
            port?.close()
        } catch (_: Exception) {
        }
        port = null
    }

    fun dispose() {
        close()
        try {
            context.unregisterReceiver(receiver)
        } catch (_: Exception) {
        }
        writer.interrupt()
    }

    /** Queue [line] (without the trailing \r\n). A later send with the same [key] replaces it. */
    fun send(line: String, key: String = line) {
        synchronized(lock) {
            pending.remove(key)
            pending[key] = line
            lock.notifyAll()
        }
    }

    private fun writeLoop() {
        while (!Thread.currentThread().isInterrupted) {
            val line = synchronized(lock) {
                while (pending.isEmpty()) {
                    try {
                        lock.wait()
                    } catch (_: InterruptedException) {
                        return
                    }
                }
                val k = pending.keys.first()
                pending.remove(k)!!
            }
            val p = port
            if (p == null) {
                onEvent(Event.Sent(line, dryRun = true))
                continue
            }
            try {
                p.write((line + "\r\n").toByteArray(Charsets.US_ASCII), 1000)
                onEvent(Event.Sent(line, dryRun = false))
            } catch (e: Exception) {
                close()
                status(false, "Write failed (${e.javaClass.simpleName}) — dry run")
            }
        }
    }

    /** How long [chars] characters take on the wire at the current baud (10 bits each), in ms. */
    fun wireMs(chars: Int) = chars * 10_000.0 / baud

    private fun describe(d: UsbDevice): String {
        val chip = when (d.vendorId) {
            0x1A86 -> "CH340"
            0x10C4 -> "CP210x"
            0x0403 -> "FTDI"
            0x067B -> "PL2303"
            0x0483 -> "STM32 VCP"
            else -> "USB %04X:%04X".format(d.vendorId, d.productId)
        }
        return chip
    }
}

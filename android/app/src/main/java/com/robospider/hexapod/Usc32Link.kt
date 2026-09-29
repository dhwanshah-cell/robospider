package com.robospider.hexapod

import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.hardware.usb.UsbConstants
import android.hardware.usb.UsbDevice
import android.hardware.usb.UsbDeviceConnection
import android.hardware.usb.UsbEndpoint
import android.hardware.usb.UsbInterface
import android.hardware.usb.UsbManager
import android.os.Build
import androidx.core.content.ContextCompat
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
        /** What the phone sees on USB, for the diagnostics line. */
        data class Devices(val text: String) : Event
    }

    private val usb = context.getSystemService(Context.USB_SERVICE) as UsbManager
    private val permissionAction = context.packageName + ".USB_PERMISSION"
    private var port: Sink? = null
    private var awaitingPermission = false
    var baud = 9600
        private set

    private val lock = Object()
    private val pending = LinkedHashMap<String, String>()
    private val writer = Thread(::writeLoop, "usc32-writer").apply { isDaemon = true; start() }

    private val receiver = object : BroadcastReceiver() {
        override fun onReceive(ctx: Context, intent: Intent) {
            when (intent.action) {
                permissionAction -> {
                    awaitingPermission = false
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

    /** Where bytes go once connected. */
    private interface Sink {
        val name: String
        fun write(b: ByteArray)
        fun setBaud(baud: Int)
        fun close()
    }

    /** A known USB-serial chip (CH340, CP210x, FTDI, PL2303, CDC-ACM) through usb-serial-for-android. */
    private class SerialSink(private val port: UsbSerialPort, override val name: String) : Sink {
        override fun write(b: ByteArray) = port.write(b, 1000)
        override fun setBaud(baud: Int) = port.setParameters(baud, 8, UsbSerialPort.STOPBITS_1, UsbSerialPort.PARITY_NONE)
        override fun close() = port.close()
    }

    /**
     * Anything else: write straight to the first OUT endpoint (bulk, else interrupt), the way
     * the old app did. If the board has a CDC control interface, set the line coding on it too.
     */
    private class RawSink(
        private val conn: UsbDeviceConnection,
        private val intf: UsbInterface,
        private val ep: UsbEndpoint,
        private val control: UsbInterface?,
        override val name: String,
    ) : Sink {
        override fun write(b: ByteArray) {
            var off = 0
            while (off < b.size) {
                val n = conn.bulkTransfer(ep, b, off, b.size - off, 1000)
                if (n <= 0) throw java.io.IOException("USB write returned $n")
                off += n
            }
        }

        override fun setBaud(baud: Int) {
            val ctl = control ?: return
            // CDC SET_LINE_CODING: baud (little endian), 1 stop bit, no parity, 8 data bits.
            val coding = byteArrayOf(
                (baud and 0xFF).toByte(), (baud shr 8 and 0xFF).toByte(), (baud shr 16 and 0xFF).toByte(),
                (baud shr 24 and 0xFF).toByte(), 0, 0, 8,
            )
            conn.controlTransfer(0x21, 0x20, 0, ctl.id, coding, coding.size, 500)
            conn.controlTransfer(0x21, 0x22, 0x03, ctl.id, null, 0, 500) // DTR + RTS on
        }

        override fun close() {
            conn.releaseInterface(intf)
            conn.close()
        }
    }

    private fun firstDevice(): UsbDevice? =
        UsbSerialProber.getDefaultProber().findAllDrivers(usb).firstOrNull()?.device ?: usb.deviceList.values.firstOrNull()

    private fun openRaw(device: UsbDevice): RawSink? {
        val out = (0 until device.interfaceCount).map { device.getInterface(it) }
            .flatMap { i -> (0 until i.endpointCount).map { i to i.getEndpoint(it) } }
            .filter { it.second.direction == UsbConstants.USB_DIR_OUT }
        val (intf, ep) = out.firstOrNull { it.second.type == UsbConstants.USB_ENDPOINT_XFER_BULK }
            ?: out.firstOrNull { it.second.type == UsbConstants.USB_ENDPOINT_XFER_INT }
            ?: return null
        val conn = usb.openDevice(device) ?: return null
        if (!conn.claimInterface(intf, true)) {
            conn.close()
            return null
        }
        val control = (0 until device.interfaceCount).map { device.getInterface(it) }
            .firstOrNull { it.interfaceClass == UsbConstants.USB_CLASS_COMM }
        val kind = if (ep.type == UsbConstants.USB_ENDPOINT_XFER_BULK) "bulk" else "interrupt"
        return RawSink(conn, intf, ep, control, "${describe(device)} (raw $kind)").also { it.setBaud(baud) }
    }

    /**
     * Re-check what's plugged in. Connects straight away when Android has already granted
     * access (e.g. the app was opened from the plug-in popup); otherwise just updates the status.
     */
    fun refresh() {
        onEvent(Event.Devices(diagnostics()))
        if (port != null || awaitingPermission) return
        val d = firstDevice()
        when {
            d == null -> status(false, "No USB device seen — dry run")
            usb.hasPermission(d) -> connect()
            else -> status(false, "${describe(d)} found — tap Connect")
        }
    }

    /** One line per USB device: ids, names, interface classes, driver, permission. */
    private fun diagnostics(): String {
        val devices = usb.deviceList.values
        if (devices.isEmpty()) return "usb: nothing attached (check OTG adapter, cable, board power)"
        val prober = UsbSerialProber.getDefaultProber()
        return devices.joinToString("\n") { d ->
            val ifaces = (0 until d.interfaceCount).joinToString(",") { "%02X".format(d.getInterface(it).interfaceClass) }
            val driver = prober.probeDevice(d)?.javaClass?.simpleName?.removeSuffix("SerialDriver") ?: "no serial driver → raw"
            "usb: %04X:%04X %s %s · if[%s] · %s · perm %s".format(
                d.vendorId, d.productId, d.manufacturerName ?: "", d.productName ?: "", ifaces, driver,
                if (usb.hasPermission(d)) "yes" else "no",
            ).replace("  ", " ")
        }
    }

    fun setBaud(value: Int) {
        baud = value
        port?.let {
            try {
                it.setBaud(baud)
                status(true, "Connected: ${it.name} @ $baud")
            } catch (e: Exception) {
                status(true, "Baud change failed: ${e.javaClass.simpleName}")
            }
        }
    }

    fun connect() {
        if (port != null) return
        val device = firstDevice() ?: return status(false, "No USB device seen — dry run")
        if (!usb.hasPermission(device)) {
            val flags = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) PendingIntent.FLAG_MUTABLE else 0
            val intent = Intent(permissionAction).setPackage(context.packageName)
            awaitingPermission = true
            usb.requestPermission(device, PendingIntent.getBroadcast(context, 0, intent, flags))
            return status(false, "Allow USB access in the popup")
        }
        var serialError: String? = null
        val driver = UsbSerialProber.getDefaultProber().probeDevice(device)
        if (driver != null) {
            val conn = usb.openDevice(device) ?: return status(false, "Couldn't open ${describe(device)}")
            try {
                val p = driver.ports.firstOrNull() ?: error("no serial port on this device")
                p.open(conn)
                p.setParameters(baud, 8, UsbSerialPort.STOPBITS_1, UsbSerialPort.PARITY_NONE)
                try {
                    p.dtr = true
                    p.rts = true
                } catch (_: Exception) {
                    // Not every chip has modem lines.
                }
                port = SerialSink(p, describe(device))
            } catch (e: Exception) {
                serialError = "${e.javaClass.simpleName} ${e.message ?: ""}".trim()
                conn.close()
            }
        }
        if (port == null) {
            port = try {
                openRaw(device)
            } catch (e: Exception) {
                serialError = serialError ?: e.javaClass.simpleName
                null
            }
        }
        val p = port
        if (p != null) status(true, "Connected: ${p.name} @ $baud")
        else status(false, "Open failed: ${serialError ?: "no writable USB endpoint"} — dry run")
        onEvent(Event.Devices(diagnostics()))
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
                p.write((line + "\r\n").toByteArray(Charsets.US_ASCII))
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

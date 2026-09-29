package com.robospider.hexapod.ui

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.widget.Toast
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import com.robospider.hexapod.BuildConfig
import com.robospider.hexapod.Drive
import com.robospider.hexapod.HexapodViewModel
import com.robospider.hexapod.Legs
import java.util.concurrent.Executors
import kotlin.math.roundToInt

private val Bg = Color(0xFF0E1014)
private val CardBg = Color(0xFF181B22)
private val Line = Color(0xFF363B48)
private val TextMain = Color(0xFFE9EBF1)
private val Muted = Color(0xFF9AA1B0)
private val Yellow = Color(0xFFFFC53D)
private val Green = Color(0xFF22C55E)
private val Cyan = Color(0xFF22D3EE)
private val Red = Color(0xFFF87171)
private val PadBtn = Color(0xFF3B4259)
private val Mono = FontFamily.Monospace

@Composable
fun HexapodScreen(vm: HexapodViewModel, cameraGranted: Boolean) {
    MaterialTheme(colorScheme = darkColorScheme(background = Bg, surface = CardBg, primary = Yellow)) {
        Column(
            Modifier
                .fillMaxSize()
                .background(Bg)
                .safeDrawingPadding()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 12.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            StatusCard(vm)
            RescueCard(vm, cameraGranted)
            DriveCard(vm)
            Legs.ALL.indices.forEach { LegCard(vm, it) }
            CalibrationCard(vm)
            Text(
                "Hexapod SAR · ${BuildConfig.BUILD_STAMP} · v${BuildConfig.VERSION_NAME}",
                color = Muted, fontFamily = Mono, fontSize = 12.sp,
                modifier = Modifier.fillMaxWidth().padding(vertical = 16.dp), textAlign = TextAlign.Center,
            )
        }
    }
}

// ---- Building blocks ----------------------------------------------------------------------

@Composable
private fun Card(content: @Composable ColumnScope.() -> Unit) {
    Column(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(20.dp))
            .background(CardBg)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
        content = content,
    )
}

@Composable
private fun Btn(
    text: String,
    modifier: Modifier = Modifier,
    fill: Color? = null,
    textColor: Color = if (fill != null) Color(0xFF1A1400) else TextMain,
    shape: Shape = RoundedCornerShape(14.dp),
    height: Int = 44,
    fontSize: Int = 15,
    onClick: () -> Unit,
) {
    Box(
        modifier
            .height(height.dp)
            .clip(shape)
            .then(if (fill != null) Modifier.background(fill) else Modifier.border(1.5.dp, Line, shape))
            .clickable(onClick = onClick)
            .padding(horizontal = 12.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(text, color = textColor, fontSize = fontSize.sp, fontWeight = FontWeight.SemiBold, maxLines = 1)
    }
}

@Composable
private fun Warning(text: String) = Text(text, color = Yellow, fontSize = 14.sp, fontWeight = FontWeight.Medium)

// ---- USB status -------------------------------------------------------------------------------

@Composable
private fun StatusCard(vm: HexapodViewModel) = Card {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(12.dp).clip(CircleShape).background(if (vm.connected) Green else Yellow))
        Spacer(Modifier.width(8.dp))
        Text(vm.linkStatus, color = TextMain, fontWeight = FontWeight.Bold, fontSize = 16.sp, modifier = Modifier.weight(1f))
        Spacer(Modifier.width(8.dp))
        Btn(if (vm.connected) "Connected" else "Connect", fill = if (vm.connected) Green else Yellow) { vm.connect() }
    }
    if (!vm.connected) {
        Text(
            "Plug the USC-32 in with a USB-OTG adapter. Until then every command is only shown below (dry run).",
            color = Muted, fontSize = 14.sp,
        )
    }
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Text("baud", color = Muted, fontSize = 14.sp)
        listOf(9600, 115200).forEach { b ->
            Btn("$b", fill = if (vm.baud == b) Yellow else null, height = 34, fontSize = 13) { vm.setBaudRate(b) }
        }
    }
    Column(Modifier.fillMaxWidth().height(64.dp)) {
        vm.log.forEach {
            Text(it, color = TextMain, fontFamily = Mono, fontSize = 12.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
    }
}

// ---- Search & rescue --------------------------------------------------------------------------

@Composable
private fun RescueCard(vm: HexapodViewModel, cameraGranted: Boolean) = Card {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Text("Search & rescue", color = TextMain, fontWeight = FontWeight.Bold, fontSize = 18.sp, modifier = Modifier.weight(1f))
        Text(vm.mode, color = if (vm.mode == "alert!") Red else Cyan, fontFamily = Mono, fontSize = 14.sp)
    }
    Box(Modifier.fillMaxWidth().aspectRatio(4f / 3f).clip(RoundedCornerShape(16.dp)).background(Color.Black)) {
        if (cameraGranted) CameraPreview(vm)
        else Text("Camera permission needed", color = Muted, modifier = Modifier.align(Alignment.Center))
        Column(
            Modifier
                .padding(10.dp)
                .clip(RoundedCornerShape(10.dp))
                .background(Color(0xAA000000))
                .padding(horizontal = 10.dp, vertical = 6.dp),
        ) {
            val detector = if (vm.personDetector.available) "person %d%% · %.0f fps".format((vm.personScore * 100).roundToInt(), vm.fps)
            else "person detector unavailable"
            Text(detector, color = Color.White, fontFamily = Mono, fontSize = 14.sp)
            Text("sound: ${vm.soundLabel} %d%%".format((vm.soundScore * 100).roundToInt()), color = Color.White, fontFamily = Mono, fontSize = 14.sp)
        }
    }
    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        Btn(if (vm.patrol) "Stop patrol" else "Start patrol", Modifier.weight(1f), fill = if (vm.patrol) Red else Green, height = 52) { vm.togglePatrol() }
        Btn("Test alert", Modifier.weight(1f), textColor = Yellow, height = 52) { vm.testAlert() }
    }
    if (vm.alertStatus.isNotEmpty()) Text(vm.alertStatus, color = TextMain, fontSize = 14.sp)
    Text("Rescuers subscribe to this in the ntfy app:", color = Muted, fontSize = 13.sp)
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        NtfyField("server", vm.ntfyServer, Modifier.weight(1f)) { vm.updateNtfy(server = it) }
        NtfyField("topic", vm.ntfyTopic, Modifier.weight(1f)) { vm.updateNtfy(topic = it) }
    }
    Warning("No obstacle sensing yet — patrol only in a clear area, hand on the power switch. Any drive button stops the patrol.")
}

@Composable
private fun NtfyField(label: String, value: String, modifier: Modifier, onChange: (String) -> Unit) {
    OutlinedTextField(
        value = value,
        onValueChange = { onChange(it.trim()) },
        label = { Text(label, fontSize = 12.sp) },
        singleLine = true,
        textStyle = TextStyle(fontFamily = Mono, fontSize = 13.sp, color = TextMain),
        keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
        colors = OutlinedTextFieldDefaults.colors(unfocusedBorderColor = Line, focusedBorderColor = Yellow),
        modifier = modifier,
    )
}

@Composable
private fun CameraPreview(vm: HexapodViewModel) {
    val context = LocalContext.current
    val owner = LocalLifecycleOwner.current
    val previewView = remember { PreviewView(context).apply { scaleType = PreviewView.ScaleType.FILL_CENTER } }
    DisposableEffect(owner) {
        val executor = Executors.newSingleThreadExecutor()
        val future = ProcessCameraProvider.getInstance(context)
        var provider: ProcessCameraProvider? = null
        future.addListener({
            val p = future.get()
            provider = p
            val preview = Preview.Builder().build().also { it.surfaceProvider = previewView.surfaceProvider }
            val analysis = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .setOutputImageFormat(ImageAnalysis.OUTPUT_IMAGE_FORMAT_RGBA_8888)
                .build()
                .also { it.setAnalyzer(executor, vm.personDetector) }
            try {
                p.unbindAll()
                p.bindToLifecycle(owner, CameraSelector.DEFAULT_BACK_CAMERA, preview, analysis)
            } catch (_: Exception) {
            }
        }, ContextCompat.getMainExecutor(context))
        onDispose {
            provider?.unbindAll()
            executor.shutdown()
        }
    }
    AndroidView({ previewView }, Modifier.fillMaxSize())
}

// ---- Drive pad --------------------------------------------------------------------------------

@Composable
private fun DriveCard(vm: HexapodViewModel) = Card {
    Text("Hold to walk · release to stand", color = TextMain, fontSize = 16.sp)
    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        HoldBtn("⟲ turn", Drive.TURN_L, vm)
        HoldBtn("▲ fwd", Drive.FWD, vm)
        HoldBtn("turn ⟳", Drive.TURN_R, vm)
    }
    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        HoldBtn("◀ left", Drive.LEFT, vm)
        HoldBtn("▼ back", Drive.BACK, vm)
        HoldBtn("right ▶", Drive.RIGHT, vm)
    }
    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        Btn("Stand", Modifier.weight(1f), fill = Yellow, height = 52) { vm.stand() }
        Btn("Center all (1500)", Modifier.weight(1f), textColor = Cyan, height = 52) { vm.centerAll() }
    }
    Row(verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f)) {
            Text("Self-level", color = TextMain, fontWeight = FontWeight.Bold, fontSize = 16.sp)
            Text("Phone upright on the robot, rear camera forward", color = Muted, fontSize = 13.sp)
        }
        Switch(
            checked = vm.selfLevel,
            onCheckedChange = { vm.setSelfLevelOn(it) },
            colors = SwitchDefaults.colors(checkedTrackColor = Yellow, uncheckedTrackColor = Line),
        )
    }
    Text(vm.tiltText, color = TextMain, fontFamily = Mono, fontSize = 13.sp)
    Warning("First runs: robot on a box, legs in the air, hand on the power switch.")
}

@Composable
private fun RowScope.HoldBtn(label: String, drive: Drive, vm: HexapodViewModel) {
    var pressed by remember { mutableStateOf(false) }
    Box(
        Modifier
            .weight(1f)
            .height(64.dp)
            .clip(RoundedCornerShape(16.dp))
            .background(if (pressed) Yellow else PadBtn)
            .pointerInput(drive) {
                detectTapGestures(onPress = {
                    pressed = true
                    vm.startDrive(drive)
                    tryAwaitRelease()
                    pressed = false
                    vm.stopDrive()
                })
            },
        contentAlignment = Alignment.Center,
    ) {
        Text(label, color = if (pressed) Color(0xFF1A1400) else TextMain, fontSize = 17.sp, fontWeight = FontWeight.Bold)
    }
}

// ---- Per-leg servo cards --------------------------------------------------------------------------

@Composable
private fun LegCard(vm: HexapodViewModel, leg: Int) = Card {
    val info = Legs.ALL[leg]
    val color = Color(info.color)
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(12.dp).clip(CircleShape).background(color))
        Spacer(Modifier.width(8.dp))
        Text(info.code, color = color, fontWeight = FontWeight.Bold, fontSize = 18.sp)
        Spacer(Modifier.width(8.dp))
        Text(info.name, color = TextMain, fontSize = 17.sp, modifier = Modifier.weight(1f))
        Text("S${Legs.channel(leg, 0)}/${Legs.channel(leg, 1)}/${Legs.channel(leg, 2)}", color = Muted, fontFamily = Mono, fontSize = 13.sp)
    }
    for (j in 0 until 3) JointRow(vm, leg * 3 + j, Legs.JOINTS[j], color)
}

@Composable
private fun JointRow(vm: HexapodViewModel, i: Int, name: String, color: Color) {
    val value = vm.pulses[i]
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(name, color = TextMain, fontWeight = FontWeight.Bold, fontSize = 15.sp, modifier = Modifier.width(52.dp))
            Btn("−", height = 36) { vm.nudgeJoint(i, -10) }
            Text("S${i + 1}", color = color, fontWeight = FontWeight.Bold, fontSize = 15.sp)
            Btn("+", height = 36) { vm.nudgeJoint(i, 10) }
            Text("$value µs", color = TextMain, fontWeight = FontWeight.Bold, fontSize = 15.sp, textAlign = TextAlign.End, modifier = Modifier.weight(1f))
            Btn("1500", height = 36, fontSize = 13) { vm.setJoint(i, 1500) }
        }
        // Local slider position while dragging, so the thumb doesn't jitter behind the send queue.
        var drag by remember { mutableFloatStateOf(Float.NaN) }
        Slider(
            value = if (drag.isNaN()) value.toFloat() else drag,
            onValueChange = {
                drag = it
                vm.setJoint(i, (it / 10).roundToInt() * 10)
            },
            onValueChangeFinished = { drag = Float.NaN },
            valueRange = Legs.MIN_US.toFloat()..Legs.MAX_US.toFloat(),
            colors = SliderDefaults.colors(thumbColor = color, activeTrackColor = color, inactiveTrackColor = Line),
        )
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            Text("dir", color = Muted, fontSize = 14.sp)
            Btn(if (vm.cal.dir[i] > 0) "+1" else "−1", height = 34, fontSize = 13) { vm.flipDir(i) }
            Spacer(Modifier.weight(1f))
            Text("trim", color = Muted, fontSize = 14.sp)
            Btn("−10", height = 34, fontSize = 13) { vm.nudgeTrim(i, -10) }
            Text("%+d".format(vm.cal.trim[i]), color = TextMain, fontFamily = Mono, fontSize = 14.sp, textAlign = TextAlign.Center, modifier = Modifier.width(48.dp))
            Btn("+10", height = 34, fontSize = 13) { vm.nudgeTrim(i, 10) }
        }
    }
}

// ---- Calibration ------------------------------------------------------------------------------

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun CalibrationCard(vm: HexapodViewModel) = Card {
    val context = LocalContext.current
    var confirmReset by remember { mutableStateOf(false) }
    Row(verticalAlignment = Alignment.CenterVertically) {
        Text("Calibration", color = TextMain, fontWeight = FontWeight.Bold, fontSize = 18.sp, modifier = Modifier.weight(1f))
        Text(if (vm.unsaved) "unsaved" else "saved", color = if (vm.unsaved) Yellow else Muted, fontSize = 14.sp, fontWeight = FontWeight.Bold)
    }
    Text(
        "Center all → fit horns (coxa straight out, femur level, tibia straight down) → Stand. " +
            "A joint moving the wrong way: flip its dir. Small offsets: trim (≈11 µs per degree).",
        color = Muted, fontSize = 14.sp,
    )
    val c = vm.cal
    LengthRow("coxa length", c.coxa, 1) { vm.setLengths(coxa = it) }
    LengthRow("femur length", c.femur, 1) { vm.setLengths(femur = it) }
    LengthRow("tibia length", c.tibia, 1) { vm.setLengths(tibia = it) }
    LengthRow("step length", c.step, 5) { vm.setLengths(step = it) }
    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        Btn("Save", Modifier.weight(1f), fill = Yellow, height = 52) {
            vm.saveCalibration()
            Toast.makeText(context, "Calibration saved", Toast.LENGTH_SHORT).show()
        }
        Btn("Reset defaults", Modifier.weight(1f), textColor = Red, height = 52) { confirmReset = true }
    }
    Text("For python/hexapod.py (long-press to copy):", color = TextMain, fontSize = 14.sp)
    val export = c.pythonExport()
    Text(
        export,
        color = TextMain, fontFamily = Mono, fontSize = 13.sp,
        modifier = Modifier.combinedClickable(onClick = {}, onLongClick = {
            val cm = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            cm.setPrimaryClip(ClipData.newPlainText("hexapod calibration", export))
            Toast.makeText(context, "Copied", Toast.LENGTH_SHORT).show()
        }),
    )
    if (confirmReset) {
        AlertDialog(
            onDismissRequest = { confirmReset = false },
            title = { Text("Reset calibration?") },
            text = { Text("Lengths, dir and trim go back to defaults. Nothing is saved until you tap Save.") },
            confirmButton = { TextButton({ vm.resetCalibration(); confirmReset = false }) { Text("Reset", color = Red) } },
            dismissButton = { TextButton({ confirmReset = false }) { Text("Cancel") } },
        )
    }
}

@Composable
private fun LengthRow(label: String, value: Int, step: Int, onChange: (Int) -> Unit) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(label, color = TextMain, fontSize = 16.sp, modifier = Modifier.weight(1f))
        Btn("−$step", height = 40) { onChange(value - step) }
        Text("$value mm", color = TextMain, fontFamily = Mono, fontSize = 15.sp, textAlign = TextAlign.Center, modifier = Modifier.width(72.dp))
        Btn("+$step", height = 40) { onChange(value + step) }
    }
}

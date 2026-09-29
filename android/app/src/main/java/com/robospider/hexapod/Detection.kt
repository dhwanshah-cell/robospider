package com.robospider.hexapod

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.Bitmap
import android.graphics.Matrix
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.SystemClock
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import com.google.mediapipe.framework.image.BitmapImageBuilder
import com.google.mediapipe.tasks.core.BaseOptions
import com.google.mediapipe.tasks.vision.core.RunningMode
import com.google.mediapipe.tasks.vision.objectdetector.ObjectDetector
import org.tensorflow.lite.Interpreter
import java.io.ByteArrayOutputStream
import java.io.FileInputStream
import java.nio.channels.FileChannel

/**
 * Looks for people in camera frames with EfficientDet-Lite0 (COCO "person"), about
 * 5 frames a second. Keeps the latest frame so an alert can attach a photo.
 */
class PersonDetector(context: Context, private val onResult: (score: Float, fps: Float) -> Unit) :
    ImageAnalysis.Analyzer {

    /** Why the detector couldn't start, shown in place of the score. */
    var error: String? = null
        private set

    private val detector: ObjectDetector? = try {
        ObjectDetector.createFromOptions(
            context,
            ObjectDetector.ObjectDetectorOptions.builder()
                .setBaseOptions(BaseOptions.builder().setModelAssetPath("efficientdet_lite0.tflite").build())
                .setRunningMode(RunningMode.IMAGE)
                .setMaxResults(3)
                .setScoreThreshold(0.05f)
                .setCategoryAllowlist(listOf("person"))
                .build(),
        )
    } catch (e: Throwable) {
        error = "${e.javaClass.simpleName} ${e.message ?: ""}".trim()
        null
    }
    val available get() = detector != null

    @Volatile
    private var lastFrame: Bitmap? = null
    private var lastRun = 0L
    private var fps = 0f

    override fun analyze(image: ImageProxy) {
        val now = SystemClock.elapsedRealtime()
        if (now - lastRun < 190) {
            image.close()
            return
        }
        val dt = now - lastRun
        lastRun = now
        val frame = try {
            val raw = image.toBitmap()
            val rot = image.imageInfo.rotationDegrees
            if (rot == 0) raw
            else Bitmap.createBitmap(raw, 0, 0, raw.width, raw.height, Matrix().apply { postRotate(rot.toFloat()) }, true)
        } catch (e: Exception) {
            null
        } finally {
            image.close()
        }
        frame ?: return
        lastFrame = frame
        val det = detector ?: return onResult(0f, 0f)
        val score = try {
            det.detect(BitmapImageBuilder(frame).build()).detections()
                .maxOfOrNull { d -> d.categories().maxOfOrNull { it.score() } ?: 0f } ?: 0f
        } catch (e: Exception) {
            0f
        }
        if (dt in 1..5000) fps = 0.7f * fps + 0.3f * (1000f / dt)
        onResult(score, fps)
    }

    fun snapshotJpeg(): ByteArray? {
        val bmp = lastFrame ?: return null
        val scale = 960f / maxOf(bmp.width, bmp.height)
        val out = if (scale < 1f) Bitmap.createScaledBitmap(bmp, (bmp.width * scale).toInt(), (bmp.height * scale).toInt(), true) else bmp
        return ByteArrayOutputStream().also { out.compress(Bitmap.CompressFormat.JPEG, 80, it) }.toByteArray()
    }

    fun close() = detector?.close()
}

/** Classifies what the microphone hears with YAMNet (521 AudioSet classes), twice a second. */
class SoundListener(private val context: Context, private val onResult: (label: String, score: Float) -> Unit) {
    private var thread: Thread? = null

    @SuppressLint("MissingPermission")
    fun start() {
        if (thread != null) return
        val previous = stopping
        thread = Thread({
            // The last listener may still hold the microphone for up to one read.
            previous?.join(2000)
            val interpreter: Interpreter
            val labels: List<String>
            try {
                val fd = context.assets.openFd("yamnet.tflite")
                val model = FileInputStream(fd.fileDescriptor).channel
                    .map(FileChannel.MapMode.READ_ONLY, fd.startOffset, fd.declaredLength)
                interpreter = Interpreter(model, Interpreter.Options().setNumThreads(2))
                labels = context.assets.open("yamnet_labels.txt").bufferedReader().readLines()
            } catch (e: Throwable) {
                onResult("error: ${e.javaClass.simpleName} ${e.message ?: ""}".trim(), 0f)
                return@Thread
            }
            val rate = 16000
            val window = 15600 // YAMNet's 0.975 s input
            val minBuf = AudioRecord.getMinBufferSize(rate, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
            val rec = try {
                AudioRecord(
                    MediaRecorder.AudioSource.MIC, rate, AudioFormat.CHANNEL_IN_MONO,
                    AudioFormat.ENCODING_PCM_16BIT, maxOf(minBuf, window * 2),
                ).also { it.startRecording() }
            } catch (e: Throwable) {
                interpreter.close()
                onResult("no mic (${e.javaClass.simpleName})", 0f)
                return@Thread
            }
            if (rec.recordingState != AudioRecord.RECORDSTATE_RECORDING) {
                rec.release()
                interpreter.close()
                onResult("no mic (busy or not allowed)", 0f)
                return@Thread
            }
            val wave = FloatArray(window) // last ~1 s of audio, oldest first
            val hop = ShortArray(rate / 2)
            val scores = Array(1) { FloatArray(labels.size.coerceAtLeast(521)) }
            try {
                while (!Thread.currentThread().isInterrupted) {
                    val n = rec.read(hop, 0, hop.size)
                    if (n <= 0) continue
                    System.arraycopy(wave, n, wave, 0, window - n)
                    for (k in 0 until n) wave[window - n + k] = hop[k] / 32768f
                    interpreter.run(wave, scores)
                    val s = scores[0]
                    var best = 0
                    for (k in s.indices) if (s[k] > s[best]) best = k
                    onResult(labels.getOrElse(best) { "class $best" }, s[best])
                }
            } catch (e: Throwable) {
                if (!Thread.currentThread().isInterrupted) onResult("error: ${e.javaClass.simpleName}", 0f)
            } finally {
                rec.stop()
                rec.release()
                interpreter.close()
            }
        }, "sound-listener").apply { isDaemon = true; start() }
    }

    private var stopping: Thread? = null

    fun stop() {
        stopping = thread?.also { it.interrupt() }
        thread = null
    }

    companion object {
        /** YAMNet classes that suggest someone who needs help. */
        val HUMAN_SOUNDS = setOf(
            "Speech", "Shout", "Yell", "Screaming", "Crying, sobbing", "Baby cry, infant cry", "Whimper",
            "Groan", "Gasp", "Children shouting", "Babbling", "Conversation", "Narration, monologue",
            "Whistling", "Knock", "Tap", "Clapping", "Cough", "Wail, moan", "Sigh", "Child speech, kid speaking",
        )
    }
}

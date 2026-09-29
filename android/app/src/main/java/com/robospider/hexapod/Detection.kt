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
import com.google.mediapipe.tasks.audio.audioclassifier.AudioClassifier
import com.google.mediapipe.tasks.components.containers.AudioData
import com.google.mediapipe.tasks.core.BaseOptions
import com.google.mediapipe.tasks.vision.core.RunningMode
import com.google.mediapipe.tasks.vision.objectdetector.ObjectDetector
import java.io.ByteArrayOutputStream

/**
 * Looks for people in camera frames with EfficientDet-Lite0 (COCO "person"), about
 * 5 frames a second. Keeps the latest frame so an alert can attach a photo.
 */
class PersonDetector(context: Context, private val onResult: (score: Float, fps: Float) -> Unit) :
    ImageAnalysis.Analyzer {

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
    } catch (e: Exception) {
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
        thread = Thread({
            val classifier = try {
                AudioClassifier.createFromOptions(
                    context,
                    AudioClassifier.AudioClassifierOptions.builder()
                        .setBaseOptions(BaseOptions.builder().setModelAssetPath("yamnet.tflite").build())
                        .setMaxResults(1)
                        .build(),
                )
            } catch (e: Exception) {
                onResult("unavailable", 0f)
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
            } catch (e: Exception) {
                classifier.close()
                onResult("no mic", 0f)
                return@Thread
            }
            val format = AudioData.AudioDataFormat.builder().setNumOfChannels(1).setSampleRate(rate.toFloat()).build()
            val audio = AudioData.create(format, window)
            val hop = ShortArray(rate / 2)
            try {
                while (!Thread.currentThread().isInterrupted) {
                    val n = rec.read(hop, 0, hop.size)
                    if (n <= 0) continue
                    audio.load(hop, 0, n) // ring buffer: keeps the last `window` samples
                    val top = classifier.classify(audio).classificationResults().firstOrNull()
                        ?.classifications()?.firstOrNull()?.categories()?.firstOrNull()
                    if (top != null) onResult(top.categoryName(), top.score())
                }
            } catch (_: Exception) {
            } finally {
                rec.stop()
                rec.release()
                classifier.close()
            }
        }, "sound-listener").apply { isDaemon = true; start() }
    }

    fun stop() {
        thread?.interrupt()
        thread = null
    }

    companion object {
        /** YAMNet classes that suggest someone who needs help. */
        val HUMAN_SOUNDS = setOf(
            "Speech", "Shout", "Yell", "Screaming", "Crying, sobbing", "Baby cry, infant cry", "Whimper",
            "Groan", "Gasp", "Children shouting", "Babbling", "Conversation", "Narration, monologue",
            "Whistling", "Knock", "Tap", "Clapping", "Cough", "Wail, moan", "Sigh", "Female speech, woman speaking",
            "Male speech, man speaking", "Child speech, kid speaking",
        )
    }
}

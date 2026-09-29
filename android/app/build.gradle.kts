import java.net.URI
import java.text.SimpleDateFormat
import java.util.Date
import java.util.TimeZone

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

// Bump versionCode for every build you install over the last one.
val appVersionCode = 1
val appVersionName = "0.1.0"
val buildStamp: String = SimpleDateFormat("yyyyMMdd-HHmm").apply {
    timeZone = TimeZone.getTimeZone("Asia/Kolkata")
}.format(Date())

android {
    namespace = "com.robospider.hexapod"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.robospider.hexapod"
        minSdk = 24
        targetSdk = 35
        versionCode = appVersionCode
        versionName = appVersionName
        // 64-bit ARM phones only; drops the 32-bit and emulator copies of the MediaPipe libraries.
        ndk { abiFilters += listOf("arm64-v8a") }
        buildConfigField("String", "BUILD_STAMP", "\"b%03d-%s\"".format(appVersionCode, buildStamp))
    }

    signingConfigs {
        // A committed debug key, so CI builds and local builds install over each other.
        getByName("debug") {
            storeFile = file("debug.keystore")
            storePassword = "android"
            keyAlias = "androiddebugkey"
            keyPassword = "android"
        }
    }

    buildTypes {
        debug {
            signingConfig = signingConfigs.getByName("debug")
        }
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("debug")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
    // Compress the MediaPipe native libraries: a much smaller APK to download.
    packaging {
        jniLibs.useLegacyPackaging = true
    }
    androidResources {
        noCompress += "tflite"
    }
}

// On-device models: person detector (COCO EfficientDet-Lite0) and sound classifier (YAMNet).
val models = mapOf(
    "efficientdet_lite0.tflite" to
        "https://storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite0/int8/latest/efficientdet_lite0.tflite",
    "yamnet.tflite" to
        "https://storage.googleapis.com/mediapipe-models/audio_classifier/yamnet/float32/latest/yamnet.tflite",
)
val downloadModels by tasks.registering {
    val assets = layout.projectDirectory.dir("src/main/assets")
    outputs.files(models.keys.map { assets.file(it) })
    doLast {
        models.forEach { (name, url) ->
            val out = assets.file(name).asFile
            if (!out.exists() || out.length() == 0L) {
                out.parentFile.mkdirs()
                logger.lifecycle("Downloading $name")
                URI(url).toURL().openStream().use { input -> out.outputStream().use { input.copyTo(it) } }
            }
        }
    }
}
tasks.named("preBuild") { dependsOn(downloadModels) }

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.10.01")
    implementation(composeBom)
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.7")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")

    val camerax = "1.4.0"
    implementation("androidx.camera:camera-core:$camerax")
    implementation("androidx.camera:camera-camera2:$camerax")
    implementation("androidx.camera:camera-lifecycle:$camerax")
    implementation("androidx.camera:camera-view:$camerax")

    implementation("com.github.mik3y:usb-serial-for-android:3.8.1")
    implementation("com.google.mediapipe:tasks-vision:0.10.14")
    implementation("com.google.mediapipe:tasks-audio:0.10.14")

    testImplementation("junit:junit:4.13.2")
}

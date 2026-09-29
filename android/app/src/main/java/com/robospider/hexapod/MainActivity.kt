package com.robospider.hexapod

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.hardware.usb.UsbManager
import android.os.Bundle
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.runtime.mutableStateOf
import androidx.core.content.ContextCompat
import com.robospider.hexapod.ui.HexapodScreen

class MainActivity : ComponentActivity() {
    private val vm: HexapodViewModel by viewModels()
    private val cameraGranted = mutableStateOf(false)

    private val askPermissions =
        registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { result ->
            cameraGranted.value = granted(Manifest.permission.CAMERA)
            if (result[Manifest.permission.RECORD_AUDIO] == true) vm.startListening()
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        // The phone rides on the robot; don't let the screen sleep mid-patrol.
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        cameraGranted.value = granted(Manifest.permission.CAMERA)
        askPermissions.launch(
            arrayOf(
                Manifest.permission.CAMERA,
                Manifest.permission.RECORD_AUDIO,
                Manifest.permission.ACCESS_FINE_LOCATION,
                Manifest.permission.ACCESS_COARSE_LOCATION,
            ),
        )
        handleUsbIntent(intent)
        setContent { HexapodScreen(vm, cameraGranted.value) }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleUsbIntent(intent)
    }

    private fun handleUsbIntent(intent: Intent?) {
        // Launched by plugging in the USC-32: Android has already granted access.
        if (intent?.action == UsbManager.ACTION_USB_DEVICE_ATTACHED) vm.connect() else vm.refreshUsb()
    }

    override fun onStart() {
        super.onStart()
        if (granted(Manifest.permission.RECORD_AUDIO)) vm.startListening()
    }

    override fun onStop() {
        vm.stopListening()
        super.onStop()
    }

    private fun granted(p: String) = ContextCompat.checkSelfPermission(this, p) == PackageManager.PERMISSION_GRANTED
}

package com.neptunalarm.neptun_alarm_app

import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.PowerManager
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.provider.Settings
import android.view.HapticFeedbackConstants
import android.view.WindowManager
import androidx.core.view.WindowCompat
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private val CHANNEL = "ua.neptun.app/android"
    
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL).setMethodCallHandler { call, result ->
            when (call.method) {
                // Haptic feedback
                "haptic" -> {
                    val type = call.argument<String>("type") ?: "light"
                    performHaptic(type)
                    result.success(null)
                }
                
                // Vibration pattern
                "vibrate" -> {
                    val pattern = call.argument<List<Long>>("pattern")
                    if (pattern != null) {
                        vibratePattern(pattern.toLongArray())
                    } else {
                        vibrate(call.argument<Long>("duration") ?: 100L)
                    }
                    result.success(null)
                }
                
                // Check battery optimization status
                "isBatteryOptimizationDisabled" -> {
                    result.success(isBatteryOptimizationDisabled())
                }
                
                // Request disable battery optimization
                "requestDisableBatteryOptimization" -> {
                    requestDisableBatteryOptimization()
                    result.success(null)
                }
                
                // Clear notification badge
                "clearBadge" -> {
                    clearNotificationBadge()
                    result.success(null)
                }
                
                // Set badge count
                "setBadge" -> {
                    val count = call.argument<Int>("count") ?: 0
                    setNotificationBadge(count)
                    result.success(null)
                }
                
                // Get device info
                "getDeviceInfo" -> {
                    result.success(getDeviceInfo())
                }
                
                // Keep screen on
                "keepScreenOn" -> {
                    val enable = call.argument<Boolean>("enable") ?: false
                    keepScreenOn(enable)
                    result.success(null)
                }
                
                // Check DND permission
                "canBypassDnd" -> {
                    result.success(canBypassDnd())
                }
                
                // Open app settings
                "openAppSettings" -> {
                    openAppSettings()
                    result.success(null)
                }
                
                // Open notification settings
                "openNotificationSettings" -> {
                    openNotificationSettings()
                    result.success(null)
                }
                
                else -> result.notImplemented()
            }
        }
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Edge-to-edge display
        WindowCompat.setDecorFitsSystemWindows(window, false)
    }
    
    private fun performHaptic(type: String) {
        val view = window.decorView
        val feedbackConstant = when (type) {
            "light" -> HapticFeedbackConstants.KEYBOARD_TAP
            "medium" -> HapticFeedbackConstants.VIRTUAL_KEY
            "heavy" -> HapticFeedbackConstants.LONG_PRESS
            "selection" -> HapticFeedbackConstants.TEXT_HANDLE_MOVE
            "success" -> HapticFeedbackConstants.CONFIRM
            "warning" -> HapticFeedbackConstants.REJECT
            "error" -> HapticFeedbackConstants.REJECT
            else -> HapticFeedbackConstants.KEYBOARD_TAP
        }
        view.performHapticFeedback(feedbackConstant)
    }
    
    private fun vibrate(durationMs: Long) {
        val vibrator = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val vibratorManager = getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as VibratorManager
            vibratorManager.defaultVibrator
        } else {
            @Suppress("DEPRECATION")
            getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
        }
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            vibrator.vibrate(VibrationEffect.createOneShot(durationMs, VibrationEffect.DEFAULT_AMPLITUDE))
        } else {
            @Suppress("DEPRECATION")
            vibrator.vibrate(durationMs)
        }
    }
    
    private fun vibratePattern(pattern: LongArray) {
        val vibrator = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val vibratorManager = getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as VibratorManager
            vibratorManager.defaultVibrator
        } else {
            @Suppress("DEPRECATION")
            getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
        }
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            vibrator.vibrate(VibrationEffect.createWaveform(pattern, -1))
        } else {
            @Suppress("DEPRECATION")
            vibrator.vibrate(pattern, -1)
        }
    }
    
    private fun isBatteryOptimizationDisabled(): Boolean {
        val powerManager = getSystemService(Context.POWER_SERVICE) as PowerManager
        return powerManager.isIgnoringBatteryOptimizations(packageName)
    }
    
    private fun requestDisableBatteryOptimization() {
        if (!isBatteryOptimizationDisabled()) {
            val intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
                data = Uri.parse("package:$packageName")
            }
            startActivity(intent)
        }
    }
    
    private fun clearNotificationBadge() {
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        notificationManager.cancelAll()
    }
    
    private fun setNotificationBadge(count: Int) {
        // Badge count on Android is handled by notifications
    }
    
    private fun getDeviceInfo(): Map<String, Any> {
        return mapOf(
            "manufacturer" to Build.MANUFACTURER,
            "model" to Build.MODEL,
            "brand" to Build.BRAND,
            "device" to Build.DEVICE,
            "sdkInt" to Build.VERSION.SDK_INT,
            "release" to Build.VERSION.RELEASE,
            "product" to Build.PRODUCT,
            "hardware" to Build.HARDWARE,
            "isEmulator" to isEmulator()
        )
    }
    
    private fun isEmulator(): Boolean {
        return (Build.FINGERPRINT.startsWith("generic")
                || Build.FINGERPRINT.startsWith("unknown")
                || Build.MODEL.contains("google_sdk")
                || Build.MODEL.contains("Emulator")
                || Build.MODEL.contains("Android SDK built for x86")
                || Build.MANUFACTURER.contains("Genymotion")
                || Build.BRAND.startsWith("generic") && Build.DEVICE.startsWith("generic")
                || "google_sdk" == Build.PRODUCT)
    }
    
    private fun keepScreenOn(enable: Boolean) {
        runOnUiThread {
            if (enable) {
                window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
            } else {
                window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
            }
        }
    }
    
    private fun canBypassDnd(): Boolean {
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        return notificationManager.isNotificationPolicyAccessGranted
    }
    
    private fun openAppSettings() {
        val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
            data = Uri.parse("package:$packageName")
        }
        startActivity(intent)
    }
    
    private fun openNotificationSettings() {
        val intent = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).apply {
                putExtra(Settings.EXTRA_APP_PACKAGE, packageName)
            }
        } else {
            Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                data = Uri.parse("package:$packageName")
            }
        }
        startActivity(intent)
    }
}

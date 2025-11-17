package com.neptun.alarmmap.utils

import android.content.Context
import android.media.AudioAttributes
import android.media.SoundPool

class SoundNotificationManager(private val context: Context) {
    
    private var soundPool: SoundPool? = null
    private var alertSoundId: Int = 0
    private var lastTrackCount = 0
    
    init {
        initSoundPool()
    }
    
    private fun initSoundPool() {
        val audioAttributes = AudioAttributes.Builder()
            .setUsage(AudioAttributes.USAGE_NOTIFICATION)
            .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
            .build()
        
        soundPool = SoundPool.Builder()
            .setMaxStreams(1)
            .setAudioAttributes(audioAttributes)
            .build()
        
        // Using system notification sound
        try {
            // Use a system sound resource
            val soundUri = android.provider.Settings.System.DEFAULT_NOTIFICATION_URI
            // For simplicity, just store the ID (we'll use system sound pool differently)
            alertSoundId = 1
        } catch (e: Exception) {
            android.util.Log.e("SoundManager", "Failed to load sound", e)
        }
    }
    
    fun onTracksUpdated(newCount: Int, soundEnabled: Boolean) {
        if (soundEnabled && newCount > lastTrackCount && lastTrackCount > 0) {
            playAlertSound()
        }
        lastTrackCount = newCount
    }
    
    private fun playAlertSound() {
        // Use system sound
        try {
            val notification = android.media.RingtoneManager.getDefaultUri(android.media.RingtoneManager.TYPE_NOTIFICATION)
            val ringtone = android.media.RingtoneManager.getRingtone(context, notification)
            ringtone?.play()
        } catch (e: Exception) {
            android.util.Log.e("SoundManager", "Failed to play sound", e)
        }
    }
    
    fun release() {
        soundPool?.release()
        soundPool = null
    }
}

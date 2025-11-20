package com.neptun.alarmmap

import android.app.Application
import android.util.Log

class NeptunApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        // Initialize AdMob SDK
        AdMobHelper.initialize(this) { status ->
            Log.d("NeptunApp", "AdMob initialized: ${status.adapterStatusMap}")
        }
    }
}

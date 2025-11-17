package com.neptun.alarmmap

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import com.neptun.alarmmap.ui.components.UpdateAvailableDialog
import com.neptun.alarmmap.ui.screens.MainScreenWithNavigation
import com.neptun.alarmmap.ui.theme.NeptunAlarmMapTheme
import com.neptun.alarmmap.utils.AutoUpdateChecker

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        
        setContent {
            NeptunAlarmMapTheme {
                var showUpdateDialog by remember { mutableStateOf(false) }
                var isFlexibleUpdate by remember { mutableStateOf(true) }
                var isImmediateUpdate by remember { mutableStateOf(false) }
                
                // Автоматична перевірка оновлень при запуску
                AutoUpdateChecker(
                    checkOnStart = true,
                    onUpdateAvailable = { flexible, immediate ->
                        isFlexibleUpdate = flexible
                        isImmediateUpdate = immediate
                        showUpdateDialog = true
                    }
                )
                
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    MainScreenWithNavigation()
                }
                
                // Діалог оновлення
                if (showUpdateDialog) {
                    UpdateAvailableDialog(
                        isFlexible = isFlexibleUpdate,
                        isImmediate = isImmediateUpdate,
                        onDismiss = { showUpdateDialog = false },
                        onUpdate = { showUpdateDialog = false }
                    )
                }
            }
        }
    }
}

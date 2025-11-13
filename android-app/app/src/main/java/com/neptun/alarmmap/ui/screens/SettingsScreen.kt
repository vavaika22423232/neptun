package com.neptun.alarmmap.ui.screens

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.neptun.alarmmap.data.PreferencesManager

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen() {
    val context = LocalContext.current
    val prefsManager = remember { PreferencesManager.getInstance(context) }
    
    val autoRefreshEnabled by prefsManager.autoRefreshEnabled.collectAsState()
    val showTrajectories by prefsManager.showTrajectories.collectAsState()
    val notificationsEnabled by prefsManager.notificationsEnabled.collectAsState()
    val showBorders by prefsManager.showBorders.collectAsState()
    val showMask by prefsManager.showMask.collectAsState()
    val refreshInterval by prefsManager.refreshInterval.collectAsState()
    
    var showClearDialog by remember { mutableStateOf(false) }
    var showIntervalDialog by remember { mutableStateOf(false) }
    
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                androidx.compose.ui.graphics.Brush.verticalGradient(
                    colors = listOf(
                        Color(0xFF0f172a),
                        Color(0xFF1e293b)
                    )
                )
            )
    ) {
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            item {
                Text(
                    text = "⚙️ Налаштування",
                    style = MaterialTheme.typography.headlineLarge,
                    fontWeight = FontWeight.Bold,
                    color = Color.White
                )
                Spacer(modifier = Modifier.height(8.dp))
            }
            
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = Color(0xCC1e293b)
                    ),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                ) {
                    Column(
                        modifier = Modifier.padding(20.dp),
                        verticalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        Text(
                            text = "🗺️ Карта",
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        )
                        
                        SettingSwitch(
                            icon = Icons.Default.Refresh,
                            title = "Авто-оновлення",
                            subtitle = "Оновлювати кожні $refreshInterval сек",
                            checked = autoRefreshEnabled,
                            onCheckedChange = { prefsManager.setAutoRefresh(it) }
                        )
                        
                        SettingItem(
                            icon = Icons.Default.DateRange,
                            title = "Інтервал оновлення",
                            subtitle = "$refreshInterval секунд",
                            onClick = { showIntervalDialog = true }
                        )
                        
                        SettingSwitch(
                            icon = Icons.Default.Home,
                            title = "Показувати траєкторії",
                            subtitle = "Відображати шляхи руху загроз",
                            checked = showTrajectories,
                            onCheckedChange = { prefsManager.setShowTrajectories(it) }
                        )
                        
                        SettingSwitch(
                            icon = Icons.Default.Check,
                            title = "Кордони України",
                            subtitle = "Показувати кордони на карті",
                            checked = showBorders,
                            onCheckedChange = { prefsManager.setShowBorders(it) }
                        )
                        
                        SettingSwitch(
                            icon = Icons.Default.Face,
                            title = "Затемнення",
                            subtitle = "Затемнювати території поза Україною",
                            checked = showMask,
                            onCheckedChange = { prefsManager.setShowMask(it) }
                        )
                    }
                }
            }
            
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = Color(0xCC1e293b)
                    ),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                ) {
                    Column(
                        modifier = Modifier.padding(20.dp),
                        verticalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        Text(
                            text = "🔔 Сповіщення",
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        )
                        
                        SettingSwitch(
                            icon = Icons.Default.Notifications,
                            title = "Push-сповіщення",
                            subtitle = "Отримувати сповіщення про нові загрози",
                            checked = notificationsEnabled,
                            onCheckedChange = { prefsManager.setNotifications(it) }
                        )
                        
                        Text(
                            text = "💡 Увімкніть сповіщення щоб отримувати інформацію про нові загрози в реальному часі",
                            style = MaterialTheme.typography.bodySmall,
                            color = Color.White.copy(alpha = 0.6f)
                        )
                    }
                }
            }
            
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = Color(0xCC1e293b)
                    ),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                ) {
                    Column(
                        modifier = Modifier.padding(20.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        Text(
                            text = "ℹ️ Про додаток",
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        )
                        
                        SettingItem(
                            icon = Icons.Default.Send,
                            title = "Telegram канал",
                            subtitle = "Підписатися на оновлення",
                            onClick = {
                                val intent = Intent(Intent.ACTION_VIEW, Uri.parse("https://t.me/+2X3wpJd-TKAwNzli"))
                                context.startActivity(intent)
                            }
                        )
                        
                        SettingItem(
                            icon = Icons.Default.Info,
                            title = "Версія додатку",
                            subtitle = "NEPTUN v1.0.0 (Build 1)",
                            onClick = {}
                        )
                        
                        SettingItem(
                            icon = Icons.Default.Star,
                            title = "Оцінити додаток",
                            subtitle = "Залишити відгук у Google Play",
                            onClick = {
                                try {
                                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse("market://details?id=com.neptun.alarmmap"))
                                    context.startActivity(intent)
                                } catch (e: Exception) {
                                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse("https://play.google.com/store/apps/details?id=com.neptun.alarmmap"))
                                    context.startActivity(intent)
                                }
                            }
                        )
                        
                        SettingItem(
                            icon = Icons.Default.Share,
                            title = "Поділитися додатком",
                            subtitle = "Розповісти друзям про NEPTUN",
                            onClick = {
                                val intent = Intent(Intent.ACTION_SEND).apply {
                                    type = "text/plain"
                                    putExtra(Intent.EXTRA_TEXT, "Спробуй NEPTUN - карта тривог України! https://t.me/+2X3wpJd-TKAwNzli")
                                }
                                context.startActivity(Intent.createChooser(intent, "Поділитися через"))
                            }
                        )
                    }
                }
            }
            
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = Color(0xCCdc2626)
                    ),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                ) {
                    Column(
                        modifier = Modifier.padding(20.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        Text(
                            text = "⚠️ Небезпечна зона",
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        )
                        
                        SettingItem(
                            icon = Icons.Default.Delete,
                            title = "Очистити кеш",
                            subtitle = "Скинути всі налаштування",
                            onClick = { showClearDialog = true },
                            tint = Color.White
                        )
                    }
                }
            }
            
            item {
                Spacer(modifier = Modifier.height(80.dp))
            }
        }
    }
    
    if (showIntervalDialog) {
        AlertDialog(
            onDismissRequest = { showIntervalDialog = false },
            title = {
                Text("Інтервал оновлення", fontWeight = FontWeight.Bold)
            },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    listOf(10, 15, 30, 60, 120).forEach { interval ->
                        TextButton(
                            onClick = {
                                prefsManager.setRefreshInterval(interval)
                                showIntervalDialog = false
                            },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(
                                "$interval секунд",
                                modifier = Modifier.fillMaxWidth(),
                                style = MaterialTheme.typography.bodyLarge
                            )
                        }
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = { showIntervalDialog = false }) {
                    Text("Закрити")
                }
            }
        )
    }
    
    if (showClearDialog) {
        AlertDialog(
            onDismissRequest = { showClearDialog = false },
            icon = {
                Icon(
                    imageVector = Icons.Default.Warning,
                    contentDescription = null,
                    tint = Color(0xFFef4444),
                    modifier = Modifier.size(48.dp)
                )
            },
            title = {
                Text("Очистити кеш?", fontWeight = FontWeight.Bold)
            },
            text = {
                Text("Всі налаштування будуть скинуті до значень за замовчуванням. Ця дія незворотна.")
            },
            confirmButton = {
                Button(
                    onClick = {
                        prefsManager.clearCache()
                        showClearDialog = false
                    },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = Color(0xFFdc2626)
                    )
                ) {
                    Text("Очистити")
                }
            },
            dismissButton = {
                TextButton(onClick = { showClearDialog = false }) {
                    Text("Скасувати")
                }
            }
        )
    }
}

@Composable
fun SettingSwitch(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    title: String,
    subtitle: String,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(Color(0x22ffffff), RoundedCornerShape(12.dp))
            .padding(16.dp),
        horizontalArrangement = Arrangement.spacedBy(16.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            tint = Color(0xFF60a5fa),
            modifier = Modifier.size(28.dp)
        )
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                style = MaterialTheme.typography.bodyLarge,
                fontWeight = FontWeight.SemiBold,
                color = Color.White
            )
            Text(
                text = subtitle,
                style = MaterialTheme.typography.bodySmall,
                color = Color.White.copy(alpha = 0.6f)
            )
        }
        Switch(
            checked = checked,
            onCheckedChange = onCheckedChange,
            colors = SwitchDefaults.colors(
                checkedThumbColor = Color.White,
                checkedTrackColor = Color(0xFF10b981),
                uncheckedThumbColor = Color.White,
                uncheckedTrackColor = Color(0xFF64748b)
            )
        )
    }
}

@Composable
fun SettingItem(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    title: String,
    subtitle: String,
    onClick: () -> Unit,
    tint: Color = Color(0xFF60a5fa)
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(Color(0x22ffffff), RoundedCornerShape(12.dp))
            .clickable(onClick = onClick)
            .padding(16.dp),
        horizontalArrangement = Arrangement.spacedBy(16.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            tint = tint,
            modifier = Modifier.size(28.dp)
        )
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                style = MaterialTheme.typography.bodyLarge,
                fontWeight = FontWeight.SemiBold,
                color = Color.White
            )
            Text(
                text = subtitle,
                style = MaterialTheme.typography.bodySmall,
                color = Color.White.copy(alpha = 0.6f)
            )
        }
        Icon(
            imageVector = Icons.Default.KeyboardArrowRight,
            contentDescription = null,
            tint = Color.White.copy(alpha = 0.5f),
            modifier = Modifier.size(24.dp)
        )
    }
}

package com.neptun.alarmmap.ui.screens

import android.content.Intent
import android.net.Uri
import androidx.compose.animation.*
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.neptun.alarmmap.ui.theme.NeptunBlue
import kotlinx.coroutines.launch

@Composable
fun MainScreenWithNavigation() {
    var selectedTab by remember { mutableStateOf(0) }
    val context = LocalContext.current
    
    Scaffold(
        bottomBar = {
            BottomNavigationBar(
                selectedTab = selectedTab,
                onTabSelected = { 
                    selectedTab = it
                    // Open Telegram on tab 2
                    if (it == 2) {
                        val intent = Intent(Intent.ACTION_VIEW, Uri.parse("https://t.me/+2X3wpJd-TKAwNzli"))
                        context.startActivity(intent)
                    }
                }
            )
        }
    ) { paddingValues ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            when (selectedTab) {
                0 -> MapScreenOSM()
                1 -> StatsScreen()
                2 -> TelegramScreen()
                3 -> SettingsScreenContent()
            }
        }
    }
}

@Composable
fun BottomNavigationBar(
    selectedTab: Int,
    onTabSelected: (Int) -> Unit
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = Color.Transparent,
        shadowElevation = 24.dp
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(
                    Brush.verticalGradient(
                        colors = listOf(
                            Color(0xFF1a1f36),
                            Color(0xFF0f1419)
                        )
                    )
                )
                .padding(horizontal = 24.dp, vertical = 16.dp)
                .navigationBarsPadding() // Додає відступ для системної панелі
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                ModernNavItem(
                    icon = Icons.Default.Place,
                    label = "Карта",
                    selected = selectedTab == 0,
                    onClick = { onTabSelected(0) }
                )
                
                ModernNavItem(
                    icon = Icons.Default.DateRange,
                    label = "Статистика",
                    selected = selectedTab == 1,
                    onClick = { onTabSelected(1) }
                )
                
                // Telegram button with glowing effect
                TelegramFloatingButton(
                    selected = selectedTab == 2,
                    onClick = { onTabSelected(2) }
                )
                
                ModernNavItem(
                    icon = Icons.Default.Settings,
                    label = "Налаштування",
                    selected = selectedTab == 3,
                    onClick = { onTabSelected(3) }
                )
            }
        }
    }
}

@Composable
fun ModernNavItem(
    icon: ImageVector,
    label: String,
    selected: Boolean,
    onClick: () -> Unit
) {
    val scale by animateFloatAsState(
        targetValue = if (selected) 1.0f else 0.92f,
        animationSpec = spring(
            dampingRatio = Spring.DampingRatioMediumBouncy,
            stiffness = Spring.StiffnessMedium
        ),
        label = "scale"
    )
    
    val iconColor by animateColorAsState(
        targetValue = if (selected) Color(0xFF60a5fa) else Color(0xFF64748b),
        animationSpec = tween(300),
        label = "iconColor"
    )
    
    Column(
        modifier = Modifier
            .scale(scale)
            .clip(RoundedCornerShape(16.dp))
            .clickable(
                onClick = onClick,
                indication = null,
                interactionSource = remember { MutableInteractionSource() }
            )
            .background(
                if (selected) 
                    Brush.radialGradient(
                        colors = listOf(
                            Color(0xFF60a5fa).copy(alpha = 0.15f),
                            Color.Transparent
                        )
                    )
                else Brush.linearGradient(listOf(Color.Transparent, Color.Transparent))
            )
            .padding(horizontal = 12.dp, vertical = 10.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(6.dp)
    ) {
        Icon(
            imageVector = icon,
            contentDescription = label,
            tint = iconColor,
            modifier = Modifier.size(26.dp)
        )
        
        if (selected) {
            Text(
                text = label,
                fontSize = 12.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color(0xFF60a5fa),
                maxLines = 1
            )
        }
    }
}

@Composable
fun TelegramFloatingButton(
    selected: Boolean,
    onClick: () -> Unit
) {
    val infiniteTransition = rememberInfiniteTransition(label = "telegram_glow")
    val glowAlpha by infiniteTransition.animateFloat(
        initialValue = 0.3f,
        targetValue = 0.8f,
        animationSpec = infiniteRepeatable(
            animation = tween(1500, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "glow"
    )
    
    Box(
        contentAlignment = Alignment.Center,
        modifier = Modifier.size(64.dp)
    ) {
        // Glowing background
        Box(
            modifier = Modifier
                .size(60.dp)
                .background(
                    Brush.radialGradient(
                        colors = listOf(
                            Color(0xFF0088cc).copy(alpha = glowAlpha * 0.5f),
                            Color.Transparent
                        )
                    ),
                    shape = CircleShape
                )
        )
        
        // Main button
        Surface(
            modifier = Modifier
                .size(52.dp)
                .scale(if (selected) 1.05f else 1f),
            shape = CircleShape,
            color = Color.Transparent,
            shadowElevation = 12.dp,
            onClick = onClick
        ) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(
                        Brush.linearGradient(
                            colors = listOf(
                                Color(0xFF0088cc),
                                Color(0xFF006699)
                            )
                        )
                    ),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.Send,
                    contentDescription = "Telegram",
                    tint = Color.White,
                    modifier = Modifier
                        .size(28.dp)
                        .rotate(-45f)
                )
            }
        }
    }
}

@Composable
fun StatsScreen() {
    val context = LocalContext.current
    val viewModel = remember { com.neptun.alarmmap.ui.viewmodel.StatsViewModel(context) }
    val uiState by viewModel.uiState.collectAsState()
    
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    colors = listOf(
                        Color(0xFF0f172a),
                        Color(0xFF1e293b)
                    )
                )
            )
    ) {
        androidx.compose.foundation.lazy.LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Header
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Статистика",
                        style = MaterialTheme.typography.headlineMedium,
                        color = Color.White,
                        fontWeight = FontWeight.Bold
                    )
                    IconButton(onClick = { viewModel.loadStats() }) {
                        Icon(
                            imageVector = Icons.Default.Refresh,
                            contentDescription = "Оновити",
                            tint = NeptunBlue
                        )
                    }
                }
            }
            
            // Live Counters
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    LiveCounterCard(
                        title = "Активні",
                        count = uiState.todayCount,
                        icon = "🚨",
                        gradient = listOf(Color(0xFFef4444), Color(0xFFdc2626)),
                        modifier = Modifier.weight(1f)
                    )
                    LiveCounterCard(
                        title = "За тиждень",
                        count = uiState.weekCount,
                        icon = "📊",
                        gradient = listOf(Color(0xFFf59e0b), Color(0xFFd97706)),
                        modifier = Modifier.weight(1f)
                    )
                }
            }
            
            // Quick Stats Grid
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(20.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = Color(0xFF1e293b)
                    ),
                    elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
                ) {
                    Column(modifier = Modifier.padding(20.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = "Швидкі показники",
                                color = Color.White,
                                fontSize = 18.sp,
                                fontWeight = FontWeight.Bold
                            )
                            Surface(
                                shape = CircleShape,
                                color = NeptunBlue.copy(alpha = 0.2f),
                                modifier = Modifier.size(32.dp)
                            ) {
                                Box(contentAlignment = Alignment.Center) {
                                    Text(text = "⚡", fontSize = 16.sp)
                                }
                            }
                        }
                        
                        androidx.compose.foundation.layout.Spacer(modifier = Modifier.height(16.dp))
                        
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            QuickStatItem(
                                label = "Місяць",
                                value = uiState.monthCount.toString(),
                                modifier = Modifier.weight(1f)
                            )
                            QuickStatItem(
                                label = "Всього",
                                value = uiState.totalCount.toString(),
                                modifier = Modifier.weight(1f)
                            )
                        }
                    }
                }
            }
            
            // Most Active Regions
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(20.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF1e293b)),
                    elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
                ) {
                    Column(modifier = Modifier.padding(20.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = "Найбільш активні регіони",
                                color = Color.White,
                                fontSize = 18.sp,
                                fontWeight = FontWeight.Bold
                            )
                            Text(text = "🗺️", fontSize = 20.sp)
                        }
                        
                        androidx.compose.foundation.layout.Spacer(modifier = Modifier.height(16.dp))
                        
                        if (uiState.isLoading) {
                            Box(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(120.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                CircularProgressIndicator(color = NeptunBlue, strokeWidth = 3.dp)
                            }
                        } else {
                            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                RegionActivityBar("Київська обл.", 85, Color(0xFFef4444))
                                RegionActivityBar("Одеська обл.", 72, Color(0xFFf59e0b))
                                RegionActivityBar("Дніпропетровська обл.", 68, Color(0xFF3b82f6))
                            }
                        }
                    }
                }
            }
            
            // Threat types statistics
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(20.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF1e293b)),
                    elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
                ) {
                    Column(modifier = Modifier.padding(20.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = "Типи загроз",
                                color = Color.White,
                                fontSize = 18.sp,
                                fontWeight = FontWeight.Bold
                            )
                            Text(text = "🎯", fontSize = 20.sp)
                        }
                        
                        androidx.compose.foundation.layout.Spacer(modifier = Modifier.height(16.dp))
                        
                        if (uiState.isLoading) {
                            Box(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(200.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                CircularProgressIndicator(color = NeptunBlue, strokeWidth = 3.dp)
                            }
                        } else if (uiState.threatStats.isEmpty()) {
                            Box(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(120.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                Text(
                                    text = "Немає даних про загрози",
                                    color = Color.White.copy(alpha = 0.5f),
                                    fontSize = 14.sp
                                )
                            }
                        } else {
                            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                                uiState.threatStats.forEach { stat ->
                                    ThreatStatRow(stat)
                                }
                            }
                        }
                    }
                }
            }
            
            // Last update
            item {
                Text(
                    text = "Оновлено: ${uiState.lastUpdate}",
                    fontSize = 12.sp,
                    color = Color.White.copy(alpha = 0.5f),
                    modifier = Modifier.fillMaxWidth(),
                    textAlign = androidx.compose.ui.text.style.TextAlign.Center
                )
            }
        }
    }
}

@Composable
fun LiveCounterCard(
    title: String,
    count: Int,
    icon: String,
    gradient: List<Color>,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(
            containerColor = Color.Transparent
        )
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(
                    Brush.linearGradient(gradient)
                )
                .padding(16.dp)
        ) {
            Column {
                Text(
                    text = icon,
                    fontSize = 28.sp,
                    modifier = Modifier.padding(bottom = 8.dp)
                )
                Text(
                    text = count.toString(),
                    fontSize = 32.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color.White
                )
                Text(
                    text = title,
                    fontSize = 13.sp,
                    color = Color.White.copy(alpha = 0.9f)
                )
            }
        }
    }
}

@Composable
fun QuickStatItem(label: String, value: String, modifier: Modifier = Modifier) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(
            containerColor = Color.White.copy(alpha = 0.05f)
        )
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = value,
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
                color = NeptunBlue
            )
            Text(
                text = label,
                fontSize = 12.sp,
                color = Color.White.copy(alpha = 0.7f)
            )
        }
    }
}

@Composable
fun RegionActivityBar(region: String, percentage: Int, color: Color) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(
                text = region,
                color = Color.White,
                fontSize = 14.sp,
                fontWeight = FontWeight.Medium
            )
            Text(
                text = "$percentage%",
                color = color,
                fontSize = 14.sp,
                fontWeight = FontWeight.Bold
            )
        }
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(8.dp)
                .background(
                    Color.White.copy(alpha = 0.1f),
                    RoundedCornerShape(4.dp)
                )
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth(percentage / 100f)
                    .height(8.dp)
                    .background(
                        Brush.horizontalGradient(
                            listOf(color.copy(alpha = 0.8f), color)
                        ),
                        RoundedCornerShape(4.dp)
                    )
            )
        }
    }
}

@Composable
fun PeriodStat(label: String, count: Int) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(
            text = count.toString(),
            fontSize = 28.sp,
            fontWeight = FontWeight.Bold,
            color = NeptunBlue
        )
        Text(
            text = label,
            fontSize = 12.sp,
            color = Color.White.copy(alpha = 0.6f)
        )
    }
}

@Composable
fun ThreatStatRow(stat: com.neptun.alarmmap.ui.viewmodel.ThreatStats) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(
                Color.White.copy(alpha = 0.05f),
                RoundedCornerShape(8.dp)
            )
            .padding(12.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Text(
                text = stat.type.emoji,
                fontSize = 24.sp
            )
            Column {
                Text(
                    text = stat.type.displayName,
                    color = Color.White,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Medium
                )
                Text(
                    text = "${stat.percentage.toInt()}%",
                    color = Color.White.copy(alpha = 0.6f),
                    fontSize = 12.sp
                )
            }
        }
        Text(
            text = stat.count.toString(),
            fontSize = 20.sp,
            fontWeight = FontWeight.Bold,
            color = NeptunBlue
        )
    }
}

@Composable
fun StatsRow(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = label,
            color = Color.White.copy(alpha = 0.8f),
            fontSize = 14.sp
        )
        Text(
            text = value,
            color = NeptunBlue,
            fontSize = 18.sp,
            fontWeight = FontWeight.Bold
        )
    }
}

@Composable
fun TelegramScreen() {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    colors = listOf(
                        Color(0xFF0f172a),
                        Color(0xFF1e293b)
                    )
                )
            ),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(16.dp),
            modifier = Modifier.padding(24.dp)
        ) {
            Surface(
                shape = CircleShape,
                color = Color(0xFF0088cc),
                modifier = Modifier.size(80.dp)
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(
                        imageVector = Icons.Default.Send,
                        contentDescription = null,
                        tint = Color.White,
                        modifier = Modifier.size(40.dp)
                    )
                }
            }
            
            Text(
                text = "Telegram канал",
                style = MaterialTheme.typography.headlineMedium,
                color = Color.White,
                fontWeight = FontWeight.Bold
            )
            
            Text(
                text = "Приєднуйтесь до нашого Telegram каналу для отримання оперативних повідомлень про загрози",
                style = MaterialTheme.typography.bodyMedium,
                color = Color.White.copy(alpha = 0.7f),
                textAlign = TextAlign.Center
            )
        }
    }
}

@Composable
fun SettingsScreenContent() {
    val context = LocalContext.current
    val prefsManager = remember { com.neptun.alarmmap.data.PreferencesManager.getInstance(context) }
    val mapViewModel = remember { com.neptun.alarmmap.ui.viewmodel.MapViewModel(context = context) }
    val uiState by mapViewModel.uiState.collectAsState()
    
    val scope = rememberCoroutineScope()
    
    var showDonateDialog by remember { mutableStateOf(false) }
    
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    colors = listOf(
                        Color(0xFF0f172a),
                        Color(0xFF1e293b)
                    )
                )
            )
    ) {
        androidx.compose.foundation.lazy.LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Header with icon
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Surface(
                        shape = CircleShape,
                        color = NeptunBlue.copy(alpha = 0.2f),
                        modifier = Modifier.size(48.dp)
                    ) {
                        Box(contentAlignment = Alignment.Center) {
                            Text(text = "⚙️", fontSize = 24.sp)
                        }
                    }
                    Text(
                        text = "Налаштування",
                        style = MaterialTheme.typography.headlineMedium,
                        color = Color.White,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
            
            // Map Settings Section
            item {
                SettingsSection(
                    title = "Налаштування карти",
                    icon = "🗺️"
                ) {
                    SettingSwitchItem(
                        title = "Автооновлення",
                        description = "Оновлювати карту кожні 10 секунд",
                        checked = uiState.isAutoRefreshEnabled,
                        onCheckedChange = { enabled ->
                            scope.launch { prefsManager.setAutoRefresh(enabled) }
                        }
                    )
                    
                    androidx.compose.foundation.layout.Spacer(modifier = Modifier.height(12.dp))
                    
                    SettingSwitchItem(
                        title = "Показувати траєкторії",
                        description = "Відображати шляхи польоту загроз",
                        checked = true,
                        onCheckedChange = { }
                    )
                }
            }
            
            // Notifications Settings
            item {
                SettingsSection(
                    title = "Сповіщення",
                    icon = "🔔"
                ) {
                    SettingSwitchItem(
                        title = "Звукові сповіщення",
                        description = "Відтворювати звук при нових загрозах",
                        checked = uiState.isSoundEnabled,
                        onCheckedChange = { enabled ->
                            scope.launch { prefsManager.setSoundEnabled(enabled) }
                        }
                    )
                    
                    androidx.compose.foundation.layout.Spacer(modifier = Modifier.height(12.dp))
                    
                    SettingSwitchItem(
                        title = "Push-повідомлення",
                        description = "Отримувати сповіщення про нові загрози",
                        checked = false,
                        onCheckedChange = { }
                    )
                    
                    androidx.compose.foundation.layout.Spacer(modifier = Modifier.height(12.dp))
                    
                    SettingSwitchItem(
                        title = "Вібрація",
                        description = "Вібрувати при сповіщеннях",
                        checked = true,
                        onCheckedChange = { }
                    )
                }
            }
            
            // Threat Filters
            item {
                SettingsSection(
                    title = "Фільтри загроз",
                    icon = "🎯"
                ) {
                    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        com.neptun.alarmmap.data.model.ThreatType.values().forEach { type ->
                            ThreatFilterItem(
                                type = type,
                                enabled = type in uiState.enabledThreatTypes,
                                onToggle = { enabled ->
                                    scope.launch {
                                        prefsManager.toggleThreatType(type, enabled)
                                    }
                                }
                            )
                        }
                    }
                }
            }
            
            // Appearance
            item {
                SettingsSection(
                    title = "Вигляд",
                    icon = "🎨"
                ) {
                    SettingClickableItem(
                        title = "Темна тема",
                        description = "Активна",
                        onClick = { }
                    )
                    
                    androidx.compose.foundation.layout.Spacer(modifier = Modifier.height(12.dp))
                    
                    SettingClickableItem(
                        title = "Розмір маркерів",
                        description = "Середній",
                        onClick = { }
                    )
                }
            }
            
            // Support Section
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(20.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = Color.Transparent
                    )
                ) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(
                                Brush.linearGradient(
                                    listOf(Color(0xFFef4444), Color(0xFFdc2626))
                                )
                            )
                            .clickable { showDonateDialog = true }
                            .padding(20.dp)
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column {
                                Text(
                                    text = "💙 Підтримати проект",
                                    fontSize = 18.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color.White
                                )
                                androidx.compose.foundation.layout.Spacer(modifier = Modifier.height(4.dp))
                                Text(
                                    text = "Допоможіть покращити додаток",
                                    fontSize = 13.sp,
                                    color = Color.White.copy(alpha = 0.9f)
                                )
                            }
                            Icon(
                                imageVector = Icons.Default.KeyboardArrowRight,
                                contentDescription = null,
                                tint = Color.White,
                                modifier = Modifier.size(28.dp)
                            )
                        }
                    }
                }
            }
            
            // App Info
            item {
                SettingsSection(
                    title = "Про додаток",
                    icon = "ℹ️"
                ) {
                    InfoRow("Версія", "2.0.0")
                    androidx.compose.foundation.layout.Spacer(modifier = Modifier.height(8.dp))
                    InfoRow("Розробник", "Neptun Team")
                    androidx.compose.foundation.layout.Spacer(modifier = Modifier.height(8.dp))
                    InfoRow("Оновлено", "Листопад 2024")
                    androidx.compose.foundation.layout.Spacer(modifier = Modifier.height(8.dp))
                    InfoRow("Ліцензія", "Open Source")
                }
            }
            
            // Social Links
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(20.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF1e293b)),
                    elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
                ) {
                    Column(modifier = Modifier.padding(20.dp)) {
                        Text(
                            text = "Приєднуйтесь до спільноти",
                            color = Color.White,
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(bottom = 16.dp)
                        )
                        
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            SocialButton(
                                icon = "📱",
                                label = "Telegram",
                                modifier = Modifier.weight(1f),
                                onClick = { }
                            )
                            SocialButton(
                                icon = "🌐",
                                label = "Сайт",
                                modifier = Modifier.weight(1f),
                                onClick = { }
                            )
                        }
                    }
                }
            }
            
            // Footer spacing
            item {
                androidx.compose.foundation.layout.Spacer(modifier = Modifier.height(8.dp))
            }
        }
    }
}

@Composable
fun SettingsSection(
    title: String,
    icon: String,
    content: @Composable ColumnScope.() -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF1e293b)),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.padding(bottom = 16.dp)
            ) {
                Text(text = icon, fontSize = 20.sp)
                Text(
                    text = title,
                    color = Color.White,
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold
                )
            }
            content()
        }
    }
}

@Composable
fun SettingSwitchItem(
    title: String,
    description: String,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                color = Color.White,
                fontSize = 16.sp,
                fontWeight = FontWeight.Medium
            )
            androidx.compose.foundation.layout.Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = description,
                color = Color.White.copy(alpha = 0.6f),
                fontSize = 13.sp,
                lineHeight = 16.sp
            )
        }
        Switch(
            checked = checked,
            onCheckedChange = onCheckedChange,
            colors = SwitchDefaults.colors(
                checkedThumbColor = NeptunBlue,
                checkedTrackColor = NeptunBlue.copy(alpha = 0.5f),
                uncheckedThumbColor = Color.White.copy(alpha = 0.4f),
                uncheckedTrackColor = Color.White.copy(alpha = 0.2f)
            )
        )
    }
}

@Composable
fun SettingClickableItem(
    title: String,
    description: String,
    onClick: () -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                color = Color.White,
                fontSize = 16.sp,
                fontWeight = FontWeight.Medium
            )
            androidx.compose.foundation.layout.Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = description,
                color = NeptunBlue,
                fontSize = 13.sp
            )
        }
        Icon(
            imageVector = Icons.Default.KeyboardArrowRight,
            contentDescription = null,
            tint = Color.White.copy(alpha = 0.5f)
        )
    }
}

@Composable
fun ThreatFilterItem(
    type: com.neptun.alarmmap.data.model.ThreatType,
    enabled: Boolean,
    onToggle: (Boolean) -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(
                Color.White.copy(alpha = 0.05f),
                RoundedCornerShape(12.dp)
            )
            .padding(12.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            modifier = Modifier.weight(1f)
        ) {
            Surface(
                shape = CircleShape,
                color = if (enabled) NeptunBlue.copy(alpha = 0.2f) else Color.White.copy(alpha = 0.1f),
                modifier = Modifier.size(40.dp)
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Text(
                        text = type.emoji,
                        fontSize = 20.sp
                    )
                }
            }
            Text(
                text = type.displayName,
                color = Color.White,
                fontSize = 16.sp,
                fontWeight = if (enabled) FontWeight.Medium else FontWeight.Normal
            )
        }
        Checkbox(
            checked = enabled,
            onCheckedChange = onToggle,
            colors = CheckboxDefaults.colors(
                checkedColor = NeptunBlue,
                uncheckedColor = Color.White.copy(alpha = 0.3f),
                checkmarkColor = Color.White
            )
        )
    }
}

@Composable
fun SocialButton(
    icon: String,
    label: String,
    modifier: Modifier = Modifier,
    onClick: () -> Unit
) {
    Card(
        modifier = modifier.clickable(onClick = onClick),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(
            containerColor = NeptunBlue.copy(alpha = 0.2f)
        )
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(text = icon, fontSize = 18.sp)
            androidx.compose.foundation.layout.Spacer(modifier = Modifier.width(6.dp))
            Text(
                text = label,
                color = Color.White,
                fontSize = 14.sp,
                fontWeight = FontWeight.Medium
            )
        }
    }
}

@Composable
fun InfoRow(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(
            text = label,
            color = Color.White.copy(alpha = 0.6f),
            fontSize = 14.sp
        )
        Text(
            text = value,
            color = Color.White,
            fontSize = 14.sp,
            fontWeight = FontWeight.Medium
        )
    }
}

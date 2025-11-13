package com.neptun.alarmmap.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.viewmodel.compose.viewModel
import com.neptun.alarmmap.data.PreferencesManager
import com.neptun.alarmmap.ui.theme.NeptunBlue
import com.neptun.alarmmap.ui.viewmodel.MapViewModel
import com.mapbox.maps.MapView
import com.mapbox.maps.Style
import com.mapbox.maps.CameraOptions
import com.mapbox.geojson.Point

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MapScreenMapbox(viewModel: MapViewModel = viewModel()) {
    val context = LocalContext.current
    val prefsManager = remember { PreferencesManager.getInstance(context) }
    
    val uiState by viewModel.uiState.collectAsState()
    val autoRefreshEnabled by prefsManager.autoRefreshEnabled.collectAsState()
    val refreshInterval by prefsManager.refreshInterval.collectAsState()
    
    LaunchedEffect(Unit) {
        viewModel.loadAlarmEvents()
    }
    
    LaunchedEffect(autoRefreshEnabled, refreshInterval) {
        if (autoRefreshEnabled) {
            while (true) {
                kotlinx.coroutines.delay((refreshInterval * 1000).toLong())
                viewModel.loadAlarmEvents()
            }
        }
    }
    
    Box(modifier = Modifier.fillMaxSize()) {
        Card(
            modifier = Modifier.fillMaxSize(),
            shape = RoundedCornerShape(0.dp),
            elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
        ) {
            AndroidView(
                modifier = Modifier.fillMaxSize(),
                factory = { ctx ->
                    MapView(ctx).apply {
                        mapboxMap.loadStyle(
                            Style.Builder()
                                .fromUri("https://api.maptiler.com/maps/streets-v2/style.json?key=m8zW2kq1Ta7cw9nODPXo")
                                .build()
                        )
                        
                        // Set camera to Ukraine center
                        mapboxMap.setCamera(
                            CameraOptions.Builder()
                                .center(Point.fromLngLat(31.1656, 48.3794))
                                .zoom(5.5)
                                .build()
                        )
                    }
                },
                update = { mapView ->
                    // Update markers when events change
                }
            )
        }
        
        // Header with logo and refresh button
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
                .align(Alignment.TopCenter),
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(
                containerColor = Color(0xCC0f172a)
            ),
            elevation = CardDefaults.cardElevation(defaultElevation = 12.dp)
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "⚡ NEPTUN",
                    style = MaterialTheme.typography.headlineMedium,
                    fontWeight = FontWeight.Bold,
                    color = Color.White
                )
                
                Row(
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Surface(
                        shape = CircleShape,
                        color = NeptunBlue,
                        modifier = Modifier.size(36.dp)
                    ) {
                        Box(contentAlignment = Alignment.Center) {
                            Text(
                                text = "${uiState.events.size}",
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = FontWeight.Bold,
                                color = Color.White
                            )
                        }
                    }
                    
                    IconButton(
                        onClick = { viewModel.loadAlarmEvents() },
                        enabled = !uiState.isLoading
                    ) {
                        Icon(
                            imageVector = Icons.Default.Refresh,
                            contentDescription = "Refresh",
                            tint = if (uiState.isLoading) Color.Gray else Color.White
                        )
                    }
                }
            }
        }
        
        if (uiState.isLoading) {
            CircularProgressIndicator(
                modifier = Modifier
                    .size(48.dp)
                    .align(Alignment.Center),
                color = NeptunBlue
            )
        }
    }
}

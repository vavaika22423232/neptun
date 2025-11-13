package com.neptun.alarmmap.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.google.android.gms.maps.model.CameraPosition
import com.google.android.gms.maps.model.LatLng
import com.google.android.gms.maps.model.BitmapDescriptorFactory
import com.google.maps.android.compose.*
import com.neptun.alarmmap.data.model.AlarmEvent
import com.neptun.alarmmap.ui.theme.DarkBackground
import com.neptun.alarmmap.ui.theme.NeptunBlue
import com.neptun.alarmmap.ui.viewmodel.MapViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MapScreen(
    viewModel: MapViewModel = viewModel()
) {
    val uiState by viewModel.uiState.collectAsState()
    
    // Ukraine center coordinates
    val ukraineCenter = LatLng(48.3794, 31.1656)
    val cameraPositionState = rememberCameraPositionState {
        position = CameraPosition.fromLatLngZoom(ukraineCenter, 6f)
    }
    
    Box(modifier = Modifier.fillMaxSize()) {
        // Google Map
        GoogleMap(
            modifier = Modifier.fillMaxSize(),
            cameraPositionState = cameraPositionState,
            properties = MapProperties(
                mapType = MapType.NORMAL,
                isMyLocationEnabled = false
            ),
            uiSettings = MapUiSettings(
                zoomControlsEnabled = false,
                myLocationButtonEnabled = false
            )
        ) {
            // Draw markers for each event
            uiState.events.forEach { event ->
                val position = LatLng(event.latitude, event.longitude)
                val markerColor = getMarkerColor(event.type)
                
                Marker(
                    state = MarkerState(position = position),
                    title = event.type,
                    snippet = event.text,
                    icon = BitmapDescriptorFactory.defaultMarker(markerColor)
                )
            }
        }
        
        // Top Header
        Surface(
            modifier = Modifier
                .fillMaxWidth()
                .align(Alignment.TopCenter),
            color = DarkBackground.copy(alpha = 0.9f),
            shadowElevation = 8.dp
        ) {
            Column(
                modifier = Modifier.padding(16.dp)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "NEPTUN",
                        style = MaterialTheme.typography.headlineMedium,
                        fontWeight = FontWeight.Bold,
                        color = NeptunBlue
                    )
                    
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        // Event count badge
                        Surface(
                            shape = RoundedCornerShape(12.dp),
                            color = NeptunBlue.copy(alpha = 0.2f),
                            border = BorderStroke(1.dp, NeptunBlue)
                        ) {
                            Row(
                                modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(4.dp)
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Warning,
                                    contentDescription = null,
                                    tint = NeptunBlue,
                                    modifier = Modifier.size(16.dp)
                                )
                                Text(
                                    text = "${uiState.events.size}",
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = Color.White
                                )
                            }
                        }
                        
                        // Refresh button
                        IconButton(
                            onClick = { viewModel.loadEvents() },
                            modifier = Modifier
                                .size(40.dp)
                                .clip(CircleShape)
                                .background(NeptunBlue.copy(alpha = 0.2f))
                        ) {
                            Icon(
                                imageVector = Icons.Default.Refresh,
                                contentDescription = "Refresh",
                                tint = NeptunBlue
                            )
                        }
                    }
                }
                
                // Active alarms count
                if (uiState.activeAlarms.isNotEmpty()) {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "🚨 Активні тривоги: ${uiState.activeAlarms.count { it.active }}",
                        style = MaterialTheme.typography.bodyMedium,
                        color = Color(0xFFEF4444)
                    )
                }
            }
        }
        
        // Loading indicator
        if (uiState.isLoading) {
            CircularProgressIndicator(
                modifier = Modifier
                    .align(Alignment.Center)
                    .size(50.dp),
                color = NeptunBlue
            )
        }
        
        // Error message
        uiState.error?.let { error ->
            Surface(
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .fillMaxWidth()
                    .padding(16.dp),
                shape = RoundedCornerShape(12.dp),
                color = Color(0xFFEF4444).copy(alpha = 0.9f)
            ) {
                Text(
                    text = error,
                    modifier = Modifier.padding(16.dp),
                    color = Color.White,
                    style = MaterialTheme.typography.bodyMedium
                )
            }
        }
        
        // Auto-refresh indicator
        if (uiState.isAutoRefreshEnabled) {
            Surface(
                modifier = Modifier
                    .align(Alignment.BottomEnd)
                    .padding(16.dp),
                shape = RoundedCornerShape(20.dp),
                color = NeptunBlue.copy(alpha = 0.8f)
            ) {
                Text(
                    text = "🔄 Auto",
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                    color = Color.White,
                    style = MaterialTheme.typography.bodySmall
                )
            }
        }
    }
}

fun getMarkerColor(eventType: String): Float {
    return when {
        eventType.contains("ракет", ignoreCase = true) -> BitmapDescriptorFactory.HUE_RED
        eventType.contains("БПЛА", ignoreCase = true) -> BitmapDescriptorFactory.HUE_ORANGE
        eventType.contains("авіа", ignoreCase = true) -> BitmapDescriptorFactory.HUE_YELLOW
        eventType.contains("артилері", ignoreCase = true) -> BitmapDescriptorFactory.HUE_VIOLET
        eventType.contains("вибух", ignoreCase = true) -> BitmapDescriptorFactory.HUE_ROSE
        else -> BitmapDescriptorFactory.HUE_BLUE
    }
}

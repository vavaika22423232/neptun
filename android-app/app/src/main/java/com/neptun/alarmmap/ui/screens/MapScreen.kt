package com.neptun.alarmmap.ui.screens

import android.content.Context
import android.graphics.drawable.BitmapDrawable
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.viewmodel.compose.viewModel
import com.neptun.alarmmap.ui.theme.DarkBackground
import com.neptun.alarmmap.ui.theme.NeptunBlue
import com.neptun.alarmmap.ui.viewmodel.MapViewModel
import com.neptun.alarmmap.ui.map.ThreatIconLoader
import com.neptun.alarmmap.ui.map.UkraineBorderLoader
import kotlinx.coroutines.launch
import org.osmdroid.config.Configuration
import org.osmdroid.tileprovider.tilesource.TileSourceFactory
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.MapView
import org.osmdroid.views.overlay.Marker

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MapScreen(
    viewModel: MapViewModel = viewModel()
) {
    val uiState by viewModel.uiState.collectAsState()
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    
    // Configure OSMDroid
    LaunchedEffect(Unit) {
        Configuration.getInstance().userAgentValue = "NEPTUN/1.0"
        // Preload common icons
        ThreatIconLoader.preloadCommonIcons()
    }
    
    Box(modifier = Modifier.fillMaxSize()) {
        // OpenStreetMap
        AndroidView(
            modifier = Modifier.fillMaxSize(),
            factory = { ctx ->
                MapView(ctx).apply {
                    setTileSource(TileSourceFactory.MAPNIK)
                    setMultiTouchControls(true)
                    controller.setZoom(6.0)
                    // Ukraine center
                    controller.setCenter(GeoPoint(48.3794, 31.1656))
                    minZoomLevel = 5.0
                    maxZoomLevel = 18.0
                    
                    // Load Ukraine border
                    coroutineScope.launch {
                        UkraineBorderLoader.loadAndDisplayBorder(this@apply)
                    }
                }
            },
            update = { mapView ->
                // Clear existing markers (but keep mask and border - first 2 overlays)
                val maskAndBorder = mapView.overlays.take(2)
                mapView.overlays.clear()
                maskAndBorder.forEach { mapView.overlays.add(it) }
                
                // Add markers for each track
                android.util.Log.d("MapScreen", "Adding ${uiState.tracks.size} markers")
                uiState.tracks.forEach { track ->
                    coroutineScope.launch {
                        // Determine icon URL (priority: marker_icon > threat_type)
                        val iconUrl = ThreatIconLoader.getIconUrlFromMarkerIcon(track.markerIcon)
                            ?: ThreatIconLoader.getIconUrl(track.threatType)
                        
                        // Load icon bitmap
                        val bitmap = ThreatIconLoader.loadBitmap(iconUrl)
                        
                        val marker = Marker(mapView).apply {
                            position = GeoPoint(track.latitude, track.longitude)
                            title = track.place ?: track.threatType ?: "Загроза"
                            snippet = track.text
                            setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM)
                            
                            // Set custom icon if loaded
                            if (bitmap != null) {
                                icon = BitmapDrawable(context.resources, bitmap)
                            }
                        }
                        
                        mapView.overlays.add(marker)
                        mapView.invalidate()
                        
                        android.util.Log.d("MapScreen", "Added marker: ${track.place} (${track.threatType}) with icon: $iconUrl")
                    }
                }
            }
        )
        
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
                                    text = "${uiState.tracks.size}",
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
                
                // Tracks count
                if (uiState.tracks.isNotEmpty()) {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "� Загроз на карті: ${uiState.tracks.size}",
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

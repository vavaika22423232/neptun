package com.neptun.alarmmap.ui.screens

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Color as AndroidColor
import android.util.Log
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
import com.neptun.alarmmap.R
import com.neptun.alarmmap.ui.theme.DarkBackground
import com.neptun.alarmmap.ui.theme.NeptunBlue
import com.neptun.alarmmap.ui.viewmodel.MapViewModel
import org.osmdroid.config.Configuration
import org.osmdroid.tileprovider.tilesource.TileSourceFactory
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.MapView
import org.osmdroid.views.overlay.Marker
import org.osmdroid.views.overlay.Polygon
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MapScreen(
    viewModel: MapViewModel = viewModel()
) {
    val uiState by viewModel.uiState.collectAsState()
    val context = LocalContext.current
    
    // Configure OSMDroid
    LaunchedEffect(Unit) {
        Configuration.getInstance().userAgentValue = "NEPTUN/1.0"
    }
    
    Box(modifier = Modifier.fillMaxSize()) {
        // OpenStreetMap with Ukraine borders and markers
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
                    
                    // Add Ukraine border
                    addUkraineBorder(this, ctx)
                }
            },
            update = { mapView ->
                // Clear existing markers (but keep border)
                val borderOverlays = mapView.overlays.filterIsInstance<Polygon>()
                mapView.overlays.clear()
                mapView.overlays.addAll(borderOverlays)
                
                // Group events by location to show count
                val groupedEvents = uiState.events.groupBy { 
                    "${it.latitude},${it.longitude}" 
                }
                
                // Add markers for each location
                groupedEvents.forEach { (_, events) ->
                    val event = events.first()
                    val count = events.sumOf { it.count ?: 1 }
                    
                    val marker = Marker(mapView).apply {
                        position = GeoPoint(event.latitude, event.longitude)
                        
                        // Get icon based on threat type
                        val iconRes = when(event.actualType.lowercase()) {
                            "shahed" -> R.drawable.shahed
                            "avia" -> R.drawable.avia
                            "raketa", "missile" -> R.drawable.raketa
                            "fpv" -> R.drawable.fpv
                            "artillery" -> R.drawable.artillery
                            "pusk" -> R.drawable.pusk
                            "obstril" -> R.drawable.obstril
                            "rszv" -> R.drawable.rszv
                            "rozved" -> R.drawable.rozved
                            "vibuh" -> R.drawable.vibuh
                            "vidboi" -> R.drawable.vidboi
                            "trivoga" -> R.drawable.trivoga
                            else -> R.drawable.marker_default
                        }
                        
                        try {
                            // Create icon with count badge
                            icon = createMarkerIcon(mapView.context, iconRes, count)
                        } catch (e: Exception) {
                            Log.e("MapScreen", "Error loading icon: $iconRes", e)
                        }
                        
                        title = event.place ?: event.text.take(50)
                        snippet = if (count > 1) {
                            "x$count: ${event.text}"
                        } else {
                            event.text
                        }
                        setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM)
                    }
                    mapView.overlays.add(marker)
                    
                    Log.d("MapScreen", "Added marker: ${event.place} (${event.actualType}) (x$count)")
                }
                
                // Add trajectories (flight paths)
                uiState.trajectories.forEach { trajectory ->
                    try {
                        val points = trajectory.path.map { coord ->
                            GeoPoint(coord[0], coord[1]) // [lat, lng]
                        }
                        
                        if (points.size >= 2) {
                            val polyline = org.osmdroid.views.overlay.Polyline(mapView).apply {
                                setPoints(points)
                                
                                // Color based on threat type
                                val color = when(trajectory.actualType.lowercase()) {
                                    "shahed" -> AndroidColor.argb(200, 239, 68, 68) // Red
                                    "avia" -> AndroidColor.argb(200, 59, 130, 246) // Blue
                                    "raketa", "missile" -> AndroidColor.argb(200, 245, 158, 11) // Orange
                                    else -> AndroidColor.argb(200, 156, 163, 175) // Gray
                                }
                                
                                outlinePaint.color = color
                                outlinePaint.strokeWidth = 4f
                                outlinePaint.isAntiAlias = true
                            }
                            
                            mapView.overlays.add(polyline)
                            Log.d("MapScreen", "Added trajectory: ${trajectory.id} with ${points.size} points")
                        }
                    } catch (e: Exception) {
                        Log.e("MapScreen", "Error adding trajectory: ${trajectory.id}", e)
                    }
                }
                
                mapView.invalidate()
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

// Helper function to load Ukraine border from GeoJSON
private fun addUkraineBorder(mapView: MapView, context: Context) {
    try {
        val inputStream = context.assets.open("geoBoundaries-UKR-ADM0_simplified.geojson")
        val reader = BufferedReader(InputStreamReader(inputStream))
        val geoJsonString = reader.readText()
        reader.close()
        
        val jsonObject = JSONObject(geoJsonString)
        val features = jsonObject.getJSONArray("features")
        
        if (features.length() > 0) {
            val feature = features.getJSONObject(0)
            val geometry = feature.getJSONObject("geometry")
            val coordinates = geometry.getJSONArray("coordinates")
            
            // Collect Ukraine polygon points for mask
            val ukrainePolygons = mutableListOf<List<GeoPoint>>()
            
            // Handle Polygon or MultiPolygon
            when (geometry.getString("type")) {
                "Polygon" -> {
                    val points = extractPolygonPoints(coordinates)
                    if (points.isNotEmpty()) {
                        ukrainePolygons.add(points)
                        addPolygonBorder(mapView, coordinates)
                    }
                }
                "MultiPolygon" -> {
                    for (i in 0 until coordinates.length()) {
                        val polyCoords = coordinates.getJSONArray(i)
                        val points = extractPolygonPoints(polyCoords)
                        if (points.isNotEmpty()) {
                            ukrainePolygons.add(points)
                            addPolygonBorder(mapView, polyCoords)
                        }
                    }
                }
            }
            
            // Add world mask (darkened area outside Ukraine)
            if (ukrainePolygons.isNotEmpty()) {
                addWorldMask(mapView, ukrainePolygons)
            }
        }
    } catch (e: Exception) {
        Log.e("MapScreen", "Error loading Ukraine border", e)
    }
}

// Extract points from polygon coordinates
private fun extractPolygonPoints(coordinates: org.json.JSONArray): List<GeoPoint> {
    return try {
        val outerRing = coordinates.getJSONArray(0)
        val points = mutableListOf<GeoPoint>()
        
        for (i in 0 until outerRing.length()) {
            val coord = outerRing.getJSONArray(i)
            val lng = coord.getDouble(0)
            val lat = coord.getDouble(1)
            points.add(GeoPoint(lat, lng))
        }
        points
    } catch (e: Exception) {
        Log.e("MapScreen", "Error extracting polygon points", e)
        emptyList()
    }
}

// Add world mask (darkened overlay outside Ukraine borders)
private fun addWorldMask(mapView: MapView, ukrainePolygons: List<List<GeoPoint>>) {
    try {
        // Create world bounding box
        val worldRing = listOf(
            GeoPoint(85.0, -180.0),
            GeoPoint(85.0, 180.0),
            GeoPoint(-85.0, 180.0),
            GeoPoint(-85.0, -180.0),
            GeoPoint(85.0, -180.0)
        )
        
        // Create polygon with world as outer ring and Ukraine as holes
        val maskPolygon = Polygon(mapView).apply {
            // Add world boundary
            points = worldRing
            
            // Add Ukraine borders as holes (inverse mask)
            holes = ukrainePolygons
            
            // Style
            fillPaint.color = AndroidColor.argb(180, 15, 23, 42) // Dark blue overlay
            outlinePaint.color = AndroidColor.TRANSPARENT
            outlinePaint.strokeWidth = 0f
        }
        
        mapView.overlays.add(0, maskPolygon) // Add as first overlay (bottom layer)
        Log.d("MapScreen", "Added world mask with ${ukrainePolygons.size} Ukraine polygons")
    } catch (e: Exception) {
        Log.e("MapScreen", "Error adding world mask", e)
    }
}

private fun addPolygonBorder(mapView: MapView, coordinates: org.json.JSONArray) {
    try {
        // Get outer ring (first array)
        val outerRing = coordinates.getJSONArray(0)
        val points = mutableListOf<GeoPoint>()
        
        for (i in 0 until outerRing.length()) {
            val coord = outerRing.getJSONArray(i)
            val lng = coord.getDouble(0)
            val lat = coord.getDouble(1)
            points.add(GeoPoint(lat, lng))
        }
        
        // Create polygon overlay
        val polygon = Polygon(mapView).apply {
            this.points = points
            fillPaint.color = AndroidColor.TRANSPARENT
            outlinePaint.color = AndroidColor.argb(180, 59, 130, 246) // Blue border
            outlinePaint.strokeWidth = 3f
        }
        
        mapView.overlays.add(0, polygon) // Add as first overlay (bottom layer)
        Log.d("MapScreen", "Added Ukraine border with ${points.size} points")
    } catch (e: Exception) {
        Log.e("MapScreen", "Error adding polygon border", e)
    }
}

// Helper function to create marker icon with count badge
private fun createMarkerIcon(context: Context, iconRes: Int, count: Int): android.graphics.drawable.BitmapDrawable? {
    return try {
        // Load base icon
        val baseBitmap = BitmapFactory.decodeResource(context.resources, iconRes)
        
        // Scale to reasonable size
        val size = 64
        val scaledBitmap = Bitmap.createScaledBitmap(baseBitmap, size, size, true)
        
        val finalBitmap = if (count > 1) {
            // Create mutable copy to draw badge
            val mutableBitmap = scaledBitmap.copy(Bitmap.Config.ARGB_8888, true)
            val canvas = Canvas(mutableBitmap)
            
            // Draw count badge
            val paint = Paint().apply {
                isAntiAlias = true
            }
            
            // Badge background
            paint.color = AndroidColor.RED
            val badgeRadius = 14f
            val badgeX = size - badgeRadius - 2f
            val badgeY = badgeRadius + 2f
            canvas.drawCircle(badgeX, badgeY, badgeRadius, paint)
            
            // Badge text
            paint.color = AndroidColor.WHITE
            paint.textSize = 18f
            paint.textAlign = Paint.Align.CENTER
            paint.isFakeBoldText = true
            val countText = if (count > 99) "99+" else count.toString()
            val textY = badgeY + 6f
            canvas.drawText(countText, badgeX, textY, paint)
            
            mutableBitmap
        } else {
            scaledBitmap
        }
        
        android.graphics.drawable.BitmapDrawable(context.resources, finalBitmap)
    } catch (e: Exception) {
        Log.e("MapScreen", "Error creating marker icon", e)
        null
    }
}

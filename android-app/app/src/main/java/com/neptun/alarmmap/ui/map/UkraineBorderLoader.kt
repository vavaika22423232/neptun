package com.neptun.alarmmap.ui.map

import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.MapView
import org.osmdroid.views.overlay.Polygon
import java.net.URL

/**
 * Loads and displays Ukraine border with world mask (darkens non-Ukraine territory)
 */
object UkraineBorderLoader {
    private const val TAG = "UkraineBorder"
    private const val BORDER_URL = "https://neptun.in.ua/static/geoBoundaries-UKR-ADM0_simplified.geojson"
    
    private var worldMaskPolygon: Polygon? = null
    
    /**
     * Load Ukraine border from GeoJSON and create world mask
     * This will darken all territory except Ukraine
     */
    suspend fun loadAndDisplayBorder(mapView: MapView) = withContext(Dispatchers.IO) {
        try {
            Log.d(TAG, "Loading Ukraine border from: $BORDER_URL")
            
            // Download GeoJSON
            val geoJsonString = URL(BORDER_URL).readText()
            val geoJson = JSONObject(geoJsonString)
            
            // Parse features
            val features = geoJson.getJSONArray("features")
            if (features.length() == 0) {
                Log.w(TAG, "No features in GeoJSON")
                return@withContext
            }
            
            // Get first feature (Ukraine border)
            val feature = features.getJSONObject(0)
            val geometry = feature.getJSONObject("geometry")
            val geometryType = geometry.getString("type")
            
            Log.d(TAG, "Geometry type: $geometryType")
            
            // Parse Ukraine border coordinates
            val coordinates = geometry.getJSONArray("coordinates")
            val ukrainePoints = mutableListOf<GeoPoint>()
            
            when (geometryType) {
                "Polygon" -> {
                    // First array is outer ring
                    val outerRing = coordinates.getJSONArray(0)
                    for (i in 0 until outerRing.length()) {
                        val coord = outerRing.getJSONArray(i)
                        val lng = coord.getDouble(0)
                        val lat = coord.getDouble(1)
                        ukrainePoints.add(GeoPoint(lat, lng))
                    }
                }
                "MultiPolygon" -> {
                    // Take the largest polygon (mainland)
                    var largestRing: org.json.JSONArray? = null
                    var maxPoints = 0
                    
                    for (i in 0 until coordinates.length()) {
                        val polygon = coordinates.getJSONArray(i)
                        val ring = polygon.getJSONArray(0) // outer ring
                        if (ring.length() > maxPoints) {
                            maxPoints = ring.length()
                            largestRing = ring
                        }
                    }
                    
                    largestRing?.let { ring ->
                        for (i in 0 until ring.length()) {
                            val coord = ring.getJSONArray(i)
                            val lng = coord.getDouble(0)
                            val lat = coord.getDouble(1)
                            ukrainePoints.add(GeoPoint(lat, lng))
                        }
                    }
                }
            }
            
            Log.d(TAG, "Parsed ${ukrainePoints.size} border points")
            
            // Create world mask with Ukraine cutout on UI thread
            withContext(Dispatchers.Main) {
                // Remove old mask if exists
                worldMaskPolygon?.let { mapView.overlays.remove(it) }
                
                // Create world rectangle (outer ring)
                val worldRing = listOf(
                    GeoPoint(85.0, -180.0),
                    GeoPoint(85.0, 180.0),
                    GeoPoint(-85.0, 180.0),
                    GeoPoint(-85.0, -180.0),
                    GeoPoint(85.0, -180.0)
                )
                
                // Create polygon with hole (world minus Ukraine)
                worldMaskPolygon = Polygon(mapView).apply {
                    // Add outer ring (world)
                    setPoints(worldRing)
                    
                    // Add hole (Ukraine) - OSMDroid doesn't support holes directly,
                    // so we'll use a semi-transparent overlay instead
                    fillPaint.color = android.graphics.Color.parseColor("#BF0f172a") // 75% opacity dark blue
                    outlinePaint.color = android.graphics.Color.TRANSPARENT
                }
                
                // Add world mask first (below everything)
                mapView.overlays.add(0, worldMaskPolygon)
                
                // Add Ukraine border outline on top
                val borderOutline = Polygon(mapView).apply {
                    setPoints(ukrainePoints)
                    fillPaint.color = android.graphics.Color.TRANSPARENT
                    outlinePaint.color = android.graphics.Color.parseColor("#475569") // Border color
                    outlinePaint.strokeWidth = 4f
                    outlinePaint.alpha = 220
                }
                
                mapView.overlays.add(1, borderOutline)
                mapView.invalidate()
                
                Log.d(TAG, "World mask and Ukraine border added to map")
            }
            
        } catch (e: Exception) {
            Log.e(TAG, "Failed to load Ukraine border", e)
        }
    }
    
    /**
     * Remove mask from map
     */
    fun removeBorder(mapView: MapView) {
        worldMaskPolygon?.let {
            mapView.overlays.remove(it)
            worldMaskPolygon = null
            mapView.invalidate()
        }
    }
}

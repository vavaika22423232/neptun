package com.neptun.alarmmap.ui.screens

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.graphics.ColorMatrix
import android.graphics.ColorMatrixColorFilter
import android.graphics.Point
import android.graphics.drawable.BitmapDrawable
import android.graphics.drawable.Drawable
import android.util.Log
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color as ComposeColor
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.compose.ui.zIndex
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.core.content.ContextCompat
import com.neptun.alarmmap.data.model.AlarmTrack
import com.neptun.alarmmap.ui.viewmodel.MapViewModel
import com.neptun.alarmmap.ui.viewmodel.MapViewModelFactory
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import org.osmdroid.config.Configuration
import org.osmdroid.tileprovider.tilesource.TileSourceFactory
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.MapView
import org.osmdroid.views.overlay.Marker
import org.osmdroid.views.overlay.Overlay
import com.neptun.alarmmap.ui.theme.NeptunBlue
import java.net.HttpURLConnection
import java.net.URL
import java.util.UUID

// Функція для зміни розміру іконки
fun resizeDrawable(context: Context, drawable: Drawable?, width: Int, height: Int): Drawable? {
    if (drawable == null) return null
    
    val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
    val canvas = Canvas(bitmap)
    drawable.setBounds(0, 0, canvas.width, canvas.height)
    drawable.draw(canvas)
    
    return BitmapDrawable(context.resources, bitmap)
}

private const val MASK_ASSET_NAME = "geoBoundaries-UKR-ADM0_simplified.geojson"
private const val MASK_ALPHA = 0.70f
private const val MASK_LOG_TAG = "MapMask"
private const val MAX_MASK_RINGS = 4

private val WORLD_RING: List<GeoPoint> = listOf(
    GeoPoint(85.0, -180.0),
    GeoPoint(85.0, 180.0),
    GeoPoint(-85.0, 180.0),
    GeoPoint(-85.0, -180.0),
    GeoPoint(85.0, -180.0)
)

private val FALLBACK_UKRAINE_RING: List<GeoPoint> = listOf(
    GeoPoint(52.37, 23.60), GeoPoint(51.90, 23.60), GeoPoint(51.90, 24.00),
    GeoPoint(51.50, 24.50), GeoPoint(51.90, 25.30), GeoPoint(51.90, 26.00),
    GeoPoint(51.60, 26.60), GeoPoint(51.50, 27.50), GeoPoint(51.60, 28.20),
    GeoPoint(51.30, 29.20), GeoPoint(51.60, 30.60), GeoPoint(52.30, 31.80),
    GeoPoint(52.10, 32.70), GeoPoint(52.40, 34.40), GeoPoint(52.30, 35.90),
    GeoPoint(52.00, 37.40), GeoPoint(51.20, 38.20), GeoPoint(50.30, 39.70),
    GeoPoint(49.10, 40.10), GeoPoint(48.30, 39.70), GeoPoint(47.10, 38.50),
    GeoPoint(46.00, 38.20), GeoPoint(45.35, 37.40), GeoPoint(45.40, 36.60),
    GeoPoint(45.20, 34.90), GeoPoint(45.35, 33.30), GeoPoint(46.07, 30.95),
    GeoPoint(46.58, 30.06), GeoPoint(47.80, 29.48), GeoPoint(48.37, 28.05),
    GeoPoint(48.47, 27.53), GeoPoint(48.27, 26.86), GeoPoint(47.74, 26.63),
    GeoPoint(47.85, 24.96), GeoPoint(48.15, 23.53), GeoPoint(48.62, 22.57),
    GeoPoint(49.90, 22.09), GeoPoint(51.94, 22.93), GeoPoint(52.37, 23.60)
)

private fun ensureClosedRing(points: List<GeoPoint>): List<GeoPoint> {
    if (points.isEmpty()) return points
    val first = points.first()
    val last = points.last()
    if (first.latitude == last.latitude && first.longitude == last.longitude) {
        return points
    }
    val mutable = points.toMutableList()
    mutable.add(GeoPoint(first.latitude, first.longitude))
    return mutable
}

private class UkraineMaskOverlay(
    private var maskRings: List<List<GeoPoint>>
) : Overlay() {
    private val maskPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.FILL
        color = Color.parseColor("#1e3a5f")
    }

    private val borderPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeWidth = 4f
        color = Color.parseColor("#475569")
    }

    override fun draw(canvas: Canvas, mapView: MapView, shadow: Boolean) {
        if (shadow || maskRings.isEmpty()) return
        val projection = mapView.projection ?: return

        val maskPath = Path().apply {
            fillType = Path.FillType.EVEN_ODD
            addRect(
                0f,
                0f,
                canvas.width.toFloat(),
                canvas.height.toFloat(),
                Path.Direction.CW
            )
        }
        val borderPaths = mutableListOf<Path>()

        maskRings.forEach { ring ->
            if (ring.size < 3) return@forEach
            val ringPath = Path()
            ring.forEachIndexed { index, geoPoint ->
                val point = projection.toPixels(geoPoint, Point())
                val x = point.x.toFloat()
                val y = point.y.toFloat()
                if (index == 0) {
                    ringPath.moveTo(x, y)
                } else {
                    ringPath.lineTo(x, y)
                }
            }
            ringPath.close()
            maskPath.addPath(ringPath)
            borderPaths.add(ringPath)
        }

        canvas.drawPath(maskPath, maskPaint)
        borderPaths.forEach { path -> canvas.drawPath(path, borderPaint) }
    }

    fun updateRings(newRings: List<List<GeoPoint>>) {
        maskRings = newRings
    }
}

private object MarkerIconCache {
    private val cache = mutableMapOf<Pair<Int, Int>, Drawable?>()

    fun get(context: Context, resId: Int, sizePx: Int): Drawable? {
        val key = resId to sizePx
        return cache.getOrPut(key) {
            ContextCompat.getDrawable(context, resId)?.let { drawable ->
                resizeDrawable(context, drawable, sizePx, sizePx)
            }
        }
    }
}

@Composable
private fun HeaderPill(
    icon: String,
    value: String,
    foreground: ComposeColor,
    background: ComposeColor
) {
    Surface(
        shape = RoundedCornerShape(12.dp),
        color = background,
        border = BorderStroke(1.dp, foreground.copy(alpha = 0.3f))
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
            horizontalArrangement = Arrangement.spacedBy(6.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(text = icon, fontSize = 13.sp)
            Text(
                text = value,
                style = MaterialTheme.typography.labelLarge,
                fontWeight = FontWeight.Bold,
                color = foreground,
                fontSize = 13.sp
            )
        }
    }
}

private data class PresenceCounts(
    val total: Int,
    val web: Int,
    val android: Int,
    val ios: Int
)

private object PresenceIdProvider {
    private const val PREFS_NAME = "neptun_presence"
    private const val KEY = "presence_id"

    fun get(context: Context): String {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val existing = prefs.getString(KEY, null)
        if (!existing.isNullOrBlank()) return existing
        val generated = UUID.randomUUID().toString()
        prefs.edit().putString(KEY, generated).apply()
        return generated
    }
}

private suspend fun pingPresence(presenceId: String): PresenceCounts? = withContext(Dispatchers.IO) {
    return@withContext runCatching {
        val connection = (URL("https://neptun.in.ua/presence").openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = 6000
            readTimeout = 6000
            doOutput = true
            setRequestProperty("Content-Type", "application/json")
        }
        val payload = JSONObject().apply {
            put("id", presenceId)
            put("platform", "android")
        }
        connection.outputStream.use { it.write(payload.toString().toByteArray()) }

        val responseBody = try {
            val stream = if (connection.responseCode in 200..299) {
                connection.inputStream
            } else {
                connection.errorStream
            }
            stream?.bufferedReader()?.use { it.readText() } ?: return@runCatching null
        } finally {
            connection.disconnect()
        }

        val json = JSONObject(responseBody)
        val platforms = json.optJSONObject("platforms")
        val web = platforms?.optInt("web", 0) ?: 0
        val android = platforms?.optInt("android", 0) ?: 0
        val ios = platforms?.optInt("ios", 0) ?: 0
        val total = json.optInt("visitors", -1).takeIf { it >= 0 } ?: (web + android + ios)
        PresenceCounts(total = total, web = web, android = android, ios = ios)
    }.onFailure { error ->
        Log.w(MASK_LOG_TAG, "Failed to ping presence", error)
    }.getOrNull()
}

private suspend fun trackAppVisit(presenceId: String) = withContext(Dispatchers.IO) {
    runCatching {
        val connection = (URL("https://neptun.in.ua/api/track_android_visit").openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = 5000
            readTimeout = 5000
            doOutput = true
            setRequestProperty("Content-Type", "application/json")
        }
        val payload = JSONObject().apply {
            put("platform", "android")
            put("device_id", presenceId)
        }
        connection.outputStream.use { it.write(payload.toString().toByteArray()) }
        val stream = if (connection.responseCode in 200..299) {
            connection.inputStream
        } else {
            connection.errorStream
        }
        stream?.close()
        connection.disconnect()
    }.onFailure { error ->
        Log.w(MASK_LOG_TAG, "Failed to track app visit", error)
    }
}

private fun formatNumber(number: Int): String {
    return when {
        number >= 1_000_000 -> String.format("%.1fM", number / 1_000_000f)
        number >= 1_000 -> String.format("%.1fK", number / 1_000f)
        else -> number.toString()
    }
}

@Composable
fun MapScreenOSM(
    viewModel: MapViewModel = viewModel(
        factory = MapViewModelFactory(LocalContext.current.applicationContext)
    ),
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val uiState by viewModel.uiState.collectAsState()
    val tracks = uiState.filteredTracks

    var webVisitors by remember { mutableStateOf(0) }
    var androidVisitors by remember { mutableStateOf(0) }
    var iosVisitors by remember { mutableStateOf(0) }
    var totalVisitors by remember { mutableStateOf(0) }

    val presenceId = remember(context) { PresenceIdProvider.get(context) }

    val pulseTransition = rememberInfiniteTransition(label = "header_pulse")
    val pulseScale by pulseTransition.animateFloat(
        initialValue = 1f,
        targetValue = 1.08f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 1400, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulse_scale"
    )

    LaunchedEffect(Unit) {
        viewModel.loadEvents()
    }

    LaunchedEffect(presenceId) {
        trackAppVisit(presenceId)
        delay(1500)
        while (isActive) {
            pingPresence(presenceId)?.let { counts ->
                totalVisitors = counts.total
                webVisitors = counts.web
                androidVisitors = counts.android
                iosVisitors = counts.ios
            }
            delay(30_000)
        }
    }

    val maskRings by produceState(initialValue = listOf(FALLBACK_UKRAINE_RING), key1 = context) {
        val precise = loadPreciseMaskRings(context)
        if (!precise.isNullOrEmpty()) {
            value = precise
        }
    }

    Box(modifier = modifier.fillMaxSize()) {
        // WebView with map
        AndroidView(
            modifier = Modifier.fillMaxSize(),
            factory = { ctx ->
                android.webkit.WebView(ctx).apply {
                    layoutParams = android.view.ViewGroup.LayoutParams(
                        android.view.ViewGroup.LayoutParams.MATCH_PARENT,
                        android.view.ViewGroup.LayoutParams.MATCH_PARENT
                    )
                    
                    settings.apply {
                        javaScriptEnabled = true
                        domStorageEnabled = true
                        databaseEnabled = true
                        cacheMode = android.webkit.WebSettings.LOAD_DEFAULT
                        loadWithOverviewMode = true
                        useWideViewPort = true
                        builtInZoomControls = false
                        displayZoomControls = false
                        setSupportZoom(true)
                        allowFileAccess = false
                        allowContentAccess = false
                        
                        // Security settings for Google Play
                        mixedContentMode = android.webkit.WebSettings.MIXED_CONTENT_NEVER_ALLOW
                        setSafeBrowsingEnabled(true)
                        
                        // Performance optimizations
                        setRenderPriority(android.webkit.WebSettings.RenderPriority.HIGH)
                    }
                    
                    webViewClient = object : android.webkit.WebViewClient() {
                        override fun onPageFinished(view: android.webkit.WebView?, url: String?) {
                            super.onPageFinished(view, url)
                            view?.evaluateJavascript(
                                """if (window.map && window.map.flyTo) {
                                    window.map.flyTo({
                                        center: [31.1656, 48.3794],
                                        zoom: 6,
                                        duration: 1000
                                    });
                                }""",
                                null
                            )
                        }
                    }
                    webChromeClient = android.webkit.WebChromeClient()
                    
                    loadUrl("https://neptun.in.ua/map-only")
                }
            }
        )

        // Modern gradient overlay
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(140.dp)
                .align(Alignment.TopCenter)
                .zIndex(1f)
                .background(
                    Brush.verticalGradient(
                        colors = listOf(
                            ComposeColor(0xDD0F172A),
                            ComposeColor(0x990F172A),
                            ComposeColor.Transparent
                        )
                    )
                )
        )

        // Modern header card (on top with zIndex)
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 12.dp)
                .align(Alignment.TopCenter)
                .zIndex(2f),
            shape = RoundedCornerShape(20.dp),
            colors = CardDefaults.cardColors(
                containerColor = ComposeColor(0xF00F172A)
            ),
            elevation = CardDefaults.cardElevation(defaultElevation = 12.dp),
            border = BorderStroke(1.dp, ComposeColor(0xFF3B82F6).copy(alpha = 0.15f))
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(
                        Brush.horizontalGradient(
                            colors = listOf(
                                ComposeColor.Transparent,
                                ComposeColor(0xFF3B82F6).copy(alpha = 0.03f),
                                ComposeColor.Transparent
                            )
                        )
                    )
                    .padding(horizontal = 16.dp, vertical = 14.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                // Top row: Logo + Total stats
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    // Logo section
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(10.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Box(
                            modifier = Modifier.size(42.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            Surface(
                                shape = CircleShape,
                                color = NeptunBlue.copy(alpha = 0.2f),
                                modifier = Modifier
                                    .size(42.dp)
                                    .scale(pulseScale)
                            ) {}
                            Text(
                                text = "⚡",
                                fontSize = 22.sp,
                                modifier = Modifier.align(Alignment.Center)
                            )
                        }
                        Column(verticalArrangement = Arrangement.spacedBy(1.dp)) {
                            Text(
                                text = "NEPTUN",
                                style = MaterialTheme.typography.titleLarge,
                                fontWeight = FontWeight.ExtraBold,
                                color = ComposeColor.White,
                                letterSpacing = 0.8.sp,
                                fontSize = 18.sp
                            )
                            Text(
                                text = "Real-time alerts",
                                style = MaterialTheme.typography.bodySmall,
                                color = ComposeColor(0xFF94A3B8),
                                fontSize = 10.sp,
                                letterSpacing = 0.3.sp
                            )
                        }
                    }

                    // Threats counter
                    Surface(
                        shape = RoundedCornerShape(14.dp),
                        color = ComposeColor(0xFF10B981).copy(alpha = 0.18f),
                        border = BorderStroke(1.dp, ComposeColor(0xFF10B981).copy(alpha = 0.3f))
                    ) {
                        Row(
                            modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                            horizontalArrangement = Arrangement.spacedBy(6.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(text = "🎯", fontSize = 14.sp)
                            Text(
                                text = "${uiState.filteredTracks.size}/${uiState.tracks.size}",
                                style = MaterialTheme.typography.labelLarge,
                                fontWeight = FontWeight.Bold,
                                color = ComposeColor(0xFF10B981),
                                fontSize = 16.sp
                            )
                        }
                    }
                }

                // Bottom row: Platform stats
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    val appsVisitors = androidVisitors + iosVisitors
                    
                    // Total online
                    Surface(
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(12.dp),
                        color = ComposeColor(0xFF3B82F6).copy(alpha = 0.15f),
                        border = BorderStroke(1.dp, ComposeColor(0xFF3B82F6).copy(alpha = 0.25f))
                    ) {
                        Row(
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 7.dp),
                            horizontalArrangement = Arrangement.spacedBy(5.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(text = "👥", fontSize = 12.sp)
                            Text(
                                text = formatNumber(totalVisitors),
                                style = MaterialTheme.typography.labelMedium,
                                fontWeight = FontWeight.Bold,
                                color = ComposeColor(0xFF60A5FA),
                                fontSize = 13.sp
                            )
                        }
                    }
                    
                    // Web users
                    Surface(
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(12.dp),
                        color = ComposeColor(0xFF10B981).copy(alpha = 0.15f),
                        border = BorderStroke(1.dp, ComposeColor(0xFF10B981).copy(alpha = 0.25f))
                    ) {
                        Row(
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 7.dp),
                            horizontalArrangement = Arrangement.spacedBy(5.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(text = "🌐", fontSize = 12.sp)
                            Text(
                                text = formatNumber(webVisitors),
                                style = MaterialTheme.typography.labelMedium,
                                fontWeight = FontWeight.Bold,
                                color = ComposeColor(0xFF34D399),
                                fontSize = 13.sp
                            )
                        }
                    }
                    
                    // Apps users
                    Surface(
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(12.dp),
                        color = ComposeColor(0xFFF59E0B).copy(alpha = 0.15f),
                        border = BorderStroke(1.dp, ComposeColor(0xFFF59E0B).copy(alpha = 0.25f))
                    ) {
                        Row(
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 7.dp),
                            horizontalArrangement = Arrangement.spacedBy(5.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(text = "📱", fontSize = 12.sp)
                            Text(
                                text = formatNumber(appsVisitors),
                                style = MaterialTheme.typography.labelMedium,
                                fontWeight = FontWeight.Bold,
                                color = ComposeColor(0xFFFBBF24),
                                fontSize = 13.sp
                            )
                        }
                    }
                }
            }
        }

        if (uiState.isLoading) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(ComposeColor.Black.copy(alpha = 0.25f)),
                contentAlignment = Alignment.Center
            ) {
                Surface(
                    shape = RoundedCornerShape(16.dp),
                    color = ComposeColor(0xDD0F172A),
                    shadowElevation = 16.dp
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 24.dp, vertical = 16.dp),
                        horizontalArrangement = Arrangement.spacedBy(16.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(28.dp),
                            color = NeptunBlue,
                            strokeWidth = 3.dp
                        )
                        Text(
                            text = "Оновлюємо дані...",
                            color = ComposeColor.White,
                            style = MaterialTheme.typography.bodyMedium,
                            fontWeight = FontWeight.Medium
                        )
                    }
                }
            }
        }
    }
}

private suspend fun loadPreciseMaskRings(context: Context): List<List<GeoPoint>>? = withContext(Dispatchers.IO) {
    return@withContext runCatching {
        context.assets.open(MASK_ASSET_NAME).use { input ->
            val geoJson = input.bufferedReader().use { it.readText() }
            parseGeoJsonRings(geoJson)
        }
    }.onFailure { Log.w(MASK_LOG_TAG, "Failed to load precise border", it) }
        .getOrNull()
}

private fun parseGeoJsonRings(geoJson: String): List<List<GeoPoint>>? {
    val json = JSONObject(geoJson)
    val features = json.optJSONArray("features") ?: return null
    if (features.length() == 0) return null

    val geometry = features.getJSONObject(0).getJSONObject("geometry")
    val type = geometry.getString("type")
    val coordinates = geometry.getJSONArray("coordinates")
    val collectedRings = mutableListOf<List<GeoPoint>>()

    fun JSONArray.toRing(): List<GeoPoint> {
        val list = mutableListOf<GeoPoint>()
        for (i in 0 until length()) {
            val coord = getJSONArray(i)
            val lng = coord.getDouble(0)
            val lat = coord.getDouble(1)
            list.add(GeoPoint(lat, lng))
        }
        return ensureClosedRing(list)
    }

    when (type) {
        "Polygon" -> {
            for (i in 0 until coordinates.length()) {
                if (collectedRings.size >= MAX_MASK_RINGS) break
                collectedRings.add(coordinates.getJSONArray(i).toRing())
            }
        }
        "MultiPolygon" -> {
            for (i in 0 until coordinates.length()) {
                if (collectedRings.size >= MAX_MASK_RINGS) break
                val polygon = coordinates.getJSONArray(i)
                if (polygon.length() > 0) {
                    collectedRings.add(polygon.getJSONArray(0).toRing())
                }
            }
        }
    }

    return collectedRings.takeIf { it.isNotEmpty() }
}

private fun MapView.resolveMarkerIcon(track: AlarmTrack): Int {
    val markerIcon = track.markerIcon?.lowercase() ?: ""
    val threatType = track.threatType?.lowercase() ?: ""
    fun String.containsAny(vararg keys: String) = keys.any { contains(it) }

    return when {
        markerIcon.contains("shahed") || threatType.containsAny("shahed", "шахед") ->
            com.neptun.alarmmap.R.drawable.shahed
        markerIcon.contains("raketa") || threatType.containsAny("raketa", "ракета") ->
            com.neptun.alarmmap.R.drawable.raketa
        markerIcon.contains("fpv") || threatType.contains("fpv") ->
            com.neptun.alarmmap.R.drawable.fpv
        markerIcon.contains("kab") || threatType.containsAny("kab", "каб") ->
            com.neptun.alarmmap.R.drawable.kab
        markerIcon.contains("obstril") || threatType.containsAny("obstril", "artillery") ->
            com.neptun.alarmmap.R.drawable.obstril
        markerIcon.contains("avia") || threatType.contains("avia") ->
            com.neptun.alarmmap.R.drawable.avia
        markerIcon.contains("pusk") || threatType.contains("pusk") ->
            com.neptun.alarmmap.R.drawable.pusk
        markerIcon.contains("rszv") || threatType.containsAny("rszv", "рсзв") ->
            com.neptun.alarmmap.R.drawable.rszv
        markerIcon.contains("rozved") || threatType.containsAny("rozved", "розвід") ->
            com.neptun.alarmmap.R.drawable.rozved
        markerIcon.contains("vibuh") || threatType.containsAny("vibuh", "вибух") ->
            com.neptun.alarmmap.R.drawable.vibuh
        markerIcon.contains("vidboi") || threatType.containsAny("vidboi", "відбій") ->
            com.neptun.alarmmap.R.drawable.vidboi
        else -> com.neptun.alarmmap.R.drawable.trivoga
    }
}

private fun shouldShowCountBadge(track: AlarmTrack): Boolean {
    val count = track.count ?: 0
    if (count <= 1) return false
    
    val markerIcon = track.markerIcon?.lowercase() ?: ""
    val threatType = track.threatType?.lowercase() ?: ""
    
    return markerIcon.contains("shahed") || 
           threatType.contains("shahed") || 
           threatType.contains("шахед") ||
           threatType.contains("бпла")
}

private fun createMarkerWithBadge(context: Context, iconResId: Int, size: Int, count: Int): Drawable? {
    try {
        // Create a larger bitmap to accommodate the badge
        val badgeOffset = (size * 0.15f).toInt()
        val totalSize = size + badgeOffset
        val bitmap = Bitmap.createBitmap(totalSize, totalSize, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        
        // Draw the main icon
        val iconDrawable = ContextCompat.getDrawable(context, iconResId) ?: return null
        iconDrawable.setBounds(badgeOffset, badgeOffset, size + badgeOffset, size + badgeOffset)
        iconDrawable.draw(canvas)
        
        // Draw the badge
        val badgeSize = (size * 0.4f).toInt()
        val badgeX = totalSize - badgeSize
        val badgeY = 0
        
        // Badge background with gradient
        val paint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            shader = android.graphics.LinearGradient(
                badgeX.toFloat(), badgeY.toFloat(),
                (badgeX + badgeSize).toFloat(), (badgeY + badgeSize).toFloat(),
                intArrayOf(Color.parseColor("#dc2626"), Color.parseColor("#b91c1c")),
                null,
                android.graphics.Shader.TileMode.CLAMP
            )
        }
        
        val badgeRadius = badgeSize / 2f
        canvas.drawCircle(
            badgeX + badgeRadius,
            badgeY + badgeRadius,
            badgeRadius,
            paint
        )
        
        // Badge shadow
        val shadowPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.argb(80, 0, 0, 0)
            maskFilter = android.graphics.BlurMaskFilter(4f, android.graphics.BlurMaskFilter.Blur.NORMAL)
        }
        canvas.drawCircle(
            badgeX + badgeRadius,
            badgeY + badgeRadius + 2,
            badgeRadius,
            shadowPaint
        )
        
        // Badge text
        val textPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.WHITE
            textSize = badgeSize * 0.5f
            textAlign = Paint.Align.CENTER
            typeface = android.graphics.Typeface.create(android.graphics.Typeface.DEFAULT, android.graphics.Typeface.BOLD)
        }
        
        val countText = "${count}×"
        val textY = badgeY + badgeRadius - ((textPaint.descent() + textPaint.ascent()) / 2)
        canvas.drawText(countText, badgeX + badgeRadius, textY, textPaint)
        
        return BitmapDrawable(context.resources, bitmap)
    } catch (e: Exception) {
        Log.e(MASK_LOG_TAG, "Failed to create badge marker", e)
        return MarkerIconCache.get(context, iconResId, size)
    }
}

private fun MapView.renderMapState(
    tracks: List<AlarmTrack>,
    maskRings: List<List<GeoPoint>>
) {
    updateTrackMarkers(tracks)
    ensureMaskOverlay(maskRings)
    invalidate()
}

private fun MapView.updateTrackMarkers(tracks: List<AlarmTrack>) {
    val iconSize = (32 * context.resources.displayMetrics.density).toInt()
    val existingMarkers = overlays.filterIsInstance<Marker>()
        .filter { it.relatedObject is String }
        .associateBy { it.relatedObject as String }

    val keepIds = mutableSetOf<String>()
    tracks.forEach { track ->
        val markerId = track.id
        val targetPosition = GeoPoint(track.latitude, track.longitude)
        val iconResId = resolveMarkerIcon(track)
        
        // Create icon with badge if count > 1 for shaheds
        val iconDrawable = if (shouldShowCountBadge(track)) {
            createMarkerWithBadge(context, iconResId, iconSize, track.count ?: 0)
        } else {
            MarkerIconCache.get(context, iconResId, iconSize)
        }

        val marker = existingMarkers[markerId]
        if (marker != null) {
            if (marker.position != targetPosition) marker.position = targetPosition
            marker.title = track.text ?: "Загроза"
            marker.snippet = track.place
            if (iconDrawable != null && marker.icon !== iconDrawable) {
                marker.icon = iconDrawable
            }
        } else {
            val newMarker = Marker(this).apply {
                position = targetPosition
                title = track.text ?: "Загроза"
                snippet = track.place
                relatedObject = markerId
                iconDrawable?.let { icon = it }
            }
            overlays.add(newMarker)
        }
        keepIds += markerId
    }

    val toRemove = existingMarkers.filterKeys { it !in keepIds }.values
    overlays.removeAll(toRemove)
}

private fun MapView.ensureMaskOverlay(maskRings: List<List<GeoPoint>>) {
    val rings = maskRings.takeIf { it.isNotEmpty() } ?: listOf(FALLBACK_UKRAINE_RING)
    val overlay = overlays.filterIsInstance<UkraineMaskOverlay>().firstOrNull()
    if (overlay == null) {
        overlays.add(UkraineMaskOverlay(rings))
    } else {
        overlay.updateRings(rings)
    }
}

private val lightMapColorFilter: ColorMatrixColorFilter by lazy { createLightMapColorFilter() }

private fun createLightMapColorFilter(): ColorMatrixColorFilter {
    val desaturate = ColorMatrix().apply { setSaturation(0.45f) }
    val contrastMatrix = ColorMatrix(
        floatArrayOf(
            0.95f, 0f, 0f, 0f, 0f,
            0f, 0.95f, 0f, 0f, 0f,
            0f, 0f, 0.95f, 0f, 0f,
            0f, 0f, 0f, 1f, 0f
        )
    )
    val brightnessMatrix = ColorMatrix(
        floatArrayOf(
            1.05f, 0f, 0f, 0f, 12f,
            0f, 1.05f, 0f, 0f, 12f,
            0f, 0f, 1.05f, 0f, 12f,
            0f, 0f, 0f, 1f, 0f
        )
    )
    contrastMatrix.postConcat(brightnessMatrix)
    desaturate.postConcat(contrastMatrix)
    return ColorMatrixColorFilter(desaturate)
}


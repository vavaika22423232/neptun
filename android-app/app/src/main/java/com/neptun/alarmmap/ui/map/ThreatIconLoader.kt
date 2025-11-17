package com.neptun.alarmmap.ui.map

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.net.URL

object ThreatIconLoader {
    private const val TAG = "ThreatIconLoader"
    private val iconCache = mutableMapOf<String, Bitmap>()
    
    // Маппінг типів загроз на іконки
    private val threatIconMap = mapOf(
        "shahed" to "https://neptun.in.ua/static/shahed.png",
        "шахед" to "https://neptun.in.ua/static/shahed.png",
        "raketa" to "https://neptun.in.ua/static/raketa.png",
        "ракета" to "https://neptun.in.ua/static/raketa.png",
        "fpv" to "https://neptun.in.ua/static/fpv.png",
        "фпв" to "https://neptun.in.ua/static/fpv.png",
        "artillery" to "https://neptun.in.ua/static/obstril.png",
        "артилерія" to "https://neptun.in.ua/static/obstril.png",
        "obstril" to "https://neptun.in.ua/static/obstril.png",
        "обстріл" to "https://neptun.in.ua/static/obstril.png",
        "avia" to "https://neptun.in.ua/static/avia.png",
        "авіація" to "https://neptun.in.ua/static/avia.png",
        "pusk" to "https://neptun.in.ua/static/pusk.png",
        "пуск" to "https://neptun.in.ua/static/pusk.png"
    )
    
    fun getIconUrl(threatType: String?): String {
        if (threatType.isNullOrBlank()) {
            return "https://neptun.in.ua/static/default.png"
        }
        
        val type = threatType.lowercase()
        threatIconMap.entries.forEach { (key, value) ->
            if (type.contains(key)) {
                return value
            }
        }
        
        return "https://neptun.in.ua/static/default.png"
    }
    
    fun getIconUrlFromMarkerIcon(markerIcon: String?): String? {
        if (markerIcon.isNullOrBlank()) {
            return null
        }
        
        // Якщо вже повний URL
        if (markerIcon.startsWith("http")) {
            return markerIcon
        }
        
        // Якщо ім'я файлу
        return "https://neptun.in.ua/static/$markerIcon"
    }
    
    suspend fun loadBitmap(url: String): Bitmap? = withContext(Dispatchers.IO) {
        try {
            // Перевірка кешу
            iconCache[url]?.let { return@withContext it }
            
            Log.d(TAG, "Завантаження іконки: $url")
            
            // Завантаження з мережі
            val connection = URL(url).openConnection()
            connection.connectTimeout = 5000
            connection.readTimeout = 5000
            val inputStream = connection.getInputStream()
            val bitmap = BitmapFactory.decodeStream(inputStream)
            inputStream.close()
            
            // Масштабування до 48x48
            val scaledBitmap = Bitmap.createScaledBitmap(bitmap, 48, 48, true)
            
            // Збереження в кеш
            iconCache[url] = scaledBitmap
            
            Log.d(TAG, "Іконку завантажено: $url")
            scaledBitmap
        } catch (e: Exception) {
            Log.e(TAG, "Помилка завантаження іконки $url: ${e.message}")
            null
        }
    }
    
    fun preloadCommonIcons() {
        // Попереднє завантаження популярних іконок
        val commonIcons = listOf(
            "https://neptun.in.ua/static/shahed.png",
            "https://neptun.in.ua/static/raketa.png",
            "https://neptun.in.ua/static/avia.png",
            "https://neptun.in.ua/static/obstril.png",
            "https://neptun.in.ua/static/fpv.png"
        )
        
        // Завантажуємо асинхронно
        kotlinx.coroutines.CoroutineScope(Dispatchers.IO).launch {
            commonIcons.forEach { url ->
                loadBitmap(url)
            }
        }
    }
}
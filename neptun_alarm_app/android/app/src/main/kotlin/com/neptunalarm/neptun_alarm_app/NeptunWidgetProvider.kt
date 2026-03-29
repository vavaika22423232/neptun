package com.neptunalarm.neptun_alarm_app

import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.Context
import android.widget.RemoteViews
import android.app.PendingIntent
import android.content.Intent
import android.view.View
import java.text.SimpleDateFormat
import java.util.*

class NeptunWidgetProvider : AppWidgetProvider() {

    override fun onUpdate(
        context: Context,
        appWidgetManager: AppWidgetManager,
        appWidgetIds: IntArray
    ) {
        for (appWidgetId in appWidgetIds) {
            updateAppWidget(context, appWidgetManager, appWidgetId)
        }
    }

    override fun onEnabled(context: Context) {}
    override fun onDisabled(context: Context) {}

    companion object {
        private const val PREFS_NAME = "HomeWidgetPreferences"
        
        fun updateAppWidget(
            context: Context,
            appWidgetManager: AppWidgetManager,
            appWidgetId: Int
        ) {
            val views = RemoteViews(context.packageName, R.layout.neptun_widget_simple)

            try {
                val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
                val region = prefs.getString("widget_region", "Україна") ?: "Україна"
                val isAlarm = prefs.getBoolean("widget_is_alarm", false)
                val totalAlarms = prefs.getInt("widget_total_alarms", 0)
                val lastUpdate = prefs.getLong("widget_last_update", System.currentTimeMillis())
                val statusText = prefs.getString("widget_status_text", null)
                
                // Threats
                val dronesCount = prefs.getInt("widget_drones_count", 0)
                val missilesCount = prefs.getInt("widget_missiles_count", 0)
                val kabCount = prefs.getInt("widget_kab_count", 0)
                val ballisticCount = prefs.getInt("widget_ballistic_count", 0)
                val totalThreats = prefs.getInt("widget_total_threats", 0)

                views.setTextViewText(R.id.widget_region, region)

                // Перевірка на Premium повідомлення
                if (statusText != null && statusText.isNotEmpty()) {
                    views.setTextViewText(R.id.widget_status, statusText)
                    views.setTextColor(R.id.widget_status, 0xFFFFD700.toInt()) // Золотий колір
                    views.setViewVisibility(R.id.widget_threats_detail, View.GONE)
                    views.setTextViewText(R.id.widget_total_alarms, "Відкрийте додаток")
                } else if (isAlarm) {
                    views.setTextViewText(R.id.widget_status, "ТРИВОГА")
                    views.setTextColor(R.id.widget_status, 0xFFFF5252.toInt())
                } else {
                    views.setTextViewText(R.id.widget_status, "Все спокійно")
                    views.setTextColor(R.id.widget_status, 0xFF66BB6A.toInt())
                }

                // Threats detail (тільки якщо не Premium повідомлення)
                if (statusText == null && totalThreats > 0) {
                    val parts = mutableListOf<String>()
                    if (dronesCount > 0) parts.add("Шахеди: $dronesCount")
                    if (missilesCount > 0) parts.add("Ракети: $missilesCount")
                    if (kabCount > 0) parts.add("КАБ: $kabCount")
                    if (ballisticCount > 0) parts.add("Балістика: $ballisticCount")
                    
                    if (parts.isNotEmpty()) {
                        views.setTextViewText(R.id.widget_threats_detail, parts.joinToString("  •  "))
                        views.setViewVisibility(R.id.widget_threats_detail, View.VISIBLE)
                    } else {
                        views.setViewVisibility(R.id.widget_threats_detail, View.GONE)
                    }
                } else if (statusText == null) {
                    views.setViewVisibility(R.id.widget_threats_detail, View.GONE)
                }

                // Total alarms (тільки якщо не Premium повідомлення)
                if (statusText == null) {
                    val alarmsText = when {
                        totalAlarms == 0 -> "Немає тривог"
                        totalAlarms == 1 -> "1 область з тривогою"
                        totalAlarms in 2..4 -> "$totalAlarms області з тривогою"
                        else -> "$totalAlarms областей з тривогою"
                    }
                    views.setTextViewText(R.id.widget_total_alarms, alarmsText)
                }

                // Time
                val sdf = SimpleDateFormat("HH:mm", Locale.getDefault())
                views.setTextViewText(R.id.widget_updated, sdf.format(Date(lastUpdate)))

            } catch (e: Exception) {
                views.setTextViewText(R.id.widget_status, "Відкрийте додаток")
                views.setTextColor(R.id.widget_status, 0xFFFFFFFF.toInt())
            }

            // Click to open app
            try {
                val intent = Intent(context, MainActivity::class.java)
                intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
                val pendingIntent = PendingIntent.getActivity(
                    context, 0, intent,
                    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
                )
                views.setOnClickPendingIntent(R.id.widget_container, pendingIntent)
            } catch (e: Exception) {}

            appWidgetManager.updateAppWidget(appWidgetId, views)
        }
    }
}

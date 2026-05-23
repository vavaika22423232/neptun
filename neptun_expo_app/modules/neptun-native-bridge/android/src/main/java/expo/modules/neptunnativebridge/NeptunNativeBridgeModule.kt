package expo.modules.neptunnativebridge

import android.appwidget.AppWidgetManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition

/**
 * Writes Flutter `home_widget` keys into `HomeWidgetPreferences` and reloads
 * `NeptunWidgetProvider` when present (copied via `withNeptunHomeWidget` config plugin).
 */
class NeptunNativeBridgeModule : Module() {
  override fun definition() = ModuleDefinition {
    Name("NeptunNativeBridge")

    Function("isAvailable") {
      true
    }

    AsyncFunction("setWidgetData") { key: String, value: Any? ->
      val context = appContext.reactContext ?: return@AsyncFunction
      val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
      val editor = prefs.edit()
      when (value) {
        null -> editor.remove(key)
        is String -> editor.putString(key, value)
        is Boolean -> editor.putBoolean(key, value)
        is Int -> editor.putInt(key, value)
        is Double -> editor.putLong(key, value.toLong())
        is Float -> editor.putFloat(key, value)
        is Long -> editor.putLong(key, value)
        else -> editor.putString(key, value.toString())
      }
      editor.apply()
    }

    AsyncFunction("reloadWidget") {
      val context = appContext.reactContext ?: return@AsyncFunction
      try {
        val manager = AppWidgetManager.getInstance(context)
        val component = ComponentName(context.packageName, WIDGET_PROVIDER)
        val ids = manager.getAppWidgetIds(component)
        if (ids.isEmpty()) return@AsyncFunction
        val intent = Intent(AppWidgetManager.ACTION_APPWIDGET_UPDATE)
        intent.component = component
        intent.putExtra(AppWidgetManager.EXTRA_APPWIDGET_IDS, ids)
        context.sendBroadcast(intent)
      } catch (_: Throwable) {
        /* provider not linked until prebuild copies Flutter widget target */
      }
    }

    AsyncFunction("startLiveActivity") { options: Map<String, Any?> ->
      /* iOS-only — no-op on Android */
    }

    AsyncFunction("updateLiveActivity") { options: Map<String, Any?> ->
      /* iOS-only */
    }

    AsyncFunction("endLiveActivity") {
      /* iOS-only */
    }
  }

  companion object {
    private const val PREFS_NAME = "HomeWidgetPreferences"
    private const val WIDGET_PROVIDER = "com.neptunalarm.neptun_alarm_app.NeptunWidgetProvider"
  }
}

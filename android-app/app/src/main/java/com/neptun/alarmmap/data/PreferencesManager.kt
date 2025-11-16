package com.neptun.alarmmap.data

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringSetPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.neptun.alarmmap.data.model.ThreatType
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "settings")

class PreferencesManager private constructor(private val context: Context) {
    
    private val AUTO_REFRESH_KEY = booleanPreferencesKey("auto_refresh")
    private val REFRESH_INTERVAL_KEY = intPreferencesKey("refresh_interval")
    private val SOUND_ENABLED_KEY = booleanPreferencesKey("sound_enabled")
    private val ENABLED_THREAT_TYPES_KEY = stringSetPreferencesKey("enabled_threat_types")
    
    val autoRefreshEnabled: Flow<Boolean> = context.dataStore.data
        .map { preferences ->
            preferences[AUTO_REFRESH_KEY] ?: true
        }
    
    val refreshInterval: Flow<Int> = context.dataStore.data
        .map { preferences ->
            preferences[REFRESH_INTERVAL_KEY] ?: 10
        }
    
    val soundEnabled: Flow<Boolean> = context.dataStore.data
        .map { preferences ->
            preferences[SOUND_ENABLED_KEY] ?: true
        }
    
    val enabledThreatTypes: Flow<Set<ThreatType>> = context.dataStore.data
        .map { preferences ->
            val savedTypes = preferences[ENABLED_THREAT_TYPES_KEY] ?: emptySet()
            if (savedTypes.isEmpty()) {
                ThreatType.values().toSet()
            } else {
                savedTypes.mapNotNull { name ->
                    try { ThreatType.valueOf(name) } catch (e: Exception) { null }
                }.toSet()
            }
        }
    
    suspend fun setAutoRefresh(enabled: Boolean) {
        context.dataStore.edit { preferences ->
            preferences[AUTO_REFRESH_KEY] = enabled
        }
    }
    
    suspend fun setRefreshInterval(seconds: Int) {
        context.dataStore.edit { preferences ->
            preferences[REFRESH_INTERVAL_KEY] = seconds
        }
    }
    
    suspend fun setSoundEnabled(enabled: Boolean) {
        context.dataStore.edit { preferences ->
            preferences[SOUND_ENABLED_KEY] = enabled
        }
    }
    
    suspend fun setEnabledThreatTypes(types: Set<ThreatType>) {
        context.dataStore.edit { preferences ->
            preferences[ENABLED_THREAT_TYPES_KEY] = types.map { it.name }.toSet()
        }
    }
    
    suspend fun toggleThreatType(type: ThreatType, enabled: Boolean) {
        context.dataStore.edit { preferences ->
            val current = preferences[ENABLED_THREAT_TYPES_KEY]?.mapNotNull {
                try { ThreatType.valueOf(it) } catch (e: Exception) { null }
            }?.toMutableSet() ?: ThreatType.values().toMutableSet()
            
            if (enabled) {
                current.add(type)
            } else {
                current.remove(type)
            }
            preferences[ENABLED_THREAT_TYPES_KEY] = current.map { it.name }.toSet()
        }
    }
    
    companion object {
        @Volatile
        private var INSTANCE: PreferencesManager? = null
        
        fun getInstance(context: Context): PreferencesManager {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: PreferencesManager(context.applicationContext).also {
                    INSTANCE = it
                }
            }
        }
    }
}

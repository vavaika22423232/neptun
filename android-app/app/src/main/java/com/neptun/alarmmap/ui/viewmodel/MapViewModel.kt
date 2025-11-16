package com.neptun.alarmmap.ui.viewmodel

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.neptun.alarmmap.data.PreferencesManager
import com.neptun.alarmmap.data.model.AlarmTrack
import com.neptun.alarmmap.data.model.ThreatType
import com.neptun.alarmmap.data.repository.AlarmRepository
import com.neptun.alarmmap.utils.SoundNotificationManager
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

data class MapUiState(
    val tracks: List<AlarmTrack> = emptyList(),
    val filteredTracks: List<AlarmTrack> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null,
    val isAutoRefreshEnabled: Boolean = true,
    val isSoundEnabled: Boolean = true,
    val enabledThreatTypes: Set<ThreatType> = ThreatType.values().toSet(),
    val showSettings: Boolean = false
)

class MapViewModel(
    private val repository: AlarmRepository = AlarmRepository(),
    private val context: Context
) : ViewModel() {
    
    private val prefsManager = PreferencesManager.getInstance(context)
    private val soundManager = SoundNotificationManager(context)
    private val _uiState = MutableStateFlow(MapUiState())
    val uiState: StateFlow<MapUiState> = _uiState.asStateFlow()
    
    private var autoRefreshJob: Job? = null
    
    init {
        loadEvents()
        startAutoRefresh()
        observePreferences()
    }
    
    private fun observePreferences() {
        viewModelScope.launch {
            combine(
                prefsManager.autoRefreshEnabled,
                prefsManager.soundEnabled,
                prefsManager.enabledThreatTypes
            ) { autoRefresh, sound, types ->
                Triple(autoRefresh, sound, types)
            }.collect { (autoRefresh, sound, types) ->
                val currentTracks = _uiState.value.tracks
                _uiState.value = _uiState.value.copy(
                    isAutoRefreshEnabled = autoRefresh,
                    isSoundEnabled = sound,
                    enabledThreatTypes = types,
                    filteredTracks = filterTracks(currentTracks, types)
                )
                
                if (autoRefresh && autoRefreshJob == null) {
                    startAutoRefresh()
                } else if (!autoRefresh) {
                    stopAutoRefresh()
                }
            }
        }
    }
    
    private fun filterTracks(tracks: List<AlarmTrack>, enabledTypes: Set<ThreatType>): List<AlarmTrack> {
        return tracks.filter { track ->
            val type = ThreatType.fromTrack(track)
            type in enabledTypes
        }
    }
    
    fun loadEvents() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            
            repository.getAlarmEvents()
                .onSuccess { response ->
                    val tracks = response.tracks ?: emptyList()
                    val filtered = filterTracks(tracks, _uiState.value.enabledThreatTypes)
                    
                    soundManager.onTracksUpdated(filtered.size, _uiState.value.isSoundEnabled)
                    
                    _uiState.value = _uiState.value.copy(
                        tracks = tracks,
                        filteredTracks = filtered,
                        isLoading = false,
                        error = null
                    )
                }
                .onFailure { exception ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        error = exception.message ?: "Unknown error occurred"
                    )
                }
        }
    }
    
    fun toggleThreatType(type: ThreatType, enabled: Boolean) {
        viewModelScope.launch {
            prefsManager.toggleThreatType(type, enabled)
        }
    }
    
    fun toggleAutoRefresh() {
        viewModelScope.launch {
            prefsManager.setAutoRefresh(!_uiState.value.isAutoRefreshEnabled)
        }
    }
    
    fun toggleSound() {
        viewModelScope.launch {
            prefsManager.setSoundEnabled(!_uiState.value.isSoundEnabled)
        }
    }
    
    fun toggleSettings() {
        _uiState.value = _uiState.value.copy(showSettings = !_uiState.value.showSettings)
    }
    
    private fun startAutoRefresh() {
        autoRefreshJob?.cancel()
        autoRefreshJob = viewModelScope.launch {
            while (isActive && _uiState.value.isAutoRefreshEnabled) {
                delay(10_000) // Refresh every 10 seconds
                loadEvents()
            }
        }
    }
    
    private fun stopAutoRefresh() {
        autoRefreshJob?.cancel()
        autoRefreshJob = null
    }
    
    override fun onCleared() {
        super.onCleared()
        stopAutoRefresh()
        soundManager.release()
    }
}

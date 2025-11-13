package com.neptun.alarmmap.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.neptun.alarmmap.data.model.AlarmTrack
import com.neptun.alarmmap.data.repository.AlarmRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

data class MapUiState(
    val tracks: List<AlarmTrack> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null,
    val isAutoRefreshEnabled: Boolean = true
)

class MapViewModel(
    private val repository: AlarmRepository = AlarmRepository()
) : ViewModel() {
    
    private val _uiState = MutableStateFlow(MapUiState())
    val uiState: StateFlow<MapUiState> = _uiState.asStateFlow()
    
    private var autoRefreshJob: Job? = null
    
    init {
        loadEvents()
        startAutoRefresh()
    }
    
    fun loadEvents() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            
            repository.getAlarmEvents()
                .onSuccess { response ->
                    _uiState.value = _uiState.value.copy(
                        tracks = response.tracks ?: emptyList(),
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
    
    fun toggleAutoRefresh() {
        val newState = !_uiState.value.isAutoRefreshEnabled
        _uiState.value = _uiState.value.copy(isAutoRefreshEnabled = newState)
        
        if (newState) {
            startAutoRefresh()
        } else {
            stopAutoRefresh()
        }
    }
    
    private fun startAutoRefresh() {
        autoRefreshJob?.cancel()
        autoRefreshJob = viewModelScope.launch {
            while (isActive && _uiState.value.isAutoRefreshEnabled) {
                delay(30_000) // Refresh every 30 seconds
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
    }
}

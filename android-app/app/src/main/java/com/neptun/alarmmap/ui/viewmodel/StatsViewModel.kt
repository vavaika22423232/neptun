package com.neptun.alarmmap.ui.viewmodel

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.neptun.alarmmap.data.model.AlarmTrack
import com.neptun.alarmmap.data.model.ThreatType
import com.neptun.alarmmap.data.repository.AlarmRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

data class ThreatStats(
    val type: ThreatType,
    val count: Int,
    val percentage: Float
)

data class StatsUiState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val todayCount: Int = 0,
    val weekCount: Int = 0,
    val monthCount: Int = 0,
    val totalCount: Int = 0,
    val threatStats: List<ThreatStats> = emptyList(),
    val lastUpdate: String = ""
)

class StatsViewModel(context: Context) : ViewModel() {
    private val repository = AlarmRepository()
    private val _uiState = MutableStateFlow(StatsUiState())
    val uiState: StateFlow<StatsUiState> = _uiState.asStateFlow()
    
    private val dateFormat = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault())
    private val calendar = Calendar.getInstance()
    
    init {
        loadStats()
    }
    
    fun loadStats() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            
            repository.getAlarmEvents()
                .onSuccess { response ->
                    val tracks = response.tracks ?: emptyList()
                    calculateStats(tracks)
                }
                .onFailure { error ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        error = "Помилка завантаження: ${error.message}"
                    )
                }
        }
    }
    
    private fun calculateStats(tracks: List<AlarmTrack>) {
        val now = Calendar.getInstance()
        val todayStart = Calendar.getInstance().apply {
            set(Calendar.HOUR_OF_DAY, 0)
            set(Calendar.MINUTE, 0)
            set(Calendar.SECOND, 0)
        }
        val weekStart = Calendar.getInstance().apply {
            add(Calendar.DAY_OF_YEAR, -7)
        }
        val monthStart = Calendar.getInstance().apply {
            add(Calendar.MONTH, -1)
        }
        
        var todayCount = 0
        var weekCount = 0
        var monthCount = 0
        val threatCounts = mutableMapOf<ThreatType, Int>()
        
        tracks.forEach { track ->
            try {
                val trackDate = dateFormat.parse(track.date)
                val trackCal = Calendar.getInstance().apply { time = trackDate ?: Date() }
                
                if (trackCal.after(todayStart)) todayCount++
                if (trackCal.after(weekStart)) weekCount++
                if (trackCal.after(monthStart)) monthCount++
                
                val type = ThreatType.fromTrack(track)
                threatCounts[type] = (threatCounts[type] ?: 0) + 1
            } catch (e: Exception) {
                // Skip invalid dates
            }
        }
        
        val total = tracks.size
        val threatStats = threatCounts.map { (type, count) ->
            ThreatStats(
                type = type,
                count = count,
                percentage = if (total > 0) (count.toFloat() / total * 100) else 0f
            )
        }.sortedByDescending { it.count }
        
        val updateTime = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
        
        _uiState.value = _uiState.value.copy(
            isLoading = false,
            todayCount = todayCount,
            weekCount = weekCount,
            monthCount = monthCount,
            totalCount = total,
            threatStats = threatStats,
            lastUpdate = updateTime
        )
    }
}

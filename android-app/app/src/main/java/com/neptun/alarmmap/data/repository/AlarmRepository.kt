package com.neptun.alarmmap.data.repository

import com.neptun.alarmmap.data.api.RetrofitClient
import com.neptun.alarmmap.data.model.ApiResponse
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class AlarmRepository {
    private val apiService = RetrofitClient.apiService
    
    suspend fun getAlarmEvents(): Result<ApiResponse> = withContext(Dispatchers.IO) {
        try {
            val response = apiService.getEvents()
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}

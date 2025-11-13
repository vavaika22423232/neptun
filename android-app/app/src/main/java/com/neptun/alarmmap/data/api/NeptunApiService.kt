package com.neptun.alarmmap.data.api

import com.neptun.alarmmap.data.model.ApiResponse
import retrofit2.http.GET

interface NeptunApiService {
    @GET("data")
    suspend fun getEvents(): ApiResponse
    
    companion object {
        const val BASE_URL = "https://neptun.in.ua/"
    }
}

package com.neptun.alarmmap.data.model

import com.google.gson.annotations.SerializedName

data class AlarmEvent(
    @SerializedName("id")
    val id: String,
    
    @SerializedName("lat")
    val latitude: Double,
    
    @SerializedName("lng")
    val longitude: Double,
    
    @SerializedName("text")
    val text: String,
    
    @SerializedName("type")
    val type: String,
    
    @SerializedName("source")
    val source: String,
    
    @SerializedName("ts")
    val timestamp: String,
    
    @SerializedName("expire")
    val expire: Long
)

data class AlarmRegion(
    @SerializedName("region")
    val region: String,
    
    @SerializedName("active")
    val active: Boolean,
    
    @SerializedName("start_ts")
    val startTimestamp: String?
)

data class ApiResponse(
    @SerializedName("events")
    val events: List<AlarmEvent>,
    
    @SerializedName("active_alarms")
    val activeAlarms: List<AlarmRegion>
)

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
    val type: String? = null,
    
    @SerializedName("threat_type")
    val threatType: String? = null,
    
    @SerializedName("source")
    val source: String,
    
    @SerializedName("ts")
    val timestamp: String? = null,
    
    @SerializedName("date")
    val date: String? = null,
    
    @SerializedName("expire")
    val expire: Long? = null,
    
    @SerializedName("place")
    val place: String? = null,
    
    @SerializedName("count")
    val count: Int? = null,
    
    @SerializedName("marker_icon")
    val markerIcon: String? = null
) {
    // Computed property to get the actual type
    val actualType: String
        get() = threatType ?: type ?: "default"
}

data class AlarmRegion(
    @SerializedName("region")
    val region: String,
    
    @SerializedName("active")
    val active: Boolean,
    
    @SerializedName("start_ts")
    val startTimestamp: String?
)

data class Trajectory(
    @SerializedName("id")
    val id: String,
    
    @SerializedName("path")
    val path: List<List<Double>>, // [[lat, lng], [lat, lng], ...]
    
    @SerializedName("type")
    val type: String? = null,
    
    @SerializedName("threat_type")
    val threatType: String? = null,
    
    @SerializedName("color")
    val color: String? = null
) {
    val actualType: String
        get() = threatType ?: type ?: "default"
}

data class ApiResponse(
    @SerializedName("tracks")
    val tracks: List<AlarmEvent>? = null,
    
    @SerializedName("events")
    val events: List<AlarmEvent>? = null,
    
    @SerializedName("trajectories")
    val trajectories: List<Trajectory>? = null,
    
    @SerializedName("active_alarms")
    val activeAlarms: List<AlarmRegion>? = null
) {
    // Computed property to get all events (tracks + events)
    val allEvents: List<AlarmEvent>
        get() = (tracks ?: emptyList()) + (events ?: emptyList())
}

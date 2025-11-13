package com.neptun.alarmmap.data.model

import com.google.gson.annotations.SerializedName

// Track = маркер на карті (загроза)
data class AlarmTrack(
    @SerializedName("id")
    val id: String,
    
    @SerializedName("lat")
    val latitude: Double,
    
    @SerializedName("lng")
    val longitude: Double,
    
    @SerializedName("text")
    val text: String,
    
    @SerializedName("threat_type")
    val threatType: String? = null,
    
    @SerializedName("marker_icon")
    val markerIcon: String? = null,
    
    @SerializedName("place")
    val place: String? = null,
    
    @SerializedName("channel")
    val channel: String? = null,
    
    @SerializedName("source_match")
    val sourceMatch: String? = null,
    
    @SerializedName("date")
    val date: String,
    
    @SerializedName("count")
    val count: Int? = null,
    
    @SerializedName("merged")
    val merged: Boolean? = false
)

// Event = текстова подія (не відображається на карті)
data class AlarmEvent(
    @SerializedName("id")
    val id: String,
    
    @SerializedName("text")
    val text: String,
    
    @SerializedName("date")
    val date: String,
    
    @SerializedName("source")
    val source: String? = null
)

data class ApiResponse(
    @SerializedName("tracks")
    val tracks: List<AlarmTrack>? = emptyList(),
    
    @SerializedName("events")
    val events: List<AlarmEvent>? = emptyList(),
    
    @SerializedName("all_sources")
    val allSources: List<String>? = emptyList()
)

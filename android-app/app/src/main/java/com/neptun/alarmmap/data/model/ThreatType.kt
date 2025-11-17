package com.neptun.alarmmap.data.model

enum class ThreatType(val displayName: String, val emoji: String) {
    SHAHED("Шахед", "✈️"),
    RAKETA("Ракета", "🚀"),
    FPV("FPV", "🛸"),
    KAB("КАБ", "💣"),
    OBSTRIL("Обстріл", "💥"),
    AVIA("Авіація", "🛩️"),
    PUSK("Пуск", "🔥"),
    RSZV("РСЗВ", "🎆"),
    ROZVED("Розвідка", "🔍"),
    VIBUH("Вибух", "⚡"),
    VIDBOI("Відбій", "✅"),
    OTHER("Інше", "⚠️");

    companion object {
        fun fromTrack(track: AlarmTrack): ThreatType {
            val markerIcon = track.markerIcon?.lowercase() ?: ""
            val threatType = track.threatType?.lowercase() ?: ""
            
            return when {
                markerIcon.contains("shahed") || threatType.contains("shahed") || threatType.contains("шахед") -> SHAHED
                markerIcon.contains("raketa") || threatType.contains("raketa") || threatType.contains("ракета") -> RAKETA
                markerIcon.contains("fpv") || threatType.contains("fpv") -> FPV
                markerIcon.contains("kab") || threatType.contains("kab") || threatType.contains("каб") -> KAB
                markerIcon.contains("obstril") || threatType.contains("obstril") || threatType.contains("artillery") -> OBSTRIL
                markerIcon.contains("avia") || threatType.contains("avia") -> AVIA
                markerIcon.contains("pusk") || threatType.contains("pusk") -> PUSK
                markerIcon.contains("rszv") || threatType.contains("rszv") || threatType.contains("рсзв") -> RSZV
                markerIcon.contains("rozved") || threatType.contains("rozved") || threatType.contains("розвід") -> ROZVED
                markerIcon.contains("vibuh") || threatType.contains("vibuh") || threatType.contains("вибух") -> VIBUH
                markerIcon.contains("vidboi") || threatType.contains("vidboi") || threatType.contains("відбій") -> VIDBOI
                else -> OTHER
            }
        }
    }
}

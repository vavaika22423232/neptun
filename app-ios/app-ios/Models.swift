import Foundation

// MARK: - API Response (точно як в Android ApiResponse)
struct ApiResponse: Codable {
    let tracks: [AlarmTrack]?
    let events: [AlarmEvent]?
    let allSources: [String]?
    
    enum CodingKeys: String, CodingKey {
        case tracks
        case events
        case allSources = "all_sources"
    }
}

// MARK: - Alarm Track (точно як в Android AlarmTrack)
struct AlarmTrack: Codable, Identifiable {
    let id: String
    let latitude: Double
    let longitude: Double
    let text: String?
    let threatType: String?
    let markerIcon: String?
    let place: String?
    let channel: String?
    let date: String?
    let count: Int?
    let merged: Bool?
    
    enum CodingKeys: String, CodingKey {
        case id
        case latitude = "lat"
        case longitude = "lng"
        case text
        case threatType = "threat_type"
        case markerIcon = "marker_icon"
        case place
        case channel
        case date
        case count
        case merged
    }
}

// MARK: - Alarm Event (точно як в Android AlarmEvent)
struct AlarmEvent: Codable, Identifiable {
    let id: String
    let text: String?
    let date: String?
    let source: String?
}

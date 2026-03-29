import '../models/map_models.dart';
import '../models/threat_event.dart';

class ThreatFeedService {
  List<ThreatEvent> buildEvents(List<ThreatMarker> markers) {
    return markers.map((marker) {
      final timestamp = _parseTimestamp(marker.date);
      final title = ThreatType.names[marker.threatType] ?? marker.threatType;
      final location = marker.place.isNotEmpty ? marker.place : 'Невідоме місце';

      return ThreatEvent(
        id: _buildId(marker, timestamp),
        threatType: marker.threatType,
        title: title,
        location: location,
        timestamp: timestamp,
        lat: marker.lat,
        lng: marker.lng,
        source: 'telegram',
        details: marker.text,
      );
    }).toList()
      ..sort((a, b) {
        if (a.timestamp == null && b.timestamp == null) return 0;
        if (a.timestamp == null) return 1;
        if (b.timestamp == null) return -1;
        return b.timestamp!.compareTo(a.timestamp!);
      });
  }

  Map<String, int> countByType(List<ThreatEvent> events) {
    final counts = <String, int>{};
    for (final event in events) {
      counts[event.threatType] = (counts[event.threatType] ?? 0) + 1;
    }
    return counts;
  }

  DateTime? _parseTimestamp(String raw) {
    if (raw.isEmpty) return null;
    return DateTime.tryParse(raw);
  }

  String _buildId(ThreatMarker marker, DateTime? timestamp) {
    final timePart = timestamp?.millisecondsSinceEpoch ?? 0;
    return '${marker.threatType}_${marker.lat}_${marker.lng}_$timePart';
  }
}

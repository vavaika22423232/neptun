class ThreatEvent {
  final String id;
  final String threatType;
  final String title;
  final String location;
  final DateTime? timestamp;
  final double? lat;
  final double? lng;
  final String source;
  final String details;

  ThreatEvent({
    required this.id,
    required this.threatType,
    required this.title,
    required this.location,
    required this.timestamp,
    required this.lat,
    required this.lng,
    required this.source,
    required this.details,
  });
}

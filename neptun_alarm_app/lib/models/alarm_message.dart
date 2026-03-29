class AlarmMessage {
  final String type;
  final String location;
  final String timestamp;
  final double? latitude;
  final double? longitude;
  final String text;

  AlarmMessage({
    required this.type,
    required this.location,
    required this.timestamp,
    this.latitude,
    this.longitude,
    required this.text,
  });

  factory AlarmMessage.fromJson(Map<String, dynamic> json) {
    return AlarmMessage(
      type: json['type'] ?? 'Невідомо',
      location: json['location'] ?? 'Невідоме місце',
      timestamp: json['timestamp'] ?? '',
      latitude: json['latitude']?.toDouble(),
      longitude: json['longitude']?.toDouble(),
      text: json['text'] ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
    'type': type,
    'location': location,
    'timestamp': timestamp,
    'latitude': latitude,
    'longitude': longitude,
    'text': text,
  };
}

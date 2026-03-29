/// Подія сповіщення з ID регіонів
class NotificationEvent {
  final String? oblastId;
  final String? raionId;
  final String? settlementId;
  
  final String title;
  final String body;
  final String threatType;
  final String alarmState;
  final bool isCritical;
  final DateTime timestamp;

  const NotificationEvent({
    this.oblastId,
    this.raionId,
    this.settlementId,
    required this.title,
    required this.body,
    this.threatType = '',
    this.alarmState = '',
    this.isCritical = false,
    required this.timestamp,
  });

  /// Чи є валідна геолокація
  bool get hasValidLocation => oblastId != null && oblastId!.isNotEmpty;

  /// Чи є конкретний район
  bool get hasRaion => raionId != null;

  /// Чи є конкретний населений пункт  
  bool get hasSettlement => settlementId != null;

  factory NotificationEvent.fromFcmData(Map<String, dynamic> data) {
    return NotificationEvent(
      oblastId: data['oblast_id'] as String?,
      raionId: data['raion_id'] as String?,
      settlementId: data['settlement_id'] as String?,
      title: data['title'] as String? ?? 'Тривога',
      body: data['body'] as String? ?? '',
      threatType: data['threat_type'] as String? ?? '',
      alarmState: data['alarm_state'] as String? ?? '',
      isCritical: data['is_critical'] == 'true',
      timestamp: DateTime.now(),
    );
  }

  @override
  String toString() => 'NotificationEvent(oblast: $oblastId, raion: $raionId, settlement: $settlementId)';
}

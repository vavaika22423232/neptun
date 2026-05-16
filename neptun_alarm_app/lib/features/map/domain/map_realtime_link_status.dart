/// Стан живого каналу даних для карти (SSE), без привʼязки до UI.
///
/// Частота `track_update` на клієнті висока — для «останнього оновлення» HUD
/// враховуються лише значущі типи подій (див. [DataStreamService]).
enum MapRealtimeLinkPhase {
  /// Ще не намагались підключитися (до першого виклику connect).
  idle,

  /// TCP / HTTP handshake до першого успішного кадру.
  connecting,

  /// SSE-сесія активна.
  live,

  /// Зʼєднання втрачено або сервер недоступний — йде backoff.
  reconnecting,
}

class MapRealtimeLinkStatus {
  const MapRealtimeLinkStatus({
    required this.phase,
    this.lastSignificantRefreshAt,
  });

  final MapRealtimeLinkPhase phase;

  /// Останній «змістовний» апдейт по мапі / тривогах (не high-frequency track).
  final DateTime? lastSignificantRefreshAt;

  static const initial = MapRealtimeLinkStatus(phase: MapRealtimeLinkPhase.idle);

  MapRealtimeLinkStatus copyWith({
    MapRealtimeLinkPhase? phase,
    DateTime? lastSignificantRefreshAt,
    bool clearRefreshAt = false,
  }) {
    return MapRealtimeLinkStatus(
      phase: phase ?? this.phase,
      lastSignificantRefreshAt: clearRefreshAt
          ? null
          : (lastSignificantRefreshAt ?? this.lastSignificantRefreshAt),
    );
  }
}

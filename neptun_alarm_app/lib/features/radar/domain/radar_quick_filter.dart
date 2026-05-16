/// Швидкий фільтр стрічки Радару за типами маркерів API.
enum RadarQuickFilter {
  /// Усі події без обмеження типу.
  all,

  /// БПЛА / шахед-подібні (включно з fpv як «активність» малих засобів).
  shahedLayer,

  /// Ракетна загроза, балістика, КАБ, РСЗВ, пускові.
  missiles,

  /// Стратегічна авіація / авіаподія на карті.
  aviation,

  /// Події тривоги / відбою.
  airRaid,

  /// Вибухи, обстріли, артилерія.
  blasts,
}

extension RadarQuickFilterLabels on RadarQuickFilter {
  String get shortLabelUk => switch (this) {
        RadarQuickFilter.all => 'Усі',
        RadarQuickFilter.shahedLayer => 'БПЛА',
        RadarQuickFilter.missiles => 'Ракети',
        RadarQuickFilter.aviation => 'Авіація',
        RadarQuickFilter.airRaid => 'Тривоги',
        RadarQuickFilter.blasts => 'Вибухи',
      };
}

extension RadarQuickFilterMatching on RadarQuickFilter {
  /// Чи збігається сира мапа маркера з обраною категорією (`threatType`/`type` із API).
  bool matchesMarker(Map<String, dynamic> m) {
    if (this == RadarQuickFilter.all) return true;
    final raw = (m['threatType'] ?? m['threat_type'] ?? m['type'] ?? '')
        .toString()
        .trim()
        .toLowerCase();
    if (raw.isEmpty) return false;

    return switch (this) {
      RadarQuickFilter.all => true,
      RadarQuickFilter.shahedLayer =>
        const {'shahed', 'drone', 'fpv', 'rozved'}.contains(raw),
      RadarQuickFilter.missiles => const {
          'raketa',
          'missile',
          'ballistic',
          'pusk',
          'kab',
          'rszv',
        }.contains(raw),
      RadarQuickFilter.aviation => raw == 'avia',
      RadarQuickFilter.airRaid => raw == 'alarm' || raw == 'alarm_cancel',
      RadarQuickFilter.blasts => const {
          'vibuh',
          'artillery',
          'obstril',
        }.contains(raw),
    };
  }
}

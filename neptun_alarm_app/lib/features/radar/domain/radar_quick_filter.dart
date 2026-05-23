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

  /// ППО / перехоплення (за типом API, якщо є).
  ppo,

  /// Лише події в обраних користувачем областях.
  myRegions,

  /// Висока важливість (ракети, балістика, щільні БПЛА).
  highPriority,
}

extension RadarQuickFilterLabels on RadarQuickFilter {
  String get shortLabelUk => switch (this) {
        RadarQuickFilter.all => 'Усі',
        RadarQuickFilter.shahedLayer => 'БПЛА',
        RadarQuickFilter.missiles => 'Ракети',
        RadarQuickFilter.aviation => 'Авіація',
        RadarQuickFilter.airRaid => 'Тривоги',
        RadarQuickFilter.blasts => 'Вибухи',
        RadarQuickFilter.ppo => 'ППО',
        RadarQuickFilter.myRegions => 'Мої області',
        RadarQuickFilter.highPriority => 'Важливі',
      };
}

extension RadarQuickFilterMatching on RadarQuickFilter {
  /// Чи збігається сира мапа маркера з обраною категорією (`threatType`/`type` із API).
  bool matchesMarker(
    Map<String, dynamic> m, {
    Set<String> myRegions = const {},
  }) {
    if (this == RadarQuickFilter.all) return true;
    final raw = (m['threatType'] ?? m['threat_type'] ?? m['type'] ?? '')
        .toString()
        .trim()
        .toLowerCase();
    if (raw.isEmpty && this != RadarQuickFilter.myRegions) return false;

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
      RadarQuickFilter.ppo =>
        const {'pvo', 'ppo', 'air_defense'}.contains(raw),
      RadarQuickFilter.myRegions => _matchesMyRegions(m, myRegions),
      RadarQuickFilter.highPriority => const {
          'raketa',
          'missile',
          'ballistic',
          'shahed',
          'drone',
          'kab',
        }.contains(raw),
    };
  }
}

bool _matchesMyRegions(Map<String, dynamic> m, Set<String> myRegions) {
  if (myRegions.isEmpty) return false;
  final place = (m['place'] ?? m['location'] ?? '').toString().toLowerCase();
  if (place.isEmpty) return false;
  for (final r in myRegions) {
    if (place.contains(r.toLowerCase())) return true;
  }
  return false;
}

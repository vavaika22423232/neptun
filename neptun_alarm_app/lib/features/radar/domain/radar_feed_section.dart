import 'threat_event.dart';

enum RadarFeedSectionKind {
  activeNow,
}

extension RadarFeedSectionKindLabels on RadarFeedSectionKind {
  String get titleUk => switch (this) {
        RadarFeedSectionKind.activeNow => 'Активні зараз',
      };
}

sealed class RadarSectionListItem {}

class RadarSectionHeaderItem extends RadarSectionListItem {
  RadarSectionHeaderItem(this.kind);
  final RadarFeedSectionKind kind;
}

class RadarSectionEventItem extends RadarSectionListItem {
  RadarSectionEventItem(this.event);
  final ThreatEvent event;
}

/// Одна стабільна секція — без перекидання карток між заголовками при оновленні API.
List<RadarSectionListItem> buildSectionedRadarFeed({
  required List<ThreatEvent> events,
}) {
  if (events.isEmpty) return [];
  final visible = events;

  return [
    RadarSectionHeaderItem(RadarFeedSectionKind.activeNow),
    for (final e in visible) RadarSectionEventItem(e),
  ];
}

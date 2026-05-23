import 'package:flutter/foundation.dart';

import '../../../pages/tabs/widgets/radar_feed_logic.dart';
import '../../../pages/tabs/widgets/radar_threat_label.dart';
import 'radar_quick_filter.dart';

enum ThreatSeverity { low, medium, high, critical }

enum ThreatSource { api, telegram, official }

/// Grouped live threat row for Radar feed (one card per threat type cluster).
@immutable
class ThreatEvent {
  const ThreatEvent({
    required this.id,
    required this.categoryKey,
    required this.title,
    required this.locations,
    required this.markers,
    required this.severity,
    required this.updatedAt,
    required this.signalCount,
    this.confidencePercent,
    this.isNew = false,
    this.source = ThreatSource.api,
  });

  final String id;
  final String categoryKey;
  final String title;
  final List<String> locations;
  final List<Map<String, dynamic>> markers;
  final ThreatSeverity severity;
  final DateTime? updatedAt;
  final int signalCount;
  final int? confidencePercent;
  final bool isNew;
  final ThreatSource source;

  String get locationLine =>
      locations.isEmpty ? 'Локація уточнюється' : locations.take(3).join(', ');

  String get updatedLabel {
    final t = updatedAt;
    if (t == null) return 'оновлення —';
    final diff = DateTime.now().difference(t);
    if (diff.inSeconds < 50) return 'щойно';
    if (diff.inMinutes < 60) return 'оновлено ${diff.inMinutes} хв тому';
    if (diff.inHours < 24) return 'оновлено ${diff.inHours} год тому';
    return 'оновлено ${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';
  }

  Map<String, dynamic> get primaryRaw =>
      markers.isNotEmpty ? markers.first : const <String, dynamic>{};
}

ThreatSeverity severityForTypeKey(String typeKey) {
  switch (typeKey.toLowerCase()) {
    case 'ballistic':
    case 'raketa':
    case 'missile':
      return ThreatSeverity.critical;
    case 'shahed':
    case 'drone':
    case 'kab':
      return ThreatSeverity.high;
    case 'avia':
      return ThreatSeverity.medium;
    default:
      return ThreatSeverity.low;
  }
}

List<ThreatEvent> buildThreatEvents(
  List<Map<String, dynamic>> markers, {
  RadarQuickFilter filter = RadarQuickFilter.all,
  String searchQuery = '',
  Set<String> myRegions = const {},
}) {
  final filtered = markers.where((m) {
    if (!filter.matchesMarker(m, myRegions: myRegions)) return false;
    if (searchQuery.trim().isEmpty) return true;
    final q = searchQuery.trim().toLowerCase();
    final place = (m['place'] ?? m['location'] ?? '').toString().toLowerCase();
    final type = (m['threatType'] ?? m['threat_type'] ?? m['type'] ?? '')
        .toString()
        .toLowerCase();
    final label = radarThreatTypeLabel(type).toLowerCase();
    return place.contains(q) || type.contains(q) || label.contains(q);
  }).toList();

  final grouped = <String, List<Map<String, dynamic>>>{};
  for (final m in filtered) {
    final key =
        (m['threatType'] ?? m['threat_type'] ?? m['type'] ?? 'unknown').toString();
    grouped.putIfAbsent(key, () => []).add(m);
  }

  final now = DateTime.now();
  final events = <ThreatEvent>[];
  for (final entry in grouped.entries) {
    final list = entry.value;
    DateTime? newest;
    int? bestConfidence;
    final places = <String>[];
    for (final m in list) {
      final t = radarMarkerTimestamp(m);
      if (t != null && (newest == null || t.isAfter(newest))) newest = t;
      final place = (m['place'] ?? m['location'] ?? '').toString().trim();
      if (place.isNotEmpty && !places.contains(place)) places.add(place);
      final q = m['track_quality_score'] ?? m['trackQualityScore'];
      if (q is num) {
        final pct = (q * (q <= 1 ? 100 : 1)).round();
        if (bestConfidence == null || pct > bestConfidence) bestConfidence = pct;
      }
    }
    final isNew = newest != null && now.difference(newest).inMinutes < 8;
    events.add(
      ThreatEvent(
        id: entry.key,
        categoryKey: entry.key,
        title: radarThreatTypeLabel(entry.key),
        locations: places,
        markers: list,
        severity: severityForTypeKey(entry.key),
        updatedAt: newest,
        signalCount: list.length,
        confidencePercent: bestConfidence,
        isNew: isNew,
      ),
    );
  }

  events.sort((a, b) {
    final ta = a.updatedAt;
    final tb = b.updatedAt;
    if (ta == null && tb == null) return a.id.compareTo(b.id);
    if (ta == null) return 1;
    if (tb == null) return -1;
    final byTime = tb.compareTo(ta);
    return byTime != 0 ? byTime : a.id.compareTo(b.id);
  });
  return events;
}

import 'radar_threat_label.dart';

/// Одна подія у стрічці Радару (після сортування та групування).
class RadarFeedEntry {
  RadarFeedEntry({
    required this.raw,
    required this.sortKey,
    required this.place,
    required this.typeKey,
    required this.typeLabel,
    required this.displayTime,
  });

  final Map<String, dynamic> raw;
  final DateTime? sortKey;
  final String place;
  final String typeKey;
  final String typeLabel;
  final String displayTime;
}

sealed class RadarListItem {}

class RadarSectionTitleItem extends RadarListItem {
  RadarSectionTitleItem(this.title);
  final String title;
}

class RadarFeedRowItem extends RadarListItem {
  RadarFeedRowItem(this.entry);
  final RadarFeedEntry entry;
}

/// Парсинг маркерів API, сортування від новіших до старіших.
List<RadarFeedEntry> buildSortedRadarFeedEntries(
  List<Map<String, dynamic>> markers,
) {
  final out = <RadarFeedEntry>[];
  for (final m in markers) {
    final dateStr = (m['date'] ?? m['timestamp'] ?? '').toString();
    final sortKey = DateTime.tryParse(dateStr);
    final typeKey =
        (m['threatType'] ?? m['threat_type'] ?? m['type'] ?? 'unknown')
            .toString();
    final place = (m['place'] ?? m['location'] ?? 'Невідомий регіон').toString();
    final displayTime = (m['time'] ?? '--:--').toString();
    out.add(
      RadarFeedEntry(
        raw: m,
        sortKey: sortKey,
        place: place,
        typeKey: typeKey,
        typeLabel: radarThreatTypeLabel(typeKey),
        displayTime: displayTime,
      ),
    );
  }
  out.sort((a, b) {
    final ta = a.sortKey;
    final tb = b.sortKey;
    if (ta == null && tb == null) return 0;
    if (ta == null) return 1;
    if (tb == null) return -1;
    return tb.compareTo(ta);
  });
  return out;
}

/// Заголовки «Сьогодні» / «Раніше» для sliver-стрічки.
List<RadarListItem> buildRadarFeedListItems(List<RadarFeedEntry> sorted) {
  final now = DateTime.now();
  final todayStart = DateTime(now.year, now.month, now.day);
  final tomorrow = todayStart.add(const Duration(days: 1));

  final today = <RadarFeedEntry>[];
  final earlier = <RadarFeedEntry>[];
  for (final e in sorted) {
    final t = e.sortKey;
    if (t != null && !t.isBefore(todayStart) && t.isBefore(tomorrow)) {
      today.add(e);
    } else {
      earlier.add(e);
    }
  }

  final out = <RadarListItem>[];
  if (today.isNotEmpty) {
    out.add(RadarSectionTitleItem('Сьогодні'));
    for (final e in today) {
      out.add(RadarFeedRowItem(e));
    }
  }
  if (earlier.isNotEmpty) {
    out.add(RadarSectionTitleItem('Раніше'));
    for (final e in earlier) {
      out.add(RadarFeedRowItem(e));
    }
  }
  return out;
}

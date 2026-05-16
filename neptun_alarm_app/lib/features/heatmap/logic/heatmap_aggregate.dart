import 'package:neptun_alarm_app/services/region_database.dart';

import '../data/heatmap_oblast_state_ids.dart';

/// Зводить лічильники за назвами районів/областей до id `1`…`27` для GeoJSON.
Map<String, int> aggregateHeatmapCountsByStateId(
  Map<String, int> mergedCountsByDisplayName,
  RegionDatabase regionDb,
) {
  regionDb.initialize();
  final out = <String, int>{};

  void addToState(String? stateId, int delta) {
    if (stateId == null || delta <= 0) return;
    out[stateId] = (out[stateId] ?? 0) + delta;
  }

  for (final e in mergedCountsByDisplayName.entries) {
    final name = e.key.trim();
    if (name.isEmpty) continue;
    final n = e.value;
    if (n <= 0) continue;

    final raionId = regionDb.getRaionIdByName(name);
    if (raionId != null) {
      final oblastUa = regionDb.getParentOblastId(raionId);
      addToState(
        oblastUa != null ? heatmapStateIdForUaOblast(oblastUa) : null,
        n,
      );
      continue;
    }

    final oblastId = regionDb.getOblastIdByName(name);
    if (oblastId != null) {
      addToState(heatmapStateIdForUaOblast(oblastId), n);
    }
  }

  return out;
}

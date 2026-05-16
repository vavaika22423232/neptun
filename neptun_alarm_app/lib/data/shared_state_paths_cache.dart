import 'dart:ui' show Path;

import 'package:neptun_alarm_app/core/utils/app_debug_log.dart';
import 'package:neptun_alarm_app/data/ukraine_region_paths.dart';
import 'package:neptun_alarm_app/utils/svg_path_parser.dart';

/// Parsed SVG paths for Ukraine oblasts (keys: API numeric state ids `'1'`–`'27'`).
/// Filled by [NativeMapPage] or [loadStateSvgPathsIfEmpty] for heatmap-only flows.
class SharedStatePathsCache {
  SharedStatePathsCache._();

  static final Map<String, List<Path>> instance = {};

  /// Parses oblast SVG paths once (e.g. heatmap opened before main map).
  static Future<void> loadStateSvgPathsIfEmpty() async {
    if (instance.isNotEmpty) return;
    const yieldEvery = 8;
    var i = 0;
    for (final entry in UkraineRegionPaths.regionPaths.entries) {
      final regionId = entry.key;
      final pathStrings = entry.value;
      final paths = <Path>[];
      for (final pathData in pathStrings) {
        try {
          paths.add(SvgPathParser.parsePath(pathData));
        } catch (e) {
          appDebugLog('SharedStatePathsCache: parse error $regionId: $e');
        }
      }
      instance[regionId] = paths;
      if (++i % yieldEvery == 0) await Future.delayed(Duration.zero);
    }
    appDebugLog('SharedStatePathsCache: parsed ${instance.length} states');
  }
}

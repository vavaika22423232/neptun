import 'package:flutter/material.dart';

import '../../../../models/map_models.dart';
import '../../../../theme/map_colors.dart';

/// Ballistic threat banner overlay.
class BallisticThreatOverlay extends StatelessWidget {
  final VoidCallback onDismiss;

  const BallisticThreatOverlay({super.key, required this.onDismiss});

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Positioned(
          top: MediaQuery.of(context).padding.top + 12,
          left: 16,
          right: 16,
          child: Center(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.error,
                borderRadius: BorderRadius.circular(14),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.15),
                    blurRadius: 10,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(
                    Icons.rocket_launch_rounded,
                    color: Colors.white,
                    size: 22,
                  ),
                  const SizedBox(width: 12),
                  const Flexible(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Загроза балістики',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 15,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        Padding(
                          padding: EdgeInsets.only(top: 2),
                          child: Text(
                            'де зараз повітряна тривога',
                            style: TextStyle(
                              color: Colors.white70,
                              fontSize: 13,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  GestureDetector(
                    onTap: onDismiss,
                    child: Icon(
                      Icons.close_rounded,
                      color: Colors.white.withValues(alpha: 0.8),
                      size: 20,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}

/// All-clear ballistic banner overlay with fade animation.
class AllClearOverlay extends StatelessWidget {
  final double progress;
  final String message;

  const AllClearOverlay({
    super.key,
    required this.progress,
    required this.message,
  });

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Positioned(
          top: MediaQuery.of(context).padding.top + 12,
          left: 16,
          right: 16,
          child: Center(
            child: AnimatedOpacity(
              opacity: progress < 0.7 ? 1.0 : (1.0 - (progress - 0.7) * 3.3),
              duration: const Duration(milliseconds: 200),
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 20,
                  vertical: 14,
                ),
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.secondary,
                  borderRadius: BorderRadius.circular(14),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.15),
                      blurRadius: 10,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(
                      Icons.check_circle_rounded,
                      color: Colors.white,
                      size: 22,
                    ),
                    const SizedBox(width: 12),
                    Flexible(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Відбій балістики',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 15,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          if (message.contains('\n'))
                            Padding(
                              padding: const EdgeInsets.only(top: 2),
                              child: Text(
                                message.split('\n').last,
                                style: TextStyle(
                                  color: Colors.white.withValues(alpha: 0.85),
                                  fontSize: 13,
                                ),
                              ),
                            ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

/// Map legend (alarm / no alarm). Optional: fromCache + lastUpdate for connectivity hint.
class MapLegend extends StatelessWidget {
  final MapColors colors;
  final bool fromCache;
  final DateTime? lastUpdate;

  const MapLegend({
    super.key,
    required this.colors,
    this.fromCache = false,
    this.lastUpdate,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        decoration: BoxDecoration(
          color: colors.panelBg.withValues(alpha: 0.9),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: colors.panelBorder),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            _legendItem(colors.normalFill, 'Немає тривоги', colors),
            const SizedBox(width: 24),
            _legendItem(colors.alarmFillState, 'Тривога', colors),
            if (fromCache || lastUpdate != null) ...[
              const SizedBox(width: 16),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: fromCache
                      ? colors.textSecondary.withValues(alpha: 0.2)
                      : colors.panelBorder.withValues(alpha: 0.5),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  fromCache && lastUpdate != null
                      ? 'З кешу • ${_formatLastUpdate(lastUpdate!)}'
                      : fromCache
                      ? 'З кешу'
                      : lastUpdate != null
                      ? _formatLastUpdate(lastUpdate!)
                      : '',
                  style: TextStyle(color: colors.textSecondary, fontSize: 10),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  static String _formatLastUpdate(DateTime dt) {
    final diff = DateTime.now().difference(dt);
    if (diff.inMinutes < 1) return 'Щойно';
    if (diff.inMinutes < 60) return '${diff.inMinutes} хв тому';
    if (diff.inHours < 24) return '${diff.inHours} год тому';
    return '${diff.inDays} д тому';
  }

  static Widget _legendItem(Color color, String label, MapColors colors) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 16,
          height: 16,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(4),
            border: Border.all(color: colors.panelBorder),
          ),
        ),
        const SizedBox(width: 8),
        Text(
          label,
          style: TextStyle(color: colors.textSecondary, fontSize: 12),
        ),
      ],
    );
  }
}

/// Threat stats summary panel - tap to open full dialog.
class ThreatStatsPanel extends StatelessWidget {
  final MapColors colors;
  final List<ThreatMarker> visibleMarkers;
  final VoidCallback onTap;

  const ThreatStatsPanel({
    super.key,
    required this.colors,
    required this.visibleMarkers,
    required this.onTap,
  });

  static Map<String, int> countAndGroup(List<ThreatMarker> markers) {
    final counts = <String, int>{};
    for (final marker in markers) {
      counts[marker.threatType] = (counts[marker.threatType] ?? 0) + 1;
    }
    final grouped = <String, int>{};
    for (final entry in counts.entries) {
      final type = entry.key;
      final count = entry.value;
      if (type == 'shahed' || type == 'fpv') {
        grouped['shahed'] = (grouped['shahed'] ?? 0) + count;
      } else if (type == 'raketa' || type == 'pusk') {
        grouped['raketa'] = (grouped['raketa'] ?? 0) + count;
      } else if (type == 'kab' || type == 'rszv') {
        grouped['kab'] = (grouped['kab'] ?? 0) + count;
      } else if (type == 'rozved') {
        grouped['rozved'] = (grouped['rozved'] ?? 0) + count;
      } else if (type == 'avia') {
        grouped['avia'] = (grouped['avia'] ?? 0) + count;
      } else {
        grouped[type] = count;
      }
    }
    return grouped;
  }

  static String _getThreatEmoji(String type) {
    switch (type) {
      case 'shahed':
        return '🛩️';
      case 'raketa':
        return '🚀';
      case 'kab':
        return '💣';
      case 'rozved':
        return '🔍';
      case 'avia':
        return '✈️';
      default:
        return '⚠️';
    }
  }

  static String _getThreatLabel(String type) {
    switch (type) {
      case 'shahed':
        return 'БПЛА';
      case 'raketa':
        return 'Ракети';
      case 'kab':
        return 'КАБи';
      case 'rozved':
        return 'Розвідники';
      case 'avia':
        return 'Авіація';
      default:
        return 'Інше';
    }
  }

  static Color _getThreatColor(String type) {
    switch (type) {
      case 'shahed':
        return Colors.orange;
      case 'raketa':
        return Colors.red;
      case 'kab':
        return Colors.redAccent;
      case 'rozved':
        return Colors.amber;
      case 'avia':
        return Colors.purple;
      default:
        return Colors.white;
    }
  }

  @override
  Widget build(BuildContext context) {
    final groupedCounts = countAndGroup(visibleMarkers);
    final sortedEntries = groupedCounts.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));

    if (sortedEntries.isEmpty) return const SizedBox.shrink();

    final total = sortedEntries.fold<int>(0, (sum, e) => sum + e.value);

    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        decoration: BoxDecoration(
          color: colors.panelBg.withValues(alpha: 0.9),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: colors.panelBorder),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.flight_rounded, size: 14, color: Colors.orange),
                const SizedBox(width: 4),
                Text(
                  'Загрози ($total)',
                  style: TextStyle(
                    color: colors.textPrimary,
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            ...sortedEntries
                .take(4)
                .map(
                  (entry) => Padding(
                    padding: const EdgeInsets.symmetric(vertical: 2),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          _getThreatEmoji(entry.key),
                          style: const TextStyle(fontSize: 12),
                        ),
                        const SizedBox(width: 4),
                        Text(
                          '${entry.value}',
                          style: TextStyle(
                            color: _getThreatColor(entry.key),
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(width: 4),
                        Text(
                          _getThreatLabel(entry.key),
                          style: TextStyle(
                            color: colors.textSecondary,
                            fontSize: 10,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
          ],
        ),
      ),
    );
  }
}

/// Operator mode toggle (debug only).
class MapOperatorToggle extends StatelessWidget {
  final MapColors colors;
  final VoidCallback onToggle;

  const MapOperatorToggle({
    super.key,
    required this.colors,
    required this.onToggle,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onToggle,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: colors.panelBg,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: colors.panelBorder),
        ),
        child: Text('OP', style: TextStyle(color: colors.textAccent)),
      ),
    );
  }
}

/// Shows the threat statistics dialog with filter chips and history.
void showThreatStatsDialog(
  BuildContext context, {
  required MapColors colors,
  required List<ThreatMarker> threatMarkers,
  required Set<String> filterableThreatTypes,
  required Set<String> visibleThreatTypes,
  required void Function(String type, bool selected) onFilterToggled,
  required List<ThreatHistoryEntry> threatHistory,
  int timeRangeMinutes = 60,
}) {
  final filtered = threatMarkers
      .where(
        (m) =>
            visibleThreatTypes.isEmpty ||
            visibleThreatTypes.contains(m.threatType),
      )
      .toList();
  final visibleCounts = <String, int>{};
  for (final m in filtered) {
    visibleCounts[m.threatType] = (visibleCounts[m.threatType] ?? 0) + 1;
  }
  final total = visibleCounts.values.fold<int>(0, (sum, v) => sum + v);

  String getThreatEmoji(String type) {
    switch (type) {
      case 'shahed':
        return '🛩️';
      case 'raketa':
        return '🚀';
      case 'kab':
        return '💣';
      case 'rozved':
        return '🔍';
      case 'avia':
        return '✈️';
      default:
        return '⚠️';
    }
  }

  Color getThreatColor(String type) {
    switch (type) {
      case 'shahed':
        return Colors.orange;
      case 'raketa':
        return Colors.red;
      case 'kab':
        return Colors.redAccent;
      case 'rozved':
        return Colors.amber;
      case 'avia':
        return Colors.purple;
      default:
        return Colors.white;
    }
  }

  showDialog(
    context: context,
    builder: (ctx) => StatefulBuilder(
      builder: (ctx, setDialogState) => AlertDialog(
        backgroundColor: colors.panelBg,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Row(
          children: [
            const Text('🎯', style: TextStyle(fontSize: 24)),
            const SizedBox(width: 8),
            Text(
              'Статистика загроз',
              style: TextStyle(
                color: colors.textPrimary,
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: colors.isDark
                    ? Colors.orange.withValues(alpha: 0.1)
                    : Colors.orange.withValues(alpha: 0.05),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.orange.withValues(alpha: 0.3)),
              ),
              child: Row(
                children: [
                  const Icon(
                    Icons.info_outline,
                    color: Colors.orange,
                    size: 18,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Орієнтовно за останні $timeRangeMinutes хв',
                      style: TextStyle(
                        color: colors.textSecondary,
                        fontSize: 12,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: filterableThreatTypes.map((type) {
                final selected = visibleThreatTypes.contains(type);
                final label = ThreatType.names[type] ?? type;
                return FilterChip(
                  label: Text(label, style: const TextStyle(fontSize: 11)),
                  selected: selected,
                  onSelected: (value) {
                    onFilterToggled(type, value);
                    setDialogState(() {});
                  },
                  selectedColor: colors.isDark
                      ? colors.textAccent.withValues(alpha: 0.2)
                      : colors.textAccent.withValues(alpha: 0.15),
                  checkmarkColor: colors.textAccent,
                  backgroundColor: colors.isDark
                      ? colors.panelBg
                      : Colors.white,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(10),
                    side: BorderSide(color: colors.panelBorder),
                  ),
                );
              }).toList(),
            ),
            const SizedBox(height: 16),
            Center(
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 20,
                  vertical: 12,
                ),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      Colors.red.withValues(alpha: 0.2),
                      Colors.orange.withValues(alpha: 0.2),
                    ],
                  ),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Column(
                  children: [
                    Text(
                      '$total',
                      style: TextStyle(
                        color: colors.textPrimary,
                        fontSize: 36,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    Text(
                      'об\'єктів у повітрі',
                      style: TextStyle(
                        color: colors.textSecondary,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            ...visibleCounts.entries.map((entry) {
              final icon = getThreatEmoji(entry.key);
              final name = ThreatType.names[entry.key] ?? entry.key;
              final color = getThreatColor(entry.key);
              return Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Row(
                  children: [
                    Text(icon, style: const TextStyle(fontSize: 18)),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        name,
                        style: TextStyle(
                          color: colors.textPrimary,
                          fontSize: 14,
                        ),
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: color.withValues(alpha: 0.2),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        '${entry.value}',
                        style: TextStyle(
                          color: color,
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ],
                ),
              );
            }),
            if (threatHistory.isNotEmpty) ...[
              const SizedBox(height: 16),
              Text(
                'Історія (останні інтервали)',
                style: TextStyle(
                  color: colors.textPrimary,
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 8),
              ...threatHistory.reversed.take(6).map((entry) {
                final time =
                    '${entry.timestamp.hour.toString().padLeft(2, '0')}:${entry.timestamp.minute.toString().padLeft(2, '0')}';
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 2),
                  child: Row(
                    children: [
                      Text(
                        time,
                        style: TextStyle(
                          color: colors.textSecondary,
                          fontSize: 12,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: LinearProgressIndicator(
                          value: (entry.total / (total == 0 ? 1 : total)).clamp(
                            0.0,
                            1.0,
                          ),
                          minHeight: 6,
                          backgroundColor: colors.panelBorder,
                          valueColor: AlwaysStoppedAnimation<Color>(
                            colors.textAccent.withValues(alpha: 0.6),
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        '${entry.total}',
                        style: TextStyle(
                          color: colors.textPrimary,
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                );
              }),
            ],
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text('Закрити', style: TextStyle(color: colors.textAccent)),
          ),
        ],
      ),
    ),
  );
}

/// Operator panel with refresh button (debug only).
class MapOperatorPanel extends StatelessWidget {
  final MapColors colors;
  final VoidCallback onRefresh;

  const MapOperatorPanel({
    super.key,
    required this.colors,
    required this.onRefresh,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: colors.panelBg,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: colors.panelBorder),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          IconButton(
            visualDensity: VisualDensity.compact,
            icon: Icon(Icons.refresh, size: 18, color: colors.textAccent),
            onPressed: onRefresh,
          ),
        ],
      ),
    );
  }
}

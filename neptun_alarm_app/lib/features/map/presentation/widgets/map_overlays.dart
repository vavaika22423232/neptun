import 'package:flutter/material.dart';
import '../../../../models/map_models.dart';
import '../../../../theme/map_colors.dart';
import '../../../../design/design_exports.dart';
import '../../../../core/widgets/neptun_shell_modal.dart';

/// Premium Ballistic threat banner.
class BallisticThreatOverlay extends StatelessWidget {
  final VoidCallback onDismiss;

  const BallisticThreatOverlay({super.key, required this.onDismiss});

  @override
  Widget build(BuildContext context) {
    return Positioned(
      top: MediaQuery.of(context).padding.top + 16,
      left: 12,
      right: 12,
      child: Center(
        child: NeptunCard(
          onTap: onDismiss,
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          borderColor: NeptunStatus.alarm.withValues(alpha: 0.6),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: NeptunStatus.alarm.withValues(alpha: 0.2),
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.rocket_launch_rounded,
                  color: NeptunStatus.alarm,
                  size: 24,
                ),
              ),
              const SizedBox(width: 14),
              Flexible(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'ЗАГРОЗА БАЛІСТИКИ',
                      style: NeptunTypography.h4Style.copyWith(
                        color: NeptunStatus.alarm,
                        letterSpacing: 1.2,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'Негайно прямуйте в укриття!',
                      style: NeptunTypography.bodySmallStyle.copyWith(
                        color: Theme.of(
                          context,
                        ).colorScheme.onSurface.withValues(alpha: 0.7),
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              Icon(
                Icons.close_rounded,
                color: Theme.of(
                  context,
                ).colorScheme.onSurface.withValues(alpha: 0.3),
                size: 20,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// All-clear ballistic banner.
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
    if (progress >= 1.0) return const SizedBox.shrink();

    return Positioned(
      top: MediaQuery.of(context).padding.top + 16,
      left: 12,
      right: 12,
      child: Center(
        child: AnimatedOpacity(
          opacity: progress < 0.7
              ? 1.0
              : (1.0 - (progress - 0.7) * 3.3).clamp(0.0, 1.0),
          duration: const Duration(milliseconds: 300),
          child: NeptunCard(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
            borderColor: NeptunStatus.safe.withValues(alpha: 0.5),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: NeptunStatus.safe.withValues(alpha: 0.2),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(
                    Icons.check_circle_rounded,
                    color: NeptunStatus.safe,
                    size: 24,
                  ),
                ),
                const SizedBox(width: 14),
                Flexible(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'ВІДБІЙ БАЛІСТИКИ',
                        style: NeptunTypography.h4Style.copyWith(
                          color: NeptunStatus.safe,
                          letterSpacing: 1.2,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        'Загроза минула',
                        style: NeptunTypography.bodySmallStyle.copyWith(
                          color: Theme.of(
                            context,
                          ).colorScheme.onSurface.withValues(alpha: 0.7),
                          fontWeight: FontWeight.w600,
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
    );
  }
}

/// Map legend revamped with NeptunCard.
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
      child: NeptunCard(
        padding: const EdgeInsets.symmetric(
          horizontal: NeptunSpacing.lg,
          vertical: 10,
        ),
        borderRadius: NeptunRadius.pill,
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            _legendItem(colors.normalFill, 'НОРМА'),
            const SizedBox(width: 16),
            _legendItem(colors.alarmStrokeState, 'ТРИВОГА'),
            if (fromCache || lastUpdate != null) ...[
              const SizedBox(width: 12),
              Container(
                width: 1,
                height: 10,
                decoration: BoxDecoration(
                  color: colors.panelBorder.withValues(alpha: 0.3),
                  borderRadius: BorderRadius.circular(1),
                ),
              ),
              const SizedBox(width: 12),
              Text(
                fromCache ? 'КЕШ' : _formatLastUpdate(lastUpdate),
                style: NeptunTypography.microStyle.copyWith(
                  color: colors.textSecondary.withValues(alpha: 0.8),
                  fontWeight: FontWeight.w800,
                  letterSpacing: 0.8,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  String _formatLastUpdate(DateTime? dt) {
    if (dt == null) return '';
    final diff = DateTime.now().difference(dt);
    if (diff.inSeconds < 10) return 'Live';
    if (diff.inMinutes < 1) return 'Щойно';
    return '${diff.inMinutes}м';
  }

  Widget _legendItem(Color color, String label) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(
            color: color,
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(color: color.withValues(alpha: 0.3), blurRadius: 4),
            ],
          ),
        ),
        const SizedBox(width: 8),
        Text(
          label,
          style: NeptunTypography.microStyle.copyWith(
            color: colors.textSecondary,
            fontWeight: FontWeight.w800,
            letterSpacing: 0.6,
          ),
        ),
      ],
    );
  }
}

/// Threat stats summary panel.
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

  @override
  Widget build(BuildContext context) {
    final groupedCounts = _countAndGroup(visibleMarkers);
    final sortedEntries = groupedCounts.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));

    if (sortedEntries.isEmpty) return const SizedBox.shrink();

    final total = sortedEntries.fold<int>(0, (sum, e) => sum + e.value);

    return NeptunCard(
      onTap: onTap,
      padding: const EdgeInsets.all(12),
      borderRadius: NeptunRadius.xl,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(
                Icons.emergency_rounded,
                size: 14,
                color: NeptunStatus.alarm,
              ),
              const SizedBox(width: 6),
              Text(
                'ЦІЛІ ($total)',
                style: NeptunTypography.microStyle.copyWith(
                  color: colors.textPrimary,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 0.8,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          ...sortedEntries
              .take(3)
              .map(
                (entry) => Padding(
                  padding: const EdgeInsets.symmetric(vertical: 3),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        _getThreatEmoji(entry.key),
                        style: const TextStyle(fontSize: 12),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        '${entry.value}',
                        style: NeptunTypography.h4Style.copyWith(
                          color: _getThreatColor(entry.key),
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        _getThreatLabel(entry.key).toUpperCase(),
                        style: NeptunTypography.microStyle.copyWith(
                          color: colors.textSecondary,
                          fontWeight: FontWeight.w700,
                          fontSize: 9,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
        ],
      ),
    );
  }

  Map<String, int> _countAndGroup(List<ThreatMarker> markers) {
    final counts = <String, int>{};
    for (final marker in markers) {
      counts[marker.threatType] = (counts[marker.threatType] ?? 0) + 1;
    }
    return counts;
  }

  String _getThreatEmoji(String type) => ThreatType.emojis[type] ?? '⚠️';
  String _getThreatLabel(String type) => ThreatType.names[type] ?? 'Інше';
  Color _getThreatColor(String type) {
    if (type == 'shahed' || type == 'fpv') return Colors.orange;
    if (type == 'raketa' || type == 'pusk') return Colors.red;
    return Colors.white;
  }
}

/// Operator mode toggle.
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
    return NeptunCard(
      onTap: onToggle,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      borderRadius: NeptunRadius.md,
      child: Text(
        'OP',
        style: NeptunTypography.microStyle.copyWith(
          color: colors.textAccent,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }
}

/// Operator panel.
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
    return NeptunCard(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
      borderRadius: NeptunRadius.md,
      child: IconButton(
        visualDensity: VisualDensity.compact,
        icon: Icon(Icons.refresh, size: 18, color: colors.textAccent),
        onPressed: onRefresh,
      ),
    );
  }
}

/// Premium Threat Statistics Dialog.
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
  NeptunShellModal.showDialog(
    context: context,
    builder: (ctx) => StatefulBuilder(
      builder: (ctx, setDialogState) {
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

        return AlertDialog(
          backgroundColor: Colors.transparent,
          insetPadding: const EdgeInsets.symmetric(
            horizontal: 20,
            vertical: 24,
          ),
          contentPadding: EdgeInsets.zero,
          content: NeptunCard(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Text('🎯', style: TextStyle(fontSize: 24)),
                    const SizedBox(width: 12),
                    Text(
                      'СТАТИСТИКА',
                      style: NeptunTypography.h3Style.copyWith(
                        color: colors.textPrimary,
                        letterSpacing: 1.0,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Text(
                  'Орієнтовно за останні $timeRangeMinutes хв',
                  style: NeptunTypography.captionStyle.copyWith(
                    color: colors.textSecondary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 20),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: filterableThreatTypes.map((type) {
                    final selected = visibleThreatTypes.contains(type);
                    final label = (ThreatType.names[type] ?? type)
                        .split(' ')
                        .last;
                    return InkWell(
                      onTap: () {
                        onFilterToggled(type, !selected);
                        setDialogState(() {});
                      },
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 200),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 6,
                        ),
                        decoration: BoxDecoration(
                          color: selected
                              ? NeptunStatus.accent.withValues(alpha: 0.2)
                              : colors.panelBorder.withValues(alpha: 0.05),
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(
                            color: selected
                                ? NeptunStatus.accent
                                : colors.panelBorder.withValues(alpha: 0.1),
                          ),
                        ),
                        child: Text(
                          label.toUpperCase(),
                          style: NeptunTypography.microStyle.copyWith(
                            color: selected
                                ? NeptunStatus.accent
                                : colors.textSecondary,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 24),
                Center(
                  child: Column(
                    children: [
                      Text(
                        '$total',
                        style: NeptunTypography.h1Style.copyWith(
                          fontSize: 56,
                          color: colors.textPrimary,
                        ),
                      ),
                      Text(
                        'ЦІЛЕЙ У ПОВІТРІ',
                        style: NeptunTypography.microStyle.copyWith(
                          color: colors.textSecondary,
                          fontWeight: FontWeight.w900,
                          letterSpacing: 2.0,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 24),
                ...visibleCounts.entries.map((entry) {
                  final name = (ThreatType.names[entry.key] ?? entry.key)
                      .split(' ')
                      .last;
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    child: Row(
                      children: [
                        Text(
                          ThreatType.emojis[entry.key] ?? '⚠️',
                          style: const TextStyle(fontSize: 18),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            name.toUpperCase(),
                            style: NeptunTypography.bodyBoldStyle.copyWith(
                              color: colors.textPrimary,
                              letterSpacing: 0.5,
                            ),
                          ),
                        ),
                        Text(
                          '${entry.value}',
                          style: NeptunTypography.h3Style.copyWith(
                            color: colors.textPrimary,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                      ],
                    ),
                  );
                }),
                const SizedBox(height: 32),
                NeptunCard(
                  padding: EdgeInsets.zero,
                  borderRadius: NeptunRadius.md,
                  backgroundColor: colors.textAccent.withValues(alpha: 0.1),
                  borderColor: colors.textAccent.withValues(alpha: 0.2),
                  onTap: () => Navigator.pop(ctx),
                  child: Container(
                    width: double.infinity,
                    height: 48,
                    alignment: Alignment.center,
                    child: Text(
                      'ЗАКРИТИ',
                      style: NeptunTypography.bodyBoldStyle.copyWith(
                        color: colors.textAccent,
                        letterSpacing: 1.0,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    ),
  );
}

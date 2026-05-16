import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../core/widgets/neptun_badge.dart';

/// Bottom sheet showing region alarm details when tapped on the map.
class RegionDetailSheet extends StatelessWidget {
  final String regionName;
  final bool isAlarmActive;
  final DateTime? alarmStartTime;
  final int threatCount;

  const RegionDetailSheet({
    super.key,
    required this.regionName,
    this.isAlarmActive = false,
    this.alarmStartTime,
    this.threatCount = 0,
  });

  static Future<void> show(
    BuildContext context, {
    required String regionName,
    bool isAlarmActive = false,
    DateTime? alarmStartTime,
    int threatCount = 0,
  }) {
    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => RegionDetailSheet(
        regionName: regionName,
        isAlarmActive: isAlarmActive,
        alarmStartTime: alarmStartTime,
        threatCount: threatCount,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Container(
      constraints: BoxConstraints(
        maxHeight: MediaQuery.of(context).size.height * 0.4,
      ),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF0F1320) : Colors.white,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.2),
            blurRadius: 20,
            offset: const Offset(0, -4),
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Handle
          Container(
            margin: const EdgeInsets.only(top: 12),
            width: 36,
            height: 4,
            decoration: BoxDecoration(
              color: cs.onSurface.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Region header
                Row(
                  children: [
                    Container(
                      width: 44,
                      height: 44,
                      decoration: BoxDecoration(
                        color: isAlarmActive
                            ? cs.error.withValues(alpha: 0.15)
                            : cs.secondary.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Icon(
                        isAlarmActive
                            ? Icons.warning_amber_rounded
                            : Icons.check_circle_outline_rounded,
                        color: isAlarmActive ? cs.error : cs.secondary,
                        size: 22,
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            regionName,
                            style: GoogleFonts.inter(
                              fontSize: 17,
                              fontWeight: FontWeight.w600,
                              color: cs.onSurface,
                            ),
                          ),
                          Text(
                            isAlarmActive ? 'Повітряна тривога' : 'Відбій',
                            style: GoogleFonts.inter(
                              fontSize: 13,
                              color: isAlarmActive ? cs.error : cs.secondary,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                    ),
                    NeptunBadge(
                      label: isAlarmActive ? 'ТРИВОГА' : 'БЕЗПЕЧНО',
                      type: isAlarmActive
                          ? NeptunBadgeType.danger
                          : NeptunBadgeType.success,
                      pulse: isAlarmActive,
                    ),
                  ],
                ),

                const SizedBox(height: 20),

                // Stats row
                Row(
                  children: [
                    _StatCard(
                      icon: Icons.crisis_alert_rounded,
                      label: 'Загрози',
                      value: '$threatCount',
                      cs: cs,
                    ),
                    const SizedBox(width: 12),
                    if (alarmStartTime != null)
                      _StatCard(
                        icon: Icons.timer_outlined,
                        label: 'Тривалість',
                        value: _formatDuration(
                          DateTime.now().difference(alarmStartTime!),
                        ),
                        cs: cs,
                      ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  String _formatDuration(Duration d) {
    if (d.inHours > 0) return '${d.inHours}г ${d.inMinutes % 60}хв';
    return '${d.inMinutes}хв';
  }
}

class _StatCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final ColorScheme cs;

  const _StatCard({
    required this.icon,
    required this.label,
    required this.value,
    required this.cs,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: cs.surfaceContainer,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, size: 16, color: cs.primary),
            const SizedBox(height: 8),
            Text(
              value,
              style: GoogleFonts.inter(
                fontSize: 20,
                fontWeight: FontWeight.w700,
                color: cs.onSurface,
              ),
            ),
            Text(
              label,
              style: GoogleFonts.inter(
                fontSize: 12,
                color: cs.onSurface.withValues(alpha: 0.5),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

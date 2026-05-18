import 'package:flutter/material.dart';
import '../../../../core/widgets/status_chip.dart';

class ActiveThreatsSummary extends StatelessWidget {
  final int activeAlarms;
  final int markers;
  final DateTime? updatedAt;

  const ActiveThreatsSummary({
    super.key,
    required this.activeAlarms,
    required this.markers,
    this.updatedAt,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final critical = activeAlarms > 0 || markers > 0;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    critical
                        ? 'Active operational situation'
                        : 'No active threats',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                ),
                StatusChip(
                  label: critical ? '$activeAlarms regions' : 'clear',
                  tone: critical
                      ? StatusChipTone.critical
                      : StatusChipTone.safe,
                  icon: critical
                      ? Icons.warning_amber_rounded
                      : Icons.check_circle_rounded,
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              '$markers tracked objects · ${_freshness()}',
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: cs.onSurfaceVariant),
            ),
          ],
        ),
      ),
    );
  }

  String _freshness() {
    final value = updatedAt;
    if (value == null) return 'waiting for data';
    final minutes = DateTime.now().difference(value).inMinutes;
    return minutes <= 0 ? 'updated now' : 'updated $minutes m ago';
  }
}

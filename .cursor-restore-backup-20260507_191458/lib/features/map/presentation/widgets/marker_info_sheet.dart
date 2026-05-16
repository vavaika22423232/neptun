import 'package:flutter/material.dart';

import '../../../../models/map_models.dart';

/// Shows a bottom sheet with threat marker details. Supports moderator delete.
void showMarkerInfoSheet(
  BuildContext context,
  ThreatMarker marker, {
  required bool isModerator,
  required void Function(ThreatMarker) onDelete,
}) {
  final color = ThreatType.getColor(marker.threatType);
  final threatName = ThreatType.names[marker.threatType] ?? marker.threatType;

  final cs = Theme.of(context).colorScheme;
  showModalBottomSheet(
    context: context,
    backgroundColor: cs.surfaceContainer,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
    ),
    builder: (ctx) {
      final cs = Theme.of(ctx).colorScheme;
      return SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      color: color.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(
                      _getThreatIcon(marker.threatType),
                      color: color,
                      size: 28,
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          threatName,
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                            color: cs.onSurface,
                          ),
                        ),
                        if (marker.date.isNotEmpty)
                          Text(
                            marker.date,
                            style: TextStyle(fontSize: 14, color: cs.outline),
                          ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              if (_isUavType(marker.threatType) &&
                  marker.count != null &&
                  marker.count! > 1) ...[
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.numbers_rounded, color: color, size: 22),
                      const SizedBox(width: 12),
                      Text(
                        'Кількість: ×${marker.count}',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                          color: cs.onSurface,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
              ],
              if (marker.place.isNotEmpty) ...[
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: cs.surfaceContainerHighest,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.location_on_rounded, color: color, size: 22),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          marker.place,
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w500,
                            color: cs.onSurface,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
              ],
              if (isModerator)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: () => onDelete(marker),
                      icon: const Icon(Icons.delete_rounded, size: 20),
                      label: const Text('Видалити мітку'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: cs.error,
                        foregroundColor: cs.onError,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                    ),
                  ),
                ),
              const SizedBox(height: 8),
            ],
          ),
        ),
      );
    },
  );
}

bool _isUavType(String type) {
  final t = type.toLowerCase();
  return t == 'shahed' || t == 'drone' || t == 'uav' || t == 'fpv';
}

IconData _getThreatIcon(String threatType) {
  switch (threatType) {
    case 'air_balloon':
    case 'balloon':
      return Icons.cloud_outlined;
    case 'shahed':
      return Icons.air_rounded;
    case 'raketa':
      return Icons.rocket_launch_rounded;
    case 'avia':
      return Icons.flight_rounded;
    case 'artillery':
    case 'obstril':
      return Icons.gps_fixed_rounded;
    case 'fpv':
      return Icons.sports_esports_rounded;
    case 'kab':
    case 'rszv':
      return Icons.dangerous_rounded;
    case 'rozved':
      return Icons.visibility_rounded;
    default:
      return Icons.warning_rounded;
  }
}

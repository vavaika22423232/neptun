import 'package:flutter/material.dart';

import '../../../../map/threat_bearing.dart';
import '../../../../models/map_models.dart';
import '../../../../design/design_exports.dart';
import '../../../../core/widgets/neptun_shell_modal.dart';
/// Shows a bottom sheet with threat marker details. Supports moderator delete.
void showMarkerInfoSheet(
  BuildContext context,
  ThreatMarker marker, {
  required bool isModerator,
  required void Function(ThreatMarker) onDelete,
  void Function(ThreatMarker)? onHide,
}) {
  final color = ThreatType.getColor(marker.threatType);
  final threatName = ThreatType.names[marker.threatType] ?? marker.threatType;

  NeptunShellModal.showBottomSheet(
    context: context,
    backgroundColor: Colors.transparent,
    isScrollControlled: true,
    builder: (ctx) {
      final courseDeg = resolveThreatBearingDeg(marker);
      return NeptunCard(
        padding: EdgeInsets.all(0),
        borderRadius: 32.0,
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Bento Handle
                Center(
                  child: Container(
                    width: 36,
                    height: 4,
                    decoration: BoxDecoration(
                      color: Theme.of(ctx).colorScheme.onSurface.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),
                const SizedBox(height: 24),
                
                Row(
                  children: [
                    Container(
                      width: 56,
                      height: 56,
                      decoration: BoxDecoration(
                        color: color.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: color.withValues(alpha: 0.2)),
                      ),
                      child: Icon(
                        _getThreatIcon(marker.threatType),
                        color: color,
                        size: 32,
                      ),
                    ),
                    const SizedBox(width: 18),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            threatName.toUpperCase(),
                            style: NeptunTypography.h3Style.copyWith(
                              color: Theme.of(ctx).colorScheme.onSurface,
                              letterSpacing: 0.5,
                            ),
                          ),
                          const SizedBox(height: 4),
                          if (marker.date.isNotEmpty)
                            Text(
                              marker.date,
                              style: NeptunTypography.captionStyle.copyWith(
                                color: Theme.of(ctx).colorScheme.onSurface.withValues(alpha: 0.6),
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                        ],
                      ),
                    ),
                  ],
                ),
                
                if (_placementHint(marker).isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 16),
                    child: Container(
                      width: double.infinity,
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                      decoration: BoxDecoration(
                        color: NeptunStatus.warning.withValues(alpha: 0.08),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: NeptunStatus.warning.withValues(alpha: 0.15)),
                      ),
                      child: Text(
                        _placementHint(marker),
                        style: NeptunTypography.microStyle.copyWith(
                          color: NeptunStatus.warning,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                  ),
                  
                const SizedBox(height: 24),
                
                if (_isUavType(marker.threatType) &&
                    marker.count != null &&
                    marker.count! > 1) ...[
                  _detailRow(
                    context: ctx,
                    icon: Icons.numbers_rounded,
                    label: 'КІЛЬКІСТЬ',
                    value: '×${marker.count}',
                    color: color,
                  ),
                  const SizedBox(height: 12),
                ],
                
                if (marker.place.isNotEmpty) ...[
                  _detailRow(
                    context: ctx,
                    icon: Icons.location_on_rounded,
                    label: 'ЛОКАЦІЯ',
                    value: marker.place,
                    color: color,
                  ),
                  const SizedBox(height: 12),
                ],

                if (courseDeg != null) ...[
                  _detailRow(
                    context: ctx,
                    icon: Icons.navigation_rounded,
                    label: 'КУРС',
                    value: '~${courseDeg.round()}°',
                    color: color,
                  ),
                  const SizedBox(height: 12),
                ],

                if (marker.place.isNotEmpty || courseDeg != null)
                  const SizedBox(height: 12),

                if (isModerator) ...[
                  const Divider(height: 1),
                  const SizedBox(height: 20),
                  if (onHide != null)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: NeptunCard(
                        padding: EdgeInsets.zero,
                        backgroundColor: Theme.of(ctx).colorScheme.onSurface.withValues(alpha: 0.05),
                        borderColor: Theme.of(ctx).colorScheme.onSurface.withValues(alpha: 0.1),
                        onTap: () {
                          Navigator.pop(ctx);
                          onHide(marker);
                        },
                        child: Container(
                          height: 52,
                          alignment: Alignment.center,
                          child: Text(
                            'ПРИХОВАТИ З КАРТИ',
                            style: NeptunTypography.bodyBoldStyle.copyWith(
                              color: Theme.of(ctx).colorScheme.onSurface.withValues(alpha: 0.8),
                              letterSpacing: 1.0,
                            ),
                          ),
                        ),
                      ),
                    ),
                  NeptunCard(
                    padding: EdgeInsets.zero,
                    backgroundColor: NeptunStatus.alarm.withValues(alpha: 0.1),
                    borderColor: NeptunStatus.alarm.withValues(alpha: 0.2),
                    onTap: () {
                      Navigator.pop(ctx);
                      onDelete(marker);
                    },
                    child: Container(
                      height: 52,
                      alignment: Alignment.center,
                      child: Text(
                        'ВИДАЛИТИ МІТКУ',
                        style: NeptunTypography.bodyBoldStyle.copyWith(
                          color: NeptunStatus.alarm,
                          letterSpacing: 1.0,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                ],
                const SizedBox(height: 8),
              ],
            ),
          ),
        ),
      );
    },
  );
}

Widget _detailRow({
  required BuildContext context,
  required IconData icon,
  required String label,
  required String value,
  required Color color,
}) {
  return Container(
    width: double.infinity,
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(
      color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.04),
      borderRadius: BorderRadius.circular(16),
    ),
    child: Row(
      children: [
        Icon(icon, color: color, size: 22),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: NeptunTypography.microStyle.copyWith(
                  color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.4),
                  fontWeight: FontWeight.w800,
                  letterSpacing: 1.2,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                value,
                style: NeptunTypography.bodyBoldStyle.copyWith(
                  color: Theme.of(context).colorScheme.onSurface,
                ),
              ),
            ],
          ),
        ),
      ],
    ),
  );
}

String _placementHint(ThreatMarker marker) {
  final pm = (marker.placementMode ?? '').toLowerCase();
  if (pm == 'approximate') {
    return 'Приблизна позиція (область / центроїд)';
  }
  if (pm == 'predictive') {
    return 'Прогноз траєкторії — може змінитися';
  }
  final c = marker.confidence0_100;
  if (c != null && c < 72) {
    return 'Нижча впевненість у координатах ($c%)';
  }
  return '';
}

bool _isUavType(String type) {
  final t = type.toLowerCase();
  return t == 'shahed' || t == 'drone' || t == 'uav' || t == 'fpv';
}

IconData _getThreatIcon(String threatType) {
  switch (threatType) {
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

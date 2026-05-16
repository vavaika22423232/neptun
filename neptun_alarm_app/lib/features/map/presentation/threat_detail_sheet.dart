import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../../core/widgets/neptun_shell_modal.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../core/widgets/neptun_badge.dart';
import '../../../models/map_models.dart';

/// Bottom sheet showing threat marker details when tapped on the map.
class ThreatDetailSheet extends StatelessWidget {
  final ThreatMarker marker;

  const ThreatDetailSheet({super.key, required this.marker});

  static Future<void> show(BuildContext context, ThreatMarker marker) {
    return NeptunShellModal.showBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => ThreatDetailSheet(marker: marker),
    );
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    final maxH = MediaQuery.sizeOf(context).height * 0.62;
    final bottomInset = MediaQuery.paddingOf(context).bottom;
    /// Ручка + відступ: без цього [SingleChildScrollView] з’їдав би зайву висоту й ламав би flex.
    const handleReserve = 12.0 + 4.0 + 8.0;
    final scrollMax = math.max(160.0, maxH - handleReserve);

    return Container(
      constraints: BoxConstraints(maxHeight: maxH),
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
          Container(
            margin: const EdgeInsets.only(top: 12),
            width: 36,
            height: 4,
            decoration: BoxDecoration(
              color: cs.onSurface.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          ConstrainedBox(
            constraints: BoxConstraints(maxHeight: scrollMax),
            child: SingleChildScrollView(
              padding: EdgeInsets.fromLTRB(20, 16, 20, 20 + bottomInset),
              physics: const BouncingScrollPhysics(),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        width: 44,
                        height: 44,
                        decoration: BoxDecoration(
                          color: cs.error.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Icon(
                          _threatIcon(marker.threatType),
                          color: cs.error,
                          size: 22,
                        ),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              _threatLabel(marker.threatType),
                              style: GoogleFonts.plusJakartaSans(
                                fontSize: 17,
                                fontWeight: FontWeight.w600,
                                color: cs.onSurface,
                              ),
                            ),
                            if (marker.place.isNotEmpty)
                              Text(
                                marker.place,
                                style: GoogleFonts.plusJakartaSans(
                                  fontSize: 13,
                                  color: cs.onSurface.withValues(alpha: 0.5),
                                ),
                              ),
                          ],
                        ),
                      ),
                      NeptunBadge.danger(label: 'АКТИВНО', pulse: true),
                    ],
                  ),
                  if (marker.text.isNotEmpty) ...[
                    const SizedBox(height: 16),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: cs.surfaceContainer,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        marker.text,
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 14,
                          color: cs.onSurface.withValues(alpha: 0.7),
                          height: 1.5,
                        ),
                      ),
                    ),
                  ],
                  if (_isUavType(marker.threatType) &&
                      marker.count != null &&
                      marker.count! > 1) ...[
                    const SizedBox(height: 12),
                    _InfoRow(
                      icon: Icons.numbers_rounded,
                      label: 'Кількість',
                      value: '×${marker.count}',
                      cs: cs,
                    ),
                  ],
                  if (marker.trajectory != null) ...[
                    const SizedBox(height: 16),
                    _InfoRow(
                      icon: Icons.navigation_rounded,
                      label: 'Напрямок',
                      value: marker.trajectory!.targetName.isEmpty
                          ? 'Невідомо'
                          : marker.trajectory!.targetName,
                      cs: cs,
                    ),
                  ],
                  const SizedBox(height: 12),
                  _InfoRow(
                    icon: Icons.gps_fixed_rounded,
                    label: 'Координати',
                    value:
                        '${marker.lat.toStringAsFixed(4)}, ${marker.lng.toStringAsFixed(4)}',
                    cs: cs,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  IconData _threatIcon(String type) {
    switch (type.toLowerCase()) {
      case 'shahed':
      case 'drone':
        return Icons.flight_rounded;
      case 'raketa':
      case 'missile':
        return Icons.rocket_launch_rounded;
      case 'ballistic':
        return Icons.warning_rounded;
      case 'avia':
        return Icons.airplanemode_active_rounded;
      case 'kab':
        return Icons.gps_fixed_rounded;
      default:
        return Icons.crisis_alert_rounded;
    }
  }

  bool _isUavType(String type) {
    final t = type.toLowerCase();
    return t == 'shahed' || t == 'drone' || t == 'uav' || t == 'fpv';
  }

  String _threatLabel(String type) {
    switch (type.toLowerCase()) {
      case 'shahed':
      case 'drone':
        return 'Ударний БПЛА';
      case 'raketa':
      case 'missile':
        return 'Крилата ракета';
      case 'ballistic':
        return 'Балістична загроза';
      case 'avia':
        return 'Тактична авіація';
      case 'kab':
        return 'Керована авіабомба';
      default:
        return type;
    }
  }
}

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final ColorScheme cs;

  const _InfoRow({
    required this.icon,
    required this.label,
    required this.value,
    required this.cs,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 16, color: cs.onSurface.withValues(alpha: 0.4)),
        const SizedBox(width: 8),
        Text(
          '$label: ',
          style: GoogleFonts.plusJakartaSans(
            fontSize: 13,
            color: cs.onSurface.withValues(alpha: 0.4),
          ),
        ),
        Expanded(
          child: Text(
            value,
            style: GoogleFonts.plusJakartaSans(
              fontSize: 13,
              fontWeight: FontWeight.w500,
              color: cs.onSurface.withValues(alpha: 0.7),
            ),
          ),
        ),
      ],
    );
  }
}

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../map/presentation/threat_detail_sheet.dart';
import '../../../../models/map_models.dart';
import '../../domain/threat_event.dart';
import '../radar_tokens.dart';

class ThreatEventCard extends StatelessWidget {
  const ThreatEventCard({super.key, required this.event});

  final ThreatEvent event;

  Color _severityColor() => switch (event.severity) {
        ThreatSeverity.critical => RadarTokens.danger,
        ThreatSeverity.high => RadarTokens.warning,
        ThreatSeverity.medium => RadarTokens.accentStrong,
        ThreatSeverity.low => RadarTokens.textMuted,
      };

  IconData _icon() {
    switch (event.categoryKey.toLowerCase()) {
      case 'shahed':
      case 'drone':
        return LucideIcons.radio;
      case 'raketa':
      case 'missile':
        return LucideIcons.triangleAlert;
      case 'avia':
        return LucideIcons.plane;
      default:
        return LucideIcons.circleAlert;
    }
  }

  void _open(BuildContext context) {
    HapticFeedback.lightImpact();
    final raw = Map<String, dynamic>.from(event.primaryRaw);
    if (raw['threat_type'] == null && raw['threatType'] != null) {
      raw['threat_type'] = raw['threatType'];
    }
    ThreatDetailSheet.show(context, ThreatMarker.fromJson(raw));
  }

  @override
  Widget build(BuildContext context) {
    final sev = _severityColor();
    return RepaintBoundary(
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () => _open(context),
          borderRadius: BorderRadius.circular(RadarTokens.cardRadius),
          child: Ink(
            decoration: BoxDecoration(
              color: RadarTokens.card.withValues(alpha: 0.95),
              borderRadius: BorderRadius.circular(RadarTokens.cardRadius),
              border: Border.all(color: RadarTokens.border),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.18),
                  blurRadius: 16,
                  offset: const Offset(0, 6),
                ),
              ],
            ),
            padding: const EdgeInsets.all(RadarTokens.cardPad),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(
                    color: sev.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Icon(_icon(), color: sev, size: 22),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              event.title,
                              style: GoogleFonts.plusJakartaSans(
                                fontSize: 17,
                                fontWeight: FontWeight.w700,
                                color: RadarTokens.textPrimary,
                              ),
                            ),
                          ),
                          if (event.isNew)
                            _Badge(label: 'NEW', color: RadarTokens.live),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        event.locationLine,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                          color: RadarTokens.textSecondary,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Text(
                            event.updatedLabel,
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: 12,
                              color: RadarTokens.textMuted,
                            ),
                          ),
                          const SizedBox(width: 8),
                          _Badge(
                            label: '${event.signalCount} сигнали',
                            color: RadarTokens.accentStrong,
                          ),
                          if (event.confidencePercent != null) ...[
                            const SizedBox(width: 6),
                            _Badge(
                              label: '${event.confidencePercent}%',
                              color: RadarTokens.textMuted,
                            ),
                          ],
                        ],
                      ),
                    ],
                  ),
                ),
                Icon(Icons.chevron_right_rounded, color: RadarTokens.textMuted),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _Badge extends StatelessWidget {
  const _Badge({required this.label, required this.color});
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(RadarTokens.chipRadius),
      ),
      child: Text(
        label,
        style: GoogleFonts.plusJakartaSans(
          fontSize: 11,
          fontWeight: FontWeight.w700,
          color: color,
        ),
      ),
    );
  }
}

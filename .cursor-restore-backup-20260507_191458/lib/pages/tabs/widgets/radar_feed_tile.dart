import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../design/neptun_design.dart';
import '../../../features/map/presentation/threat_detail_sheet.dart';
import '../../../models/map_models.dart';
import 'radar_feed_logic.dart';

class RadarFeedTile extends StatelessWidget {
  const RadarFeedTile({super.key, required this.entry});

  final RadarFeedEntry entry;

  IconData _iconForType(String type) {
    switch (type.toLowerCase()) {
      case 'missile':
      case 'raketa':
        return LucideIcons.triangleAlert;
      case 'drone':
      case 'shahed':
        return LucideIcons.radio;
      case 'aircraft':
      case 'avia':
        return LucideIcons.plane;
      default:
        return LucideIcons.circleAlert;
    }
  }

  void _openDetail(BuildContext context) {
    HapticFeedback.lightImpact();
    final normalized = Map<String, dynamic>.from(entry.raw);
    if (normalized['threat_type'] == null && normalized['threatType'] != null) {
      normalized['threat_type'] = normalized['threatType'];
    }
    if (normalized['place'] == null && normalized['location'] != null) {
      normalized['place'] = normalized['location'];
    }
    ThreatDetailSheet.show(context, ThreatMarker.fromJson(normalized));
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final iconColor = NeptunStatus.alarm.withValues(alpha: 0.95);

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () => _openDetail(context),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 4),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(_iconForType(entry.typeKey), size: 20, color: iconColor),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      entry.place,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                        color: cs.onSurface,
                        height: 1.25,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      entry.typeLabel,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                        color: cs.onSurface.withValues(alpha: 0.55),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Text(
                entry.displayTime,
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: cs.onSurface.withValues(alpha: 0.45),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

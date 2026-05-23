import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../../core/utils/open_neptun_telegram.dart';
import '../radar_tokens.dart';

class RadarEmptyState extends StatelessWidget {
  const RadarEmptyState({
    super.key,
    this.lastUpdated,
    this.onOpenMap,
  });

  final DateTime? lastUpdated;
  final VoidCallback? onOpenMap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 48),
      child: Column(
        children: [
          Container(
            width: 72,
            height: 72,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: RadarTokens.live.withValues(alpha: 0.12),
            ),
            child: const Icon(
              LucideIcons.shieldCheck,
              size: 36,
              color: RadarTokens.live,
            ),
          ),
          const SizedBox(height: 20),
          Text(
            'Активних загроз наразі немає',
            textAlign: TextAlign.center,
            style: GoogleFonts.plusJakartaSans(
              fontSize: 18,
              fontWeight: FontWeight.w700,
              color: RadarTokens.textPrimary,
            ),
          ),
          if (lastUpdated != null) ...[
            const SizedBox(height: 8),
            Text(
              'Останнє оновлення: ${_rel(lastUpdated!)}',
              style: GoogleFonts.plusJakartaSans(
                fontSize: 13,
                color: RadarTokens.textMuted,
              ),
            ),
          ],
          const SizedBox(height: 24),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            alignment: WrapAlignment.center,
            children: [
              FilledButton.icon(
                onPressed: () => openNeptunTelegramChannel('radar_empty'),
                icon: const Icon(Icons.telegram, size: 18),
                label: const Text('Telegram'),
                style: FilledButton.styleFrom(
                  backgroundColor: RadarTokens.accentStrong.withValues(alpha: 0.2),
                  foregroundColor: RadarTokens.accent,
                ),
              ),
              if (onOpenMap != null)
                OutlinedButton.icon(
                  onPressed: onOpenMap,
                  icon: const Icon(Icons.map_outlined, size: 18),
                  label: const Text('Карта'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: RadarTokens.textSecondary,
                    side: const BorderSide(color: RadarTokens.border),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }

  String _rel(DateTime t) {
    final d = DateTime.now().difference(t);
    if (d.inMinutes < 60) return '${d.inMinutes} хв тому';
    return '${d.inHours} год тому';
  }
}

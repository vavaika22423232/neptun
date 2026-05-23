import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../../core/utils/open_neptun_telegram.dart';
import '../radar_tokens.dart';

/// Premium glass Telegram CTA — dismissible, compact after dismiss.
class TelegramChannelCard extends StatelessWidget {
  const TelegramChannelCard({
    super.key,
    required this.compact,
    required this.onDismiss,
  });

  final bool compact;
  final VoidCallback onDismiss;

  @override
  Widget build(BuildContext context) {
    if (compact) {
      return Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () => openNeptunTelegramChannel('radar_compact'),
          borderRadius: BorderRadius.circular(14),
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: Row(
              children: [
                Icon(Icons.telegram, size: 18, color: RadarTokens.accentStrong),
                const SizedBox(width: 8),
                Text(
                  'Telegram — найшвидші оновлення',
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: RadarTokens.textSecondary,
                  ),
                ),
                const Spacer(),
                Icon(Icons.chevron_right, size: 18, color: RadarTokens.textMuted),
              ],
            ),
          ),
        ),
      );
    }

    return ClipRRect(
      borderRadius: BorderRadius.circular(RadarTokens.cardRadius),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
        child: Container(
          decoration: BoxDecoration(
            color: RadarTokens.card.withValues(alpha: 0.92),
            borderRadius: BorderRadius.circular(RadarTokens.cardRadius),
            border: Border.all(color: RadarTokens.border),
          ),
          child: Stack(
            children: [
              Padding(
                padding: const EdgeInsets.all(RadarTokens.cardPad),
                child: Row(
                  children: [
                    Container(
                      width: 44,
                      height: 44,
                      decoration: BoxDecoration(
                        color: RadarTokens.accentStrong.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(14),
                      ),
                      child: const Icon(
                        Icons.telegram,
                        color: RadarTokens.accentStrong,
                        size: 24,
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Офіційний Telegram канал',
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: 16,
                              fontWeight: FontWeight.w700,
                              color: RadarTokens.textPrimary,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            'Найшвидші оновлення',
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: 13,
                              color: RadarTokens.textSecondary,
                            ),
                          ),
                        ],
                      ),
                    ),
                    IconButton(
                      onPressed: () => openNeptunTelegramChannel('radar_card'),
                      icon: const Icon(Icons.arrow_forward_rounded),
                      color: RadarTokens.accent,
                    ),
                  ],
                ),
              ),
              Positioned(
                top: 4,
                right: 4,
                child: IconButton(
                  visualDensity: VisualDensity.compact,
                  onPressed: onDismiss,
                  icon: Icon(
                    Icons.close_rounded,
                    size: 20,
                    color: RadarTokens.textMuted.withValues(alpha: 0.8),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

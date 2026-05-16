import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../utils/open_neptun_telegram.dart';

/// Компактний рядок як на сайті (`TelegramBanner` з `isCompact`) — той самий копірайт і CTA.
class TelegramRadarPromoCard extends StatefulWidget {
  const TelegramRadarPromoCard({
    super.key,
    required this.onDismiss,
  });

  final VoidCallback onDismiss;

  @override
  State<TelegramRadarPromoCard> createState() => _TelegramRadarPromoCardState();
}

class _TelegramRadarPromoCardState extends State<TelegramRadarPromoCard> {
  static const Color _accent = Color(0xFF3A9EFD);
  static const Color _accentDarkFill = Color(0xFF2A8AE0);

  Future<void> _open() => openNeptunTelegramChannel('radar_banner');

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final borderTop = cs.outline.withValues(alpha: isDark ? 0.08 : 0.12);

    return Material(
      color: Colors.transparent,
      child: DecoratedBox(
        decoration: BoxDecoration(
          border: Border(top: BorderSide(color: borderTop)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Expanded(
              child: InkWell(
                onTap: _open,
                borderRadius: BorderRadius.circular(8),
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(12, 10, 8, 10),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      _StaticAccentDot(accent: _accent),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text.rich(
                          TextSpan(
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: 10,
                              height: 1.25,
                            ),
                            children: [
                              TextSpan(
                                text: 'Щоб не перевіряти сайт ',
                                style: TextStyle(
                                  fontWeight: FontWeight.w500,
                                  color: isDark
                                      ? _accent.withValues(alpha: 0.85)
                                      : cs.onSurface.withValues(alpha: 0.55),
                                ),
                              ),
                              TextSpan(
                                text: 'ХЛОПЦІ ПИШУТЬ В TELEGRAM',
                                style: TextStyle(
                                  fontWeight: FontWeight.w800,
                                  letterSpacing: 0.6,
                                  color: cs.onSurface,
                                ),
                              ),
                              TextSpan(
                                text: ' — максимально швидко',
                                style: TextStyle(
                                  fontWeight: FontWeight.w500,
                                  color: cs.onSurface.withValues(alpha: 0.5),
                                ),
                              ),
                            ],
                          ),
                          maxLines: 3,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      const SizedBox(width: 8),
                      _SubscribePill(
                        isDark: isDark,
                        accent: _accent,
                        accentDarkFill: _accentDarkFill,
                      ),
                    ],
                  ),
                ),
              ),
            ),
            IconButton(
              visualDensity: VisualDensity.compact,
              onPressed: widget.onDismiss,
              icon: Icon(
                Icons.close_rounded,
                size: 20,
                color: cs.onSurface.withValues(alpha: 0.4),
              ),
              tooltip: 'Приховати',
            ),
          ],
        ),
      ),
    );
  }
}

class _StaticAccentDot extends StatelessWidget {
  const _StaticAccentDot({required this.accent});

  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 8,
      height: 8,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: accent,
        boxShadow: [
          BoxShadow(
            color: accent.withValues(alpha: 0.5),
            blurRadius: 4,
            spreadRadius: 0,
          ),
        ],
      ),
    );
  }
}

/// Візуально як кнопка на сайті; тап обробляє батьківський `InkWell`.
class _SubscribePill extends StatelessWidget {
  const _SubscribePill({
    required this.isDark,
    required this.accent,
    required this.accentDarkFill,
  });

  final bool isDark;
  final Color accent;
  final Color accentDarkFill;

  @override
  Widget build(BuildContext context) {
    final border = isDark
        ? accent.withValues(alpha: 0.5)
        : accentDarkFill.withValues(alpha: 0.85);
    final bg = isDark
        ? accent.withValues(alpha: 0.2)
        : accentDarkFill.withValues(alpha: 0.95);
    final fg = isDark ? const Color(0xFFE1F0FF) : Colors.white;

    return IgnorePointer(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: border, width: 1),
          color: bg,
          boxShadow: [
            BoxShadow(
              color: (isDark ? accent : accentDarkFill).withValues(alpha: 0.22),
              blurRadius: 8,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.telegram, size: 13, color: fg),
            const SizedBox(width: 4),
            Text(
              'Підписатись!',
              style: GoogleFonts.plusJakartaSans(
                fontSize: 9,
                fontWeight: FontWeight.w800,
                letterSpacing: 0.8,
                color: fg,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

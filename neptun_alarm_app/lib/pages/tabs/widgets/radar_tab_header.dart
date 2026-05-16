import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Компактна шапка: заголовок, підзаголовок і badge з кількістю активних тривог.
class RadarTabHeader extends StatelessWidget {
  const RadarTabHeader({
    super.key,
    required this.activeAlarms,
  });

  final int activeAlarms;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Expanded(
              child: Text(
                'Радар загроз',
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                  color: cs.onSurface,
                  height: 1.2,
                ),
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(999),
                color: cs.surfaceContainerHighest,
                border: Border.all(
                  color: cs.error.withValues(alpha: 0.35),
                  width: 1,
                ),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.notifications_active_outlined,
                    size: 16,
                    color: cs.error,
                  ),
                  const SizedBox(width: 6),
                  Text(
                    '$activeAlarms',
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 15,
                      fontWeight: FontWeight.w800,
                      color: cs.onSurface,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        Text(
          'Оновлення повітряних загроз — одна стрічка',
          style: GoogleFonts.plusJakartaSans(
            fontSize: 13,
            color: cs.onSurface.withValues(alpha: 0.55),
            height: 1.35,
          ),
        ),
      ],
    );
  }
}

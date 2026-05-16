import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../design/design_exports.dart';

/// Шапка вкладки «Регіони»: заголовок, пояснення та лічильник обраних позицій.
class RegionsTabHeader extends StatelessWidget {
  const RegionsTabHeader({
    super.key,
    required this.selectedOblastCount,
    required this.totalSelections,
  });

  final int selectedOblastCount;
  final int totalSelections;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    String subtitle;
    if (totalSelections == 0) {
      subtitle =
          'Оберіть область або окремі райони — push-сповіщення надходять під час тривог у цих зонах.';
    } else if (selectedOblastCount > 0) {
      subtitle =
          'Обрано областей: $selectedOblastCount · усього позицій у списку: $totalSelections';
    } else {
      subtitle =
          'Обрано лише райони ($totalSelections) — сповіщення йдуть за вибраними районами.';
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Text(
                'Регіони сповіщень',
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                  color: cs.onSurface,
                  height: 1.2,
                ),
              ),
            ),
            const SizedBox(width: NeptunSpacing.sm),
            StatusPill(
              label: '$totalSelections',
              variant: totalSelections > 0
                  ? StatusPillVariant.safe
                  : StatusPillVariant.neutral,
              icon: Icons.notifications_active_rounded,
            ),
          ],
        ),
        const SizedBox(height: NeptunSpacing.sm),
        Text(
          subtitle,
          style: GoogleFonts.plusJakartaSans(
            fontSize: 13,
            color: cs.onSurface.withValues(alpha: 0.55),
            height: 1.4,
          ),
        ),
      ],
    );
  }
}

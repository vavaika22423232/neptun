import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../neptun_design.dart';

/// Strong section header with optional leading icon and trailing action.
/// Creates clear visual hierarchy between sections.
class SectionHeader extends StatelessWidget {
  final String title;
  final IconData? icon;
  final Widget? trailing;
  final EdgeInsetsGeometry? padding;

  const SectionHeader({
    super.key,
    required this.title,
    this.icon,
    this.trailing,
    this.padding,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Padding(
      padding: padding ??
          const EdgeInsets.fromLTRB(
            NeptunSpacing.lg,
            NeptunSpacing.xl,
            NeptunSpacing.lg,
            NeptunSpacing.sm,
          ),
      child: Row(
        children: [
          if (icon != null) ...[
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: cs.primary.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(NeptunRadius.sm),
              ),
              child: Icon(icon, size: 18, color: cs.primary),
            ),
            const SizedBox(width: NeptunSpacing.md),
          ],
          Expanded(
            child: Text(
              title.toUpperCase(),
              style: GoogleFonts.plusJakartaSans(
                fontSize: NeptunTypography.micro,
                fontWeight: FontWeight.w700,
                letterSpacing: 1.4,
                color: isDark
                    ? cs.onSurface.withValues(alpha: 0.5)
                    : cs.onSurface.withValues(alpha: 0.6),
              ),
            ),
          ),
          ?trailing,
        ],
      ),
    );
  }
}

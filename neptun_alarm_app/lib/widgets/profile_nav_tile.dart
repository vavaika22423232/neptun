import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import '../core/widgets/neptun_badge.dart';
import '../design/neptun_design.dart';

/// Unified tile for Profile tab and Settings: icon, label, subtitle, optional trailing (Switch/chevron).
/// [iconAccent] enables the React-style colored 48×48 icon plate.
class ProfileNavTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final String? subtitle;
  final String? badge;
  final Widget? trailing;
  final VoidCallback? onTap;
  /// When set, icon sits in a rounded square with tinted fill/border (NEPTUN Premium Modern).
  final Color? iconAccent;
  /// Hairline separator below this row (groups inside one card).
  final bool showDividerBelow;

  const ProfileNavTile({
    super.key,
    required this.icon,
    required this.label,
    this.subtitle,
    this.badge,
    this.trailing,
    this.onTap,
    this.iconAccent,
    this.showDividerBelow = false,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final accent = iconAccent;
    final usePlate = accent != null;

    final iconWidget = usePlate
        ? Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(18),
              color: accent.withValues(alpha: 0.09),
              border: Border.all(
                color: accent.withValues(alpha: 0.19),
                width: 1,
              ),
            ),
            alignment: Alignment.center,
            child: Icon(icon, size: 22, color: accent),
          )
        : Icon(icon, size: 22, color: cs.primary);

    final titleStyle = GoogleFonts.plusJakartaSans(
      fontSize: usePlate ? 15 : 14,
      fontWeight: usePlate ? FontWeight.w600 : FontWeight.w500,
      color: cs.onSurface,
    );

    final subtitleStyle = GoogleFonts.plusJakartaSans(
      fontSize: 12,
      height: 1.35,
      color: usePlate
          ? NeptunStatus.muted
          : cs.onSurface.withValues(alpha: 0.4),
    );

    final row = Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap != null
            ? () {
                HapticFeedback.selectionClick();
                onTap!();
              }
            : null,
        borderRadius: BorderRadius.circular(NeptunRadius.md),
        child: Padding(
          padding: NeptunSpacing.listTilePadding,
          child: Row(
            children: [
              iconWidget,
              const SizedBox(width: NeptunSpacing.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(label, style: titleStyle),
                    if (subtitle != null) ...[
                      const SizedBox(height: NeptunSpacing.xs),
                      Text(subtitle!, style: subtitleStyle),
                    ],
                  ],
                ),
              ),
              if (badge != null) ...[
                const SizedBox(width: 8),
                NeptunBadge.pro(label: badge!),
              ],
              if (trailing != null) ...[
                const SizedBox(width: 8),
                trailing!,
              ] else if (onTap != null)
                Icon(
                  Icons.chevron_right_rounded,
                  size: 20,
                  color: cs.onSurface.withValues(alpha: 0.25),
                )
              else
                const SizedBox(width: 4),
            ],
          ),
        ),
      ),
    );

    if (!showDividerBelow) return row;

    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        row,
        Divider(
          height: 1,
          thickness: 1,
          indent: 20,
          endIndent: 20,
          color: isDark
              ? Colors.white.withValues(alpha: 0.05)
              : cs.outline.withValues(alpha: 0.12),
        ),
      ],
    );
  }
}

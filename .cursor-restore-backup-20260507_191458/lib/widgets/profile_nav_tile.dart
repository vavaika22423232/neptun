import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import '../core/widgets/neptun_badge.dart';

/// Unified tile for Profile tab and Settings: icon, label, subtitle, optional trailing (Switch/chevron).
/// Matches _NavTile visual style: flat, no cards, InkWell with borderRadius 14.
class ProfileNavTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final String? subtitle;
  final String? badge;
  final Widget? trailing;
  final VoidCallback? onTap;
  /// Якщо задано — колір іконки замість [ColorScheme.primary].
  final Color? iconAccent;
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

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap != null
            ? () {
                HapticFeedback.selectionClick();
                onTap!();
              }
            : null,
        borderRadius: BorderRadius.circular(14),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              child: Row(
                children: [
                  Icon(icon, size: 22, color: iconAccent ?? cs.primary),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          label,
                          style: GoogleFonts.plusJakartaSans(
                            fontSize: 14,
                            fontWeight: FontWeight.w500,
                            color: cs.onSurface,
                          ),
                        ),
                        if (subtitle != null)
                          Text(
                            subtitle!,
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: 12,
                              color: cs.onSurface.withValues(alpha: 0.4),
                            ),
                          ),
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
            if (showDividerBelow)
              Divider(
                height: 1,
                thickness: 0.5,
                color: cs.outlineVariant.withValues(alpha: 0.35),
              ),
          ],
        ),
      ),
    );
  }
}

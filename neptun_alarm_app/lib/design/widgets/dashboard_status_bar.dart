import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../neptun_design.dart';
import 'status_pill.dart';
import 'tactical_surface.dart';

/// Hero status bar for dashboard — primary information at a glance.
/// Shows alarm count, status, and optional quick action.
class DashboardStatusBar extends StatelessWidget {
  final bool hasAlarms;
  final int alarmCount;
  final String? subtitle;
  final VoidCallback? onTap;
  final Widget? trailing;

  const DashboardStatusBar({
    super.key,
    required this.hasAlarms,
    this.alarmCount = 0,
    this.subtitle,
    this.onTap,
    this.trailing,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final accentColor = hasAlarms ? cs.error : cs.secondary;
    final icon = hasAlarms ? Icons.warning_amber_rounded : Icons.shield_rounded;

    return TacticalSurface(
      style: hasAlarms ? TacticalSurfaceStyle.glow : TacticalSurfaceStyle.raised,
      accentGlow: hasAlarms ? accentColor : null,
      onTap: onTap,
      padding: const EdgeInsets.all(NeptunSpacing.lg),
      child: Row(
        children: [
          Container(
            width: 52,
            height: 52,
            decoration: BoxDecoration(
              color: accentColor.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(NeptunRadius.md),
              border: Border.all(
                color: accentColor.withValues(alpha: 0.35),
                width: 0.5,
              ),
            ),
            child: Icon(icon, color: accentColor, size: 26),
          ),
          const SizedBox(width: NeptunSpacing.lg),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  hasAlarms ? 'Тривога: $alarmCount рег.' : 'Все спокійно',
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: NeptunTypography.h2,
                    fontWeight: FontWeight.w700,
                    color: cs.onSurface,
                  ),
                ),
                if (subtitle != null) ...[
                  const SizedBox(height: NeptunSpacing.xs),
                  Text(
                    subtitle!,
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: NeptunTypography.caption,
                      color: cs.onSurface.withValues(alpha: 0.55),
                    ),
                  ),
                ],
              ],
            ),
          ),
          if (trailing != null)
            trailing!
          else
            StatusPill(
              label: hasAlarms ? 'ТРИВОГА' : 'БЕЗПЕЧНО',
              variant: hasAlarms ? StatusPillVariant.alarm : StatusPillVariant.safe,
              pulse: hasAlarms,
            ),
        ],
      ),
    );
  }
}

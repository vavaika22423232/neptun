import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../neptun_design.dart';

/// Compact status indicator pill for tactical dashboard.
/// Use for: safe/alarm/offline, threat counts, live status.
enum StatusPillVariant { safe, alarm, warning, neutral, accent }

class StatusPill extends StatelessWidget {
  final String label;
  final StatusPillVariant variant;
  final bool pulse;
  final IconData? icon;

  const StatusPill({
    super.key,
    required this.label,
    this.variant = StatusPillVariant.neutral,
    this.pulse = false,
    this.icon,
  });

  Color _color(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    switch (variant) {
      case StatusPillVariant.safe:
        return cs.secondary;
      case StatusPillVariant.alarm:
        return cs.error;
      case StatusPillVariant.warning:
        return cs.tertiary;
      case StatusPillVariant.accent:
        return cs.primary;
      case StatusPillVariant.neutral:
        return cs.onSurface.withValues(alpha: 0.5);
    }
  }

  @override
  Widget build(BuildContext context) {
    final color = _color(context);

    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      padding: const EdgeInsets.symmetric(
        horizontal: NeptunSpacing.md,
        vertical: NeptunSpacing.xs + 2,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(NeptunRadius.pill),
        border: Border.all(color: color.withValues(alpha: 0.4), width: 0.5),
        boxShadow: pulse
            ? [
                BoxShadow(
                  color: color.withValues(alpha: 0.35),
                  blurRadius: 6,
                  spreadRadius: 0,
                ),
              ]
            : null,
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (pulse || icon != null)
            Padding(
              padding: const EdgeInsets.only(right: NeptunSpacing.xs),
              child: icon != null
                  ? Icon(icon, size: 12, color: color)
                  : Container(
                      width: 6,
                      height: 6,
                      decoration: BoxDecoration(
                        color: color,
                        shape: BoxShape.circle,
                        boxShadow: pulse
                            ? [
                                BoxShadow(
                                  color: color.withValues(alpha: 0.6),
                                  blurRadius: 4,
                                ),
                              ]
                            : null,
                      ),
                    ),
            ),
          Text(
            label,
            style: GoogleFonts.plusJakartaSans(
              fontSize: NeptunTypography.micro,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.5,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}

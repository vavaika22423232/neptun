import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import '../neptun_design.dart';

/// Compact action tile for quick actions grid (e.g. dashboard shortcuts).
/// Icon + label, no subtitle — dense and scannable.
class ActionTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;
  final Color? iconColor;

  const ActionTile({
    super.key,
    required this.icon,
    required this.label,
    required this.onTap,
    this.iconColor,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final color = iconColor ?? cs.primary;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () {
          HapticFeedback.selectionClick();
          onTap();
        },
        borderRadius: BorderRadius.circular(NeptunRadius.md),
        child: Container(
          padding: const EdgeInsets.symmetric(
            vertical: NeptunSpacing.lg,
            horizontal: NeptunSpacing.md,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(NeptunRadius.sm),
                ),
                child: Icon(icon, color: color, size: 22),
              ),
              const SizedBox(height: NeptunSpacing.sm),
              Text(
                label,
                style: GoogleFonts.plusJakartaSans(
                  fontSize: NeptunTypography.caption,
                  fontWeight: FontWeight.w600,
                  color: cs.onSurface,
                ),
                textAlign: TextAlign.center,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

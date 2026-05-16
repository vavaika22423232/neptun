import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../config/app_constants.dart';
import '../neptun_design.dart';

/// Simple bottom navigation bar with minimal styling.
class TacticalNavBar extends StatelessWidget {
  final int selectedIndex;
  final ValueChanged<int> onTap;
  final List<TacticalNavDestination> destinations;

  /// `true` — floating capsule; otherwise full-width bar.
  final bool floating;

  /// For docked bar: bottom system inset (home indicator).
  final double bottomViewInset;

  const TacticalNavBar({
    super.key,
    required this.selectedIndex,
    required this.onTap,
    required this.destinations,
    this.floating = false,
    this.bottomViewInset = 0,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    final row = Row(
      mainAxisAlignment: MainAxisAlignment.spaceAround,
      children: List.generate(destinations.length, (i) {
        final d = destinations[i];
        final selected = selectedIndex == i;
        return _NavItem(
          icon: selected ? d.selectedIcon : d.icon,
          label: d.label,
          selected: selected,
          onTap: () {
            HapticFeedback.selectionClick();
            onTap(i);
          },
        );
      }),
    );

    final scaffoldBg = Theme.of(context).scaffoldBackgroundColor;

    if (!floating) {
      return Container(
        padding: EdgeInsets.fromLTRB(
          NeptunSpacing.lg,
          NeptunSpacing.md,
          NeptunSpacing.lg,
          NeptunSpacing.lg + bottomViewInset,
        ),
        decoration: BoxDecoration(
          color: scaffoldBg,
          border: Border(
            top: BorderSide(
              color: cs.outline.withValues(alpha: 0.2),
              width: 0.5,
            ),
          ),
        ),
        child: row,
      );
    }

    return Container(
      margin: EdgeInsets.fromLTRB(
        NeptunSpacing.lg,
        NeptunSpacing.sm,
        NeptunSpacing.lg,
        NeptunSpacing.md + bottomViewInset,
      ),
      decoration: BoxDecoration(
        color: scaffoldBg,
        borderRadius: BorderRadius.circular(32),
        border: Border.all(color: cs.outline, width: 1),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: NeptunSpacing.md,
          vertical: NeptunSpacing.sm + 2,
        ),
        child: row,
      ),
    );
  }
}

class TacticalNavDestination {
  final IconData icon;
  final IconData selectedIcon;
  final String label;

  const TacticalNavDestination({
    required this.icon,
    required this.selectedIcon,
    required this.label,
  });
}

class _NavItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _NavItem({
    required this.icon,
    required this.label,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    final textColor = selected
        ? cs.primary
        : (isDark
              ? cs.onSurface.withValues(alpha: 0.5)
              : cs.onSurface.withValues(alpha: 0.45));

    return Expanded(
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(12),
          child: AnimatedContainer(
            duration: AppConstants.bottomNavSelectionDuration,
            curve: Curves.easeOutCubic,
            padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
            decoration: BoxDecoration(
              color: selected
                  ? cs.primary.withValues(alpha: 0.08)
                  : Colors.transparent,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(icon, size: 24, color: textColor),
                const SizedBox(height: 4),
                AnimatedDefaultTextStyle(
                  duration: AppConstants.bottomNavSelectionDuration,
                  curve: Curves.easeOutCubic,
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 11,
                    fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
                    color: textColor,
                  ),
                  child: Text(
                    label,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    textAlign: TextAlign.center,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

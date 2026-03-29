import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import '../neptun_design.dart';

/// Premium bottom navigation with pill-style selection indicator.
/// Tactical, compact, information-dense.
class TacticalNavBar extends StatelessWidget {
  final int selectedIndex;
  final ValueChanged<int> onTap;
  final List<TacticalNavDestination> destinations;

  const TacticalNavBar({
    super.key,
    required this.selectedIndex,
    required this.onTap,
    required this.destinations,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Container(
      padding: const EdgeInsets.fromLTRB(NeptunSpacing.lg, NeptunSpacing.sm, NeptunSpacing.lg, NeptunSpacing.lg),
      decoration: BoxDecoration(
        color: isDark ? NeptunSurfaces.s1 : cs.surface,
        border: Border(
          top: BorderSide(
            color: isDark ? NeptunSurfaces.border : cs.outline.withValues(alpha: 0.2),
            width: 0.5,
          ),
        ),
      ),
      child: SafeArea(
        top: false,
        child: Row(
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
        ),
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

    return Expanded(
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(NeptunRadius.md),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            padding: const EdgeInsets.symmetric(vertical: NeptunSpacing.sm, horizontal: NeptunSpacing.xs),
            decoration: BoxDecoration(
              color: selected ? cs.primary.withValues(alpha: 0.12) : Colors.transparent,
              borderRadius: BorderRadius.circular(NeptunRadius.md),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                AnimatedScale(
                  scale: selected ? 1.08 : 1.0,
                  duration: MediaQuery.disableAnimationsOf(context)
                      ? Duration.zero
                      : const Duration(milliseconds: 240),
                  curve: Curves.easeOutCubic,
                  child: Icon(
                    icon,
                    size: 24,
                    color: selected ? cs.primary : cs.onSurface.withValues(alpha: 0.5),
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  label,
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 11,
                    fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                    color: selected ? cs.primary : cs.onSurface.withValues(alpha: 0.55),
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

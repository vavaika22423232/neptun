import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

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
      padding: const EdgeInsets.fromLTRB(14, 4, 14, 4),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF070B15) : cs.surface,
        border: Border(
          top: BorderSide(
            color: isDark
                ? const Color(0xFF0D1420)
                : cs.outline.withValues(alpha: 0.16),
            width: 1,
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
          borderRadius: BorderRadius.circular(18),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            height: 56,
            margin: const EdgeInsets.symmetric(horizontal: 2),
            padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 4),
            decoration: BoxDecoration(
              color: selected ? const Color(0xFF1D2332) : Colors.transparent,
              borderRadius: BorderRadius.circular(18),
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
                    color: selected
                        ? const Color(0xFFF1F4FA)
                        : cs.onSurface.withValues(alpha: 0.48),
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  label,
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 11,
                    fontWeight: selected ? FontWeight.w800 : FontWeight.w700,
                    color: selected
                        ? const Color(0xFFF1F4FA)
                        : cs.onSurface.withValues(alpha: 0.52),
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

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import '../neptun_design.dart';
import 'tactical_surface.dart';

/// Region/oblast selection tile — not a generic list tile.
/// Expandable with district chips, clear selected state.
class RegionTile extends StatelessWidget {
  final String name;
  final String? emoji;
  final bool isSelected;
  final bool isExpanded;
  final List<String>? districts;
  final Set<String> selectedDistricts;
  final VoidCallback onOblastTap;
  final void Function(String district) onDistrictTap;
  final VoidCallback? onExpandTap;

  const RegionTile({
    super.key,
    required this.name,
    this.emoji,
    required this.isSelected,
    required this.isExpanded,
    this.districts,
    this.selectedDistricts = const {},
    required this.onOblastTap,
    required this.onDistrictTap,
    this.onExpandTap,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final hasDistricts = districts != null && districts!.isNotEmpty;

    return TacticalSurface(
      style: isSelected
          ? TacticalSurfaceStyle.raised
          : TacticalSurfaceStyle.flat,
      margin: EdgeInsets.zero,
      padding: EdgeInsets.zero,
      onTap: null,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: () {
          HapticFeedback.selectionClick();
          onOblastTap();
        },
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.all(NeptunSpacing.lg),
              child: Row(
                children: [
                  if (emoji != null)
                    Padding(
                      padding: const EdgeInsets.only(right: NeptunSpacing.sm),
                      child: Text(emoji!, style: const TextStyle(fontSize: 18)),
                    ),
                  Expanded(
                    child: Text(
                      name,
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: NeptunTypography.h3,
                        fontWeight: FontWeight.w600,
                        color: cs.onSurface,
                      ),
                    ),
                  ),
                  Container(
                    width: 24,
                    height: 24,
                    decoration: BoxDecoration(
                      color: isSelected
                          ? cs.primary.withValues(alpha: 0.2)
                          : cs.onSurface.withValues(alpha: 0.08),
                      shape: BoxShape.circle,
                      border: isSelected
                          ? Border.all(color: cs.primary, width: 1.5)
                          : null,
                    ),
                    child: isSelected
                        ? Icon(Icons.check_rounded, size: 14, color: cs.primary)
                        : null,
                  ),
                  if (hasDistricts)
                    GestureDetector(
                      onTap: onExpandTap != null
                          ? () {
                              HapticFeedback.selectionClick();
                              onExpandTap!();
                            }
                          : null,
                      child: Padding(
                        padding: const EdgeInsets.all(NeptunSpacing.xs),
                        child: Icon(
                          isExpanded
                              ? Icons.expand_less_rounded
                              : Icons.expand_more_rounded,
                          color: cs.onSurface.withValues(alpha: 0.5),
                          size: 22,
                        ),
                      ),
                    ),
                ],
              ),
            ),
            if (isExpanded && hasDistricts) ...[
              Divider(
                height: 1,
                color: isDark
                    ? NeptunSurfaces.border
                    : cs.outline.withValues(alpha: 0.2),
                indent: NeptunSpacing.lg,
                endIndent: NeptunSpacing.lg,
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(
                  NeptunSpacing.lg,
                  NeptunSpacing.sm,
                  NeptunSpacing.lg,
                  NeptunSpacing.lg,
                ),
                child: Wrap(
                  spacing: NeptunSpacing.sm,
                  runSpacing: NeptunSpacing.sm,
                  children: districts!
                      .map(
                        (d) => _DistrictChip(
                          label: d,
                          selected: selectedDistricts.contains(d),
                          onTap: () {
                            HapticFeedback.selectionClick();
                            onDistrictTap(d);
                          },
                        ),
                      )
                      .toList(),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _DistrictChip extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _DistrictChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(
          horizontal: NeptunSpacing.md,
          vertical: NeptunSpacing.xs + 2,
        ),
        decoration: BoxDecoration(
          color: selected
              ? cs.primary.withValues(alpha: 0.18)
              : cs.onSurface.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(NeptunRadius.pill),
          border: Border.all(
            color: selected
                ? cs.primary.withValues(alpha: 0.5)
                : Colors.transparent,
            width: 0.5,
          ),
        ),
        child: Text(
          label,
          style: GoogleFonts.plusJakartaSans(
            fontSize: NeptunTypography.caption,
            fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
            color: selected ? cs.primary : cs.onSurface.withValues(alpha: 0.8),
          ),
        ),
      ),
    );
  }
}

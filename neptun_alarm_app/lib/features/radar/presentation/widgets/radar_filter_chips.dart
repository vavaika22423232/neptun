import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../domain/radar_quick_filter.dart';
import '../radar_tokens.dart';

class RadarFilterChips extends StatelessWidget {
  const RadarFilterChips({
    super.key,
    required this.selected,
    required this.onChanged,
    this.showMyRegions = true,
  });

  final RadarQuickFilter selected;
  final ValueChanged<RadarQuickFilter> onChanged;
  final bool showMyRegions;

  static const List<RadarQuickFilter> _order = [
    RadarQuickFilter.all,
    RadarQuickFilter.shahedLayer,
    RadarQuickFilter.missiles,
    RadarQuickFilter.aviation,
    RadarQuickFilter.airRaid,
    RadarQuickFilter.ppo,
    RadarQuickFilter.myRegions,
    RadarQuickFilter.highPriority,
    RadarQuickFilter.blasts,
  ];

  @override
  Widget build(BuildContext context) {
    final chips = showMyRegions
        ? _order
        : _order.where((f) => f != RadarQuickFilter.myRegions).toList();

    return SizedBox(
      height: 38,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: chips.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (context, i) {
          final f = chips[i];
          final on = selected == f;
          return FilterChip(
            label: Text(f.shortLabelUk),
            selected: on,
            showCheckmark: false,
            onSelected: (_) {
              HapticFeedback.selectionClick();
              onChanged(f);
            },
            labelStyle: GoogleFonts.plusJakartaSans(
              fontSize: 13,
              fontWeight: on ? FontWeight.w700 : FontWeight.w600,
              color: on ? RadarTokens.bg : RadarTokens.textSecondary,
            ),
            selectedColor: RadarTokens.accent,
            backgroundColor: RadarTokens.card.withValues(alpha: 0.7),
            side: BorderSide(color: RadarTokens.border),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(RadarTokens.chipRadius),
            ),
            padding: const EdgeInsets.symmetric(horizontal: 4),
            materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
            visualDensity: VisualDensity.compact,
          );
        },
      ),
    );
  }
}

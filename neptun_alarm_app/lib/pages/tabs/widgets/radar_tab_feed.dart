import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/widgets/neptun_empty_state.dart';
import '../../../core/widgets/neptun_error_state.dart';
import '../../../core/widgets/neptun_shimmer.dart';
import '../../../features/radar/domain/radar_quick_filter.dart';

import 'radar_feed_logic.dart';
import 'radar_feed_tile.dart';

/// Sliver-и для стрічки Радару: завантаження, помилка, порожній стан або список подій.
List<Widget> buildRadarFeedSlivers({
  required bool isLoading,
  required String? error,
  required Future<void> Function() onRetry,
  required List<Map<String, dynamic>> markers,
  required double horizontalPadding,
  RadarQuickFilter quickFilter = RadarQuickFilter.all,
}) {
  if (isLoading) {
    return [_buildLoadingSliver(horizontalPadding)];
  }
  if (error != null) {
    final friendly = _radarFriendlyError(error);
    return [
      SliverPadding(
        padding: EdgeInsets.fromLTRB(
          horizontalPadding,
          24,
          horizontalPadding,
          24,
        ),
        sliver: SliverToBoxAdapter(
          child: NeptunErrorBanner(
            message: friendly.short,
            detail: friendly.detail,
            onRetry: onRetry,
          ),
        ),
      ),
    ];
  }

  final sorted = buildSortedRadarFeedEntries(markers, filter: quickFilter);
  if (sorted.isEmpty) {
    if (markers.isNotEmpty && quickFilter != RadarQuickFilter.all) {
      return [
        SliverPadding(
          padding: EdgeInsets.fromLTRB(
            horizontalPadding,
            32,
            horizontalPadding,
            32,
          ),
          sliver: SliverToBoxAdapter(
            child: NeptunEmptyState(
              icon: Icons.filter_alt_outlined,
              title: 'Нічого під цей фільтр',
              subtitle:
                  'Спробуйте іншу категорію або перегляньте розширений радар.',
            ),
          ),
        ),
      ];
    }

    return [
      SliverPadding(
        padding: EdgeInsets.fromLTRB(
          horizontalPadding,
          32,
          horizontalPadding,
          32,
        ),
        sliver: const SliverToBoxAdapter(
          child: NeptunEmptyState(
            icon: LucideIcons.shieldCheck,
            title: 'Активних загроз немає',
            subtitle: 'Наразі ситуація спокійна',
          ),
        ),
      ),
    ];
  }

  final items = buildRadarFeedListItems(sorted);
  return [
    SliverPadding(
      padding: EdgeInsets.fromLTRB(horizontalPadding, 8, horizontalPadding, 0),
      sliver: SliverList(
        delegate: SliverChildBuilderDelegate(
          (context, index) {
            final item = items[index];
            switch (item) {
              case RadarSectionTitleItem(:final title):
                final isFirst = index == 0;
                return Padding(
                  padding: EdgeInsets.only(
                    top: isFirst ? 4 : 20,
                    bottom: 8,
                  ),
                  child: Text(
                    title,
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.4,
                      color: Theme.of(context)
                          .colorScheme
                          .onSurface
                          .withValues(alpha: 0.5),
                    ),
                  ),
                );
              case RadarFeedRowItem(:final entry):
                final prev = index > 0 ? items[index - 1] : null;
                final showTopDivider = prev is RadarFeedRowItem;
                return Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (showTopDivider)
                      Divider(
                        height: 1,
                        thickness: 1,
                        color: Theme.of(context)
                            .colorScheme
                            .outline
                            .withValues(alpha: 0.12),
                      ),
                    RadarFeedTile(entry: entry),
                  ],
                );
            }
          },
          childCount: items.length,
        ),
      ),
    ),
  ];
}

({String short, String? detail}) _radarFriendlyError(String raw) {
  const short =
      'Не вдалося оновити дані. Перевірте з\'єднання та спробуйте ще раз.';
  final detail = kDebugMode ? raw.trim() : null;
  return (short: short, detail: detail);
}

Widget _buildLoadingSliver(double horizontalPadding) {
  return SliverPadding(
    padding: EdgeInsets.fromLTRB(horizontalPadding, 16, horizontalPadding, 0),
    sliver: SliverList(
      delegate: SliverChildBuilderDelegate(
        (context, index) => Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: NeptunShimmer(
            width: double.infinity,
            height: 52,
            borderRadius: 12,
          ),
        ),
        childCount: 8,
      ),
    ),
  );
}

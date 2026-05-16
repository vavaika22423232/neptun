import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../../core/di/service_locator.dart';
import '../../../../pages/tabs/widgets/radar_feed_logic.dart';
import '../../../../design/design_exports.dart';
import '../../../../services/data_stream_service.dart';
import '../../../map/domain/map_realtime_link_status.dart';
import '../../domain/radar_quick_filter.dart';

/// Зведення статусів, живий канал SSE і швидкі фільтри стрічки Радару.
class RadarOverviewStrip extends StatelessWidget {
  const RadarOverviewStrip({
    super.key,
    required this.markers,
    required this.activeOblastsUnderAlarm,
    required this.quickFilter,
    required this.onQuickFilterChanged,
    required this.historyMinutes,
    this.lastFetchedAt,
  });

  final List<Map<String, dynamic>> markers;
  final int activeOblastsUnderAlarm;
  final RadarQuickFilter quickFilter;
  final ValueChanged<RadarQuickFilter> onQuickFilterChanged;
  final int historyMinutes;
  final DateTime? lastFetchedAt;

  static const List<RadarQuickFilter> _chipsOrder = [
    RadarQuickFilter.all,
    RadarQuickFilter.shahedLayer,
    RadarQuickFilter.missiles,
    RadarQuickFilter.aviation,
    RadarQuickFilter.airRaid,
    RadarQuickFilter.blasts,
  ];

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isLight = Theme.of(context).brightness == Brightness.light;
    final places = _topPlaces(markers);
    final filteredCount = markers
        .where((m) => quickFilter.matchesMarker(m))
        .length;
    final hasMissileBuzz = markers.any(_isMissileRelated);

    final surface = isLight
        ? NeptunLightSurfaces.elevated
        : NeptunSurfaces.s1;
    final borderCol = cs.outline.withValues(alpha: 0.14);

    return NeptunBentoSurface(
      margin: EdgeInsets.zero,
      padding: const EdgeInsets.fromLTRB(
        NeptunSpacing.lg,
        NeptunSpacing.md,
        NeptunSpacing.lg,
        NeptunSpacing.md,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Що зараз по небу',
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 17,
                        fontWeight: FontWeight.w700,
                        height: 1.25,
                        color: cs.onSurface,
                      ),
                    ),
                    const SizedBox(height: NeptunSpacing.xs),
                    Text(
                      '$filteredCount з ${markers.length} подій показані у фіді (~$historyMinutes хв)'
                      '${quickFilter != RadarQuickFilter.all ? ' • фільтр увімкнено' : ''}',
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 13,
                        height: 1.45,
                        color: cs.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: NeptunSpacing.sm),
              ListenableBuilder(
                listenable: sl<DataStreamService>().mapRealtimeLink,
                builder: (context, _) {
                  final st = sl<DataStreamService>().mapRealtimeLink.value;
                  return _LinkPhasePill(phase: st.phase);
                },
              ),
            ],
          ),
          const SizedBox(height: NeptunSpacing.sm),
          _MetricsRow(
            activeOblasts: activeOblastsUnderAlarm,
            places: places,
            surfaceBg: surface,
            borderCol: borderCol,
          ),
          if (hasMissileBuzz) ...[
            const SizedBox(height: NeptunSpacing.sm),
            _CalmCue(
              icon: LucideIcons.rocket,
              text:
                  'Є активність ракетної/ високошвидкісної групи загроз у цьому вікні. Тримайте канал відкритим.',
            ),
          ],
          const SizedBox(height: NeptunSpacing.md),
          SizedBox(
            height: 40,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: _chipsOrder.length,
              separatorBuilder: (context, _) =>
                  const SizedBox(width: NeptunSpacing.xs),
              itemBuilder: (context, index) {
                final f = _chipsOrder[index];
                final selected = quickFilter == f;
                return FilterChip(
                  label: Text(
                    f.shortLabelUk,
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 13,
                      fontWeight: selected ? FontWeight.w700 : FontWeight.w600,
                      color: selected ? cs.primary : cs.onSurface,
                    ),
                  ),
                  selected: selected,
                  showCheckmark: false,
                  onSelected: (_) {
                    HapticFeedback.selectionClick();
                    onQuickFilterChanged(f);
                  },
                  selectedColor:
                      cs.primaryContainer.withValues(alpha: 0.55),
                  backgroundColor: cs.surface.withValues(alpha: 0.5),
                  side: BorderSide(color: borderCol),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(NeptunRadius.md),
                  ),
                  padding:
                      const EdgeInsets.symmetric(horizontal: NeptunSpacing.sm),
                  materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  visualDensity: VisualDensity.compact,
                );
              },
            ),
          ),
          if (lastFetchedAt != null) ...[
            const SizedBox(height: NeptunSpacing.sm),
            Text(
              'Дані API: ${_formatFetchedRelative(lastFetchedAt!)}',
              style: GoogleFonts.plusJakartaSans(
                fontSize: 12,
                color: cs.onSurfaceVariant.withValues(alpha: 0.85),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _MetricsRow extends StatelessWidget {
  const _MetricsRow({
    required this.activeOblasts,
    required this.places,
    required this.surfaceBg,
    required this.borderCol,
  });

  final int activeOblasts;
  final List<String> places;
  final Color surfaceBg;
  final Color borderCol;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final placeLine = places.isEmpty
        ? 'Назви локацій зʼявляться після першої події'
        : places.join(' · ');
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(NeptunSpacing.md),
      decoration: BoxDecoration(
        color: surfaceBg.withValues(alpha: 0.75),
        borderRadius: BorderRadius.circular(NeptunRadius.md),
        border: Border.all(color: borderCol),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                LucideIcons.bellDot,
                size: 17,
                color: cs.error.withValues(alpha: 0.85),
              ),
              const SizedBox(width: NeptunSpacing.sm),
              Expanded(
                child: Text(
                  'Областей з активною тривогою зараз — $activeOblasts',
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: cs.onSurface,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: NeptunSpacing.sm),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(
                LucideIcons.mapPin,
                size: 17,
                color: cs.onSurfaceVariant,
              ),
              const SizedBox(width: NeptunSpacing.sm),
              Expanded(
                child: Text(
                  placeLine,
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 13,
                    height: 1.35,
                    color: cs.onSurfaceVariant,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _CalmCue extends StatelessWidget {
  const _CalmCue({
    required this.icon,
    required this.text,
  });

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(NeptunSpacing.md),
      decoration: BoxDecoration(
        color: cs.error.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(NeptunRadius.md),
        border: Border.all(
          color: NeptunStatus.warning.withValues(alpha: 0.35),
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 18, color: NeptunStatus.warning),
          const SizedBox(width: NeptunSpacing.sm),
          Expanded(
            child: Text(
              text,
              style: GoogleFonts.plusJakartaSans(
                fontSize: 13,
                height: 1.38,
                color: cs.onSurface,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _LinkPhasePill extends StatelessWidget {
  const _LinkPhasePill({required this.phase});

  final MapRealtimeLinkPhase phase;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final (label, color) = switch (phase) {
      MapRealtimeLinkPhase.idle => ('Очікуємо канал', cs.onSurfaceVariant),
      MapRealtimeLinkPhase.connecting => ('Зʼєднання…', NeptunStatus.warning),
      MapRealtimeLinkPhase.live => ('На звʼязку', const Color(0xFF059669)),
      MapRealtimeLinkPhase.reconnecting =>
        ('Повторне підключення', NeptunStatus.warning),
    };
    return Container(
      constraints: const BoxConstraints(maxWidth: 132),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(NeptunRadius.pill),
        border: Border.all(color: cs.outline.withValues(alpha: 0.18)),
        color: cs.surfaceContainerHighest.withValues(alpha: 0.45),
      ),
      child: Text(
        label,
        textAlign: TextAlign.center,
        style: GoogleFonts.plusJakartaSans(
          fontSize: 11,
          fontWeight: FontWeight.w700,
          height: 1.2,
          color: color,
        ),
      ),
    );
  }
}

List<String> _topPlaces(List<Map<String, dynamic>> markers, {int max = 4}) {
  final sorted = List<Map<String, dynamic>>.from(markers);
  sorted.sort((a, b) {
    final ta = radarMarkerTimestamp(a);
    final tb = radarMarkerTimestamp(b);
    if (ta == null && tb == null) return 0;
    if (ta == null) return 1;
    if (tb == null) return -1;
    return tb.compareTo(ta);
  });
  final out = <String>[];
  for (final m in sorted) {
    final p = (m['place'] ?? m['location'] ?? '').toString().trim();
    if (p.isEmpty || p == 'Невідомий регіон') continue;
    if (out.contains(p)) continue;
    out.add(p);
    if (out.length >= max) break;
  }
  return out;
}

bool _isMissileRelated(Map<String, dynamic> m) =>
    RadarQuickFilter.missiles.matchesMarker(m);

String _formatFetchedRelative(DateTime t) {
  final now = DateTime.now();
  final diff = now.difference(t);
  if (diff.inSeconds < 45) return 'щойно';
  if (diff.inMinutes < 60) return '${diff.inMinutes} хв тому';
  if (diff.inHours < 12) return '${diff.inHours} год тому';
  return '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';
}

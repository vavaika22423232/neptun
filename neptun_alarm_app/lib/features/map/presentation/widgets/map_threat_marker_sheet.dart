import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:share_plus/share_plus.dart';

import '../../../../core/router/route_paths.dart';
import '../../../../core/widgets/neptun_shell_modal.dart';
import '../../../../design/design_exports.dart';
import '../../../../models/map_models.dart';

/// Нативний bottom sheet для маркера з WebView (Phase A bridge).
Future<void> showMapThreatMarkerSheet(
  BuildContext context,
  Map<String, dynamic> raw,
) {
  return NeptunShellModal.showBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (ctx) {
      return Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.viewPaddingOf(ctx).bottom + NeptunSpacing.md,
          left: NeptunSpacing.screenHorizontal,
          right: NeptunSpacing.screenHorizontal,
        ),
        child: _ThreatMarkerSheetBody(raw: raw),
      );
    },
  );
}

class _ThreatMarkerSheetBody extends StatelessWidget {
  const _ThreatMarkerSheetBody({required this.raw});

  final Map<String, dynamic> raw;

  ThreatMarker get _m {
    try {
      return ThreatMarker.fromJson(Map<String, dynamic>.from(raw));
    } catch (_) {
      return ThreatMarker(
        lat: double.tryParse(raw['lat']?.toString() ?? '') ?? 0,
        lng: double.tryParse(raw['lng']?.toString() ?? '') ?? 0,
        threatType: raw['threat_type']?.toString() ?? 'default',
        place: raw['place']?.toString() ?? '',
        text: raw['text']?.toString() ?? '',
        date: raw['date']?.toString() ?? '',
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final m = _m;
    final typeLabel = ThreatType.names[m.threatType] ?? m.threatType;
    final status = _ThreatSheetStatus.resolve(raw, m);
    final hint = raw['display_trust_hint_uk']?.toString().trim() ?? '';
    final motionReason = raw['motion_reason']?.toString().trim() ?? '';

    String? bearingLine;
    final cb = m.courseBearing;
    if (cb != null && cb.isFinite) {
      final dir = (m.courseDirection ?? m.arrowDirection ?? '').trim();
      bearingLine =
          dir.isNotEmpty ? 'Курс ~${cb.round()}° · $dir' : 'Курс ~${cb.round()}°';
    }

    String? trajSeg;
    if (m.trajectory != null) {
      final t = m.trajectory!;
      if (t.sourceName.isNotEmpty || t.targetName.isNotEmpty) {
        final seg = '${t.sourceName} → ${t.targetName}'.trim();
        if (seg != '→') trajSeg = seg;
      }
    }
    final regionBlock = [
      if (m.place.isNotEmpty) m.place,
      ?trajSeg,
    ].join('\n');

    var confidenceLine = '';
    if (m.confidence0_100 != null) {
      confidenceLine = 'Впевненість: ${m.confidence0_100}%';
      if (m.placementMode != null && m.placementMode!.isNotEmpty) {
        confidenceLine += ' · ${m.placementMode}';
      }
    } else if (m.placementMode != null && m.placementMode!.isNotEmpty) {
      confidenceLine = m.placementMode!;
    }

    final shareText = _buildShareText(typeLabel, m);

    return DecoratedBox(
      decoration: NeptunFloatingChrome.panelDecoration(
        isDark: isDark,
        colorScheme: cs,
        borderRadius: 28,
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          NeptunSpacing.lg,
          NeptunSpacing.md,
          NeptunSpacing.lg,
          NeptunSpacing.lg,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Center(
              child: Container(
                width: 36,
                height: 4,
                margin: const EdgeInsets.only(bottom: NeptunSpacing.md),
                decoration: BoxDecoration(
                  color: cs.onSurface.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(999),
                ),
              ),
            ),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  ThreatType.icons[m.threatType] ?? Icons.place_rounded,
                  color: ThreatType.getColor(m.threatType).withValues(
                    alpha: isDark ? 0.95 : 0.85,
                  ),
                  size: 26,
                ),
                const SizedBox(width: NeptunSpacing.sm),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        typeLabel,
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: NeptunTypography.title + 2,
                          fontWeight: FontWeight.w700,
                          height: 1.2,
                          color: cs.onSurface,
                        ),
                      ),
                      const SizedBox(height: NeptunSpacing.xs),
                      _StatusBadge(
                        label: status.label,
                        color: status.accent,
                      ),
                    ],
                  ),
                ),
              ],
            ),
            if (regionBlock.isNotEmpty) ...[
              const SizedBox(height: NeptunSpacing.md),
              Text(
                regionBlock,
                style: GoogleFonts.plusJakartaSans(
                  fontSize: NeptunTypography.body,
                  fontWeight: FontWeight.w600,
                  height: 1.35,
                  color: cs.onSurface.withValues(alpha: 0.78),
                ),
              ),
            ],
            if (m.date.isNotEmpty) ...[
              const SizedBox(height: NeptunSpacing.sm),
              Text(
                'Час: ${m.date}',
                style: GoogleFonts.plusJakartaSans(
                  fontSize: NeptunTypography.caption + 1,
                  fontWeight: FontWeight.w500,
                  color: cs.onSurface.withValues(alpha: 0.52),
                ),
              ),
            ],
            if (bearingLine != null) ...[
              const SizedBox(height: NeptunSpacing.sm),
              Text(
                bearingLine,
                style: GoogleFonts.plusJakartaSans(
                  fontSize: NeptunTypography.caption + 1,
                  fontWeight: FontWeight.w600,
                  color: cs.onSurface.withValues(alpha: 0.6),
                ),
              ),
            ],
            if (confidenceLine.isNotEmpty) ...[
              const SizedBox(height: NeptunSpacing.sm),
              Text(
                confidenceLine,
                style: GoogleFonts.plusJakartaSans(
                  fontSize: NeptunTypography.caption + 1,
                  fontWeight: FontWeight.w500,
                  color: cs.onSurface.withValues(alpha: 0.55),
                ),
              ),
            ],
            if (hint.isNotEmpty) ...[
              const SizedBox(height: NeptunSpacing.sm),
              Text(
                hint,
                style: GoogleFonts.plusJakartaSans(
                  fontSize: NeptunTypography.caption,
                  height: 1.35,
                  color: cs.onSurface.withValues(alpha: 0.48),
                ),
              ),
            ],
            if (motionReason.isNotEmpty) ...[
              const SizedBox(height: NeptunSpacing.sm),
              Text(
                motionReason,
                style: GoogleFonts.plusJakartaSans(
                  fontSize: NeptunTypography.micro,
                  height: 1.35,
                  color: cs.onSurface.withValues(alpha: 0.45),
                ),
              ),
            ],
            const SizedBox(height: NeptunSpacing.md),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () {
                      HapticFeedback.selectionClick();
                      Navigator.of(context).pop();
                      context.push(RoutePaths.radarFull);
                    },
                    icon: const Icon(Icons.open_in_full_rounded, size: 18),
                    label: const Text('Радар'),
                  ),
                ),
                const SizedBox(width: NeptunSpacing.sm),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () {
                      HapticFeedback.selectionClick();
                      Navigator.of(context).pop();
                      context.go(RoutePaths.radarRegionsView);
                    },
                    icon:
                        const Icon(Icons.notifications_active_outlined, size: 18),
                    label: const Text('Сповіщення'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: NeptunSpacing.sm),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: () async {
                  HapticFeedback.mediumImpact();
                  await Share.share(shareText);
                },
                icon: const Icon(Icons.ios_share_rounded, size: 18),
                label: const Text('Поділитись'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  static String _buildShareText(String typeLabel, ThreatMarker m) {
    final b = StringBuffer(typeLabel);
    if (m.place.isNotEmpty) {
      b.writeln();
      b.write(m.place);
    }
    if (m.date.isNotEmpty) {
      b.writeln();
      b.write(m.date);
    }
    b.writeln();
    b.writeln('NEPTUN — https://neptun.in.ua');
    return b.toString();
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: NeptunSpacing.sm,
        vertical: NeptunSpacing.xs + 1,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(NeptunSpacing.sm),
        border: Border.all(color: color.withValues(alpha: 0.35)),
      ),
      child: Text(
        label,
        style: GoogleFonts.plusJakartaSans(
          fontSize: NeptunTypography.micro + 1,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.2,
          color: cs.onSurface.withValues(alpha: 0.92),
        ),
      ),
    );
  }
}

class _ThreatSheetStatus {
  const _ThreatSheetStatus._(this.label, this.accent);

  final String label;
  final Color accent;

  static _ThreatSheetStatus resolve(Map<String, dynamic> raw, ThreatMarker m) {
    final state = raw['track_state']?.toString().toLowerCase();

    final epochMs = (raw['last_update_epoch'] as num?)?.toInt();
    final staleByAge = epochMs != null &&
        DateTime.now().difference(
              DateTime.fromMillisecondsSinceEpoch(epochMs),
            ) >
            const Duration(minutes: 30);

    if (state == 'stale' || state == 'lost' || staleByAge) {
      return const _ThreatSheetStatus._(
          'Застаріле уточнення', Color(0xFF78716C));
    }
    if (state == 'extrapolated') {
      return const _ThreatSheetStatus._(
          'Оновлено (оцінка руху)', Color(0xFF0F766E));
    }
    if (state == 'observed') {
      return const _ThreatSheetStatus._('Спостерігається', Color(0xFF0F766E));
    }

    if (_modeLooksApproximate(m)) {
      return const _ThreatSheetStatus._('Приблизно на карті', Color(0xFFB45309));
    }

    return const _ThreatSheetStatus._('Активне позначення', Color(0xFF00668a));
  }
}

bool _modeLooksApproximate(ThreatMarker m) {
  final pm = (m.placementMode ?? '').toLowerCase();
  return pm.contains('approx') ||
      pm.contains('predict') ||
      pm.contains('region');
}

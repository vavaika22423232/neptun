import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../../core/router/route_paths.dart';
import '../../../../core/di/service_locator.dart';
import '../../../../core/providers/api_reachability_provider.dart';
import '../../../../design/design_exports.dart';
import '../../../../pages/app_shell.dart';
import '../../../../services/data_stream_service.dart';
import '../../domain/map_realtime_link_status.dart';

/// Компактний map-first блок: статус ситуації, живий канал, відносний час оновлення.
///
/// Спокійна «SaaS» панель поверх карти (без градієнтів / неону).
class MapSituationStatusStrip extends StatelessWidget {
  const MapSituationStatusStrip({super.key});

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: sl<DataStreamService>().mapRealtimeLink,
      builder: (context, _) {
        final link = sl<DataStreamService>().mapRealtimeLink.value;
        return Consumer(
          builder: (ctx, ref, _) {
            final onlineAsync = ref.watch(effectiveOnlineProvider);
            final online = onlineAsync.value ?? EffectiveOnlineState.online;
            return _MapSituationStatusBody(
              link: link,
              online: online,
            );
          },
        );
      },
    );
  }
}

class _MapSituationStatusBody extends StatelessWidget {
  const _MapSituationStatusBody({
    required this.link,
    required this.online,
  });

  final MapRealtimeLinkStatus link;
  final EffectiveOnlineState online;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final top = MediaQuery.paddingOf(context).top +
        AppShellState.chromeHeight +
        AppShellState.contentTopGap;
    final h = NeptunSpacing.screenHorizontal;

            final subtitle = _buildSubtitle();
    final dotColor = _dotColor(cs);
    final subtitleColor =
        cs.onSurface.withValues(alpha: isDark ? 0.68 : 0.58);

    return Padding(
      padding: EdgeInsets.fromLTRB(h, top, h, NeptunSpacing.sm),
      child: Material(
        color: Colors.transparent,
        child: DecoratedBox(
          decoration: NeptunFloatingChrome.panelDecoration(
            isDark: isDark,
            colorScheme: cs,
            borderRadius: NeptunFloatingChrome.radiusShell,
          ),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(
              NeptunSpacing.md,
              NeptunSpacing.sm,
              NeptunSpacing.xs,
              NeptunSpacing.sm,
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        'Ситуація зараз',
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: NeptunTypography.micro,
                          fontWeight: FontWeight.w600,
                          letterSpacing: 0.35,
                          color: cs.onSurface.withValues(alpha: 0.45),
                        ),
                      ),
                      const SizedBox(height: NeptunSpacing.xs),
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Padding(
                            padding: const EdgeInsets.only(top: 5),
                            child: AnimatedContainer(
                              duration: const Duration(milliseconds: 280),
                              width: NeptunSpacing.sm + 2,
                              height: NeptunSpacing.sm + 2,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                color: dotColor,
                                boxShadow: link.phase == MapRealtimeLinkPhase.live &&
                                        online == EffectiveOnlineState.online
                                    ? [
                                        BoxShadow(
                                          blurRadius: 6,
                                          spreadRadius: 0,
                                          color: dotColor.withValues(alpha: 0.35),
                                        ),
                                      ]
                                    : null,
                              ),
                            ),
                          ),
                          const SizedBox(width: NeptunSpacing.sm),
                          Expanded(
                            child: Text(
                              subtitle,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: GoogleFonts.plusJakartaSans(
                                fontSize: NeptunTypography.caption + 1,
                                fontWeight: FontWeight.w600,
                                height: 1.3,
                                color: subtitleColor,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                IconButton(
                  tooltip: 'Радар та фільтри',
                  constraints: const BoxConstraints(minWidth: 40, minHeight: 40),
                  padding: EdgeInsets.zero,
                  onPressed: () {
                    HapticFeedback.selectionClick();
                    context.push(RoutePaths.radarFull);
                  },
                  icon: Icon(
                    Icons.tune_rounded,
                    color: cs.onSurface.withValues(alpha: isDark ? 0.82 : 0.72),
                    size: 22,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Color _dotColor(ColorScheme cs) {
    if (online != EffectiveOnlineState.online) {
      return cs.outline.withValues(alpha: 0.55);
    }
    switch (link.phase) {
      case MapRealtimeLinkPhase.idle:
      case MapRealtimeLinkPhase.connecting:
        return cs.primary.withValues(alpha: 0.85);
      case MapRealtimeLinkPhase.reconnecting:
        return cs.tertiary;
      case MapRealtimeLinkPhase.live:
        return cs.primary;
    }
  }

  String _buildSubtitle() {
    switch (online) {
      case EffectiveOnlineState.noNetwork:
        return 'Без звʼязку — показуємо останнє доступне на карті';
      case EffectiveOnlineState.apiUnreachable:
        return 'Сервер недоступний — оновлення з карти можуть затримуватись';
      case EffectiveOnlineState.online:
        break;
    }

    switch (link.phase) {
      case MapRealtimeLinkPhase.idle:
        return 'Готуємо зʼєднання з живими даними';
      case MapRealtimeLinkPhase.connecting:
        return 'Підключення до каналу оновлень…';
      case MapRealtimeLinkPhase.reconnecting:
        return 'Відновлюємо канал даних…';
      case MapRealtimeLinkPhase.live:
        final t = link.lastSignificantRefreshAt;
        if (t == null) {
          return 'Канал активний — чекаємо на зміни з сервера';
        }
        return 'Дані сервіса оновлено · ${_relativeUkrShort(t)}';
    }
  }
}

/// Стислий текст для HUD (українською).
String _relativeUkrShort(DateTime at) {
  final now = DateTime.now();
  var diff = now.difference(at);
  if (diff.isNegative) diff = Duration.zero;

  if (diff < const Duration(seconds: 15)) return 'щойно';
  if (diff < const Duration(minutes: 1)) return '${diff.inSeconds} с тому';

  final m = diff.inMinutes;
  if (diff < const Duration(hours: 1)) {
    final tail = _minuteWord(m);
    return '$m $tail тому';
  }

  final h = diff.inHours;
  if (diff < const Duration(days: 1)) {
    final tail = _hourWord(h);
    return '$h $tail тому';
  }

  final d = diff.inDays;
  final tail = _dayWord(d);
  return '$d $tail тому';
}

String _minuteWord(int n) {
  if (n % 100 >= 11 && n % 100 <= 14) return 'хвилин';
  if (n % 10 == 1) return 'хвилина';
  if (n % 10 >= 2 && n % 10 <= 4) return 'хвилини';
  return 'хвилин';
}

String _hourWord(int n) {
  if (n % 100 >= 11 && n % 100 <= 14) return 'годин';
  if (n % 10 == 1) return 'година';
  if (n % 10 >= 2 && n % 10 <= 4) return 'години';
  return 'годин';
}

String _dayWord(int n) {
  if (n % 100 >= 11 && n % 100 <= 14) return 'днів';
  if (n % 10 == 1) return 'день';
  if (n % 10 >= 2 && n % 10 <= 4) return 'дні';
  return 'днів';
}

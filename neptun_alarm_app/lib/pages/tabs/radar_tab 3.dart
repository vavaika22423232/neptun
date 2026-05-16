import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../config/config.dart';
import '../../core/di/service_locator.dart';
import '../../core/widgets/tab_index_scope.dart';
import '../../design/design_exports.dart';
import '../../features/radar/domain/radar_quick_filter.dart';
import '../../features/radar/presentation/providers/radar_feed_provider.dart';
import '../../features/radar/presentation/widgets/radar_overview_strip.dart';
import '../../services/data_stream_service.dart';
import '../../core/widgets/neptun_overlay_insets.dart';
import '../messages_page.dart';
import 'widgets/radar_tab_feed.dart';
import 'widgets/radar_tab_header.dart';
import 'widgets/radar_telegram_inline_row.dart';

/// Вкладка «Радар»: стрічка подій + вбудований вибір регіонів для сповіщень.
///
/// Дані стрічки — [radarFeedProvider] (REST + доповнення лічильника з SSE).
class RadarTab extends ConsumerStatefulWidget {
  const RadarTab({super.key});

  @override
  ConsumerState<RadarTab> createState() => _RadarTabState();
}

class _RadarTabState extends ConsumerState<RadarTab>
    with AutomaticKeepAliveClientMixin {
  @override
  bool get wantKeepAlive => true;

  Timer? _refreshTimer;
  int? _lastTabIndex;
  StreamSubscription<List<dynamic>>? _alarmSub;

  static const int _radarShellTabIndex = 1;

  bool _showTelegramPromo = false;

  /// 0 — стрічка радару; 1 — області й сповіщення ([AlertsPage] embedded).
  int _paneIndex = 0;

  RadarQuickFilter _quickFilter = RadarQuickFilter.all;

  @override
  void initState() {
    super.initState();
    _loadTelegramPromoFlag();
    _refreshTimer = Timer.periodic(
      const Duration(seconds: 30),
      (_) => ref.read(radarFeedProvider.notifier).refresh(),
    );
    _alarmSub = sl<DataStreamService>().alarmStream.listen(
      (rows) =>
          ref.read(radarFeedProvider.notifier).applyAlarmStreamSnapshot(rows),
    );
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    _alarmSub?.cancel();
    super.dispose();
  }

  Future<void> _loadTelegramPromoFlag() async {
    final prefs = await SharedPreferences.getInstance();
    if (!mounted) return;
    final dismissed =
        prefs.getBool(PrefsKeys.telegramRadarBannerDismissed) ?? false;
    setState(() => _showTelegramPromo = !dismissed);
  }

  Future<void> _dismissTelegramPromo() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(PrefsKeys.telegramRadarBannerDismissed, true);
    if (mounted) setState(() => _showTelegramPromo = false);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final uri = GoRouterState.of(context).uri;
    if (uri.queryParameters['view'] == 'regions' && _paneIndex != 1) {
      setState(() => _paneIndex = 1);
    }

    final idx = TabIndexScope.maybeOf(context)?.index ?? -1;
    if (idx == _radarShellTabIndex &&
        _lastTabIndex != _radarShellTabIndex) {
      _lastTabIndex = _radarShellTabIndex;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        ref.read(radarFeedProvider.notifier).refresh();
      });
    } else if (idx != _radarShellTabIndex) {
      _lastTabIndex = idx;
    }
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final feed = ref.watch(radarFeedProvider);
    final historyMinutes = ref.watch(radarMapHistoryMinutesProvider);

    final cs = Theme.of(context).colorScheme;
    final topInset = neptunContentTopPadding(context) + NeptunSpacing.lg;
    final bottomInset = neptunContentBottomPadding(context);
    final h = NeptunSpacing.screenHorizontal;

    return NeptunTabPageScaffold(
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: EdgeInsets.fromLTRB(h, topInset, h, NeptunSpacing.sm),
            child: NeptunBentoSurface(
              padding: const EdgeInsets.all(NeptunSpacing.xs),
              child: SegmentedButton<int>(
                showSelectedIcon: false,
                style: SegmentedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(
                    horizontal: NeptunSpacing.sm,
                    vertical: NeptunSpacing.sm,
                  ),
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  visualDensity: VisualDensity.compact,
                ),
                segments: const [
                  ButtonSegment(
                    value: 0,
                    label: Text('Стрічка'),
                    icon: Icon(Icons.radar, size: 18),
                  ),
                  ButtonSegment(
                    value: 1,
                    label: Text('Регіони'),
                    icon: Icon(Icons.notifications_active_outlined, size: 18),
                  ),
                ],
                selected: {_paneIndex},
                onSelectionChanged: (selection) {
                  HapticFeedback.selectionClick();
                  setState(() => _paneIndex = selection.first);
                },
              ),
            ),
          ),
          Expanded(
            child: IndexedStack(
              index: _paneIndex,
              children: [
                RefreshIndicator(
                  onRefresh: () =>
                      ref.read(radarFeedProvider.notifier).refresh(),
                  color: cs.primary,
                  backgroundColor: cs.surfaceContainerHighest,
                  child: CustomScrollView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    slivers: [
                      SliverToBoxAdapter(
                        child: Padding(
                          padding: EdgeInsets.fromLTRB(h, 0, h, 0),
                          child: NeptunBentoSurface(
                            margin: const EdgeInsets.only(
                              bottom: NeptunSpacing.md,
                            ),
                            padding: const EdgeInsets.fromLTRB(
                              NeptunSpacing.lg,
                              NeptunSpacing.lg,
                              NeptunSpacing.lg,
                              NeptunSpacing.sm,
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                RadarTabHeader(
                                  activeAlarms: feed.activeOblastsUnderAlarm,
                                ),
                                if (_showTelegramPromo)
                                  RadarTelegramInlineRow(
                                    onDismiss: _dismissTelegramPromo,
                                  ),
                              ],
                            ),
                          ),
                        ),
                      ),
                      if (!feed.isLoading && feed.error == null)
                        SliverToBoxAdapter(
                          child: Padding(
                            padding: EdgeInsets.fromLTRB(
                              h,
                              0,
                              h,
                              NeptunSpacing.md,
                            ),
                            child: RadarOverviewStrip(
                              markers: feed.markers,
                              activeOblastsUnderAlarm:
                                  feed.activeOblastsUnderAlarm,
                              quickFilter: _quickFilter,
                              onQuickFilterChanged: (v) =>
                                  setState(() => _quickFilter = v),
                              historyMinutes: historyMinutes,
                              lastFetchedAt: feed.lastFetchedAt,
                            ),
                          ),
                        ),
                      ...buildRadarFeedSlivers(
                        isLoading: feed.isLoading,
                        error: feed.error,
                        onRetry: () =>
                            ref.read(radarFeedProvider.notifier).refresh(),
                        markers: feed.markers,
                        horizontalPadding: h,
                        quickFilter: _quickFilter,
                      ),
                      SliverToBoxAdapter(child: SizedBox(height: bottomInset)),
                    ],
                  ),
                ),
                const AlertsPage(embedded: true),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

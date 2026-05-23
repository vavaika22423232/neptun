import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../config/prefs_keys.dart';
import '../../core/di/service_locator.dart';
import '../../core/widgets/neptun_error_state.dart';
import '../../core/widgets/neptun_shimmer.dart';
import '../../core/widgets/tab_index_scope.dart';
import '../../features/radar/domain/radar_feed_section.dart';
import '../../features/radar/domain/threat_event.dart';
import '../../features/radar/presentation/providers/radar_ui_provider.dart';
import '../../features/radar/presentation/radar_tokens.dart';
import '../../features/radar/presentation/providers/radar_feed_provider.dart'
    show radarFeedProvider, radarMapHistoryMinutesProvider;
import '../../features/radar/presentation/widgets/radar_empty_state.dart';
import '../../features/radar/presentation/widgets/radar_filter_chips.dart';
import '../../features/radar/presentation/widgets/radar_live_status_bar.dart';
import '../../features/radar/presentation/widgets/radar_new_updates_pill.dart';
import '../../features/radar/presentation/widgets/telegram_channel_card.dart';
import '../../features/radar/presentation/widgets/threat_event_card.dart';
import '../app_shell.dart';

/// Premium live threat monitoring feed (not a map).
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
  final _scrollController = ScrollController();
  final _knownMarkerIds = <String>{};

  static const int _radarTabIndex = 1;

  @override
  void initState() {
    super.initState();
    _refreshTimer = Timer.periodic(
      const Duration(seconds: 30),
      (_) => ref.read(radarFeedProvider.notifier).refresh(),
    );
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final idx = TabIndexScope.maybeOf(context)?.index ?? -1;
    if (idx == _radarTabIndex && _lastTabIndex != _radarTabIndex) {
      _lastTabIndex = _radarTabIndex;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        ref.read(radarFeedProvider.notifier).refresh();
      });
    } else if (idx != _radarTabIndex) {
      _lastTabIndex = idx;
    }
  }

  Set<String> _myRegions() {
    final list = sl<SharedPreferences>().getStringList(PrefsKeys.selectedRegions) ?? [];
    return list.map((e) => e.trim()).where((e) => e.isNotEmpty).toSet();
  }

  Future<void> _onRefresh() =>
      ref.read(radarFeedProvider.notifier).refresh();

  double _topInset(BuildContext context) {
    return MediaQuery.paddingOf(context).top +
        AppShellState.chromeHeight +
        AppShellState.contentTopGap;
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final feed = ref.watch(radarFeedProvider);
    final ui = ref.watch(radarUiProvider);
    final historyMinutes = ref.watch(radarMapHistoryMinutesProvider);
    final myRegions = _myRegions();

    var newMarkerCount = 0;
    for (final m in feed.markers) {
      final id = (m['id'] ?? m['track_id'] ?? '').toString();
      if (id.isEmpty || _knownMarkerIds.contains(id)) continue;
      _knownMarkerIds.add(id);
      newMarkerCount++;
    }
    if (newMarkerCount > 0) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        ref.read(radarUiProvider.notifier).bumpNewUpdates(newMarkerCount);
      });
    }

    final events = buildThreatEvents(
      feed.markers,
      filter: ui.filter,
      searchQuery: ui.searchQuery,
      myRegions: myRegions,
    );

    final topInset = _topInset(context);

    final header = Padding(
      padding: EdgeInsets.fromLTRB(
        RadarTokens.screenPadH,
        topInset,
        RadarTokens.screenPadH,
        RadarTokens.cardGap,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          RadarLiveStatusBar(
            eventCount: events.length,
            activeOblasts: feed.activeOblastsUnderAlarm,
            lastFetchedAt: feed.lastFetchedAt,
            isStale: feed.showStaleBanner,
          ),
          const SizedBox(height: RadarTokens.cardGap),
          TelegramChannelCard(
            compact: ui.telegramDismissed,
            onDismiss: () => ref.read(radarUiProvider.notifier).dismissTelegram(),
          ),
          const SizedBox(height: RadarTokens.cardGap),
          _SearchRow(
            expanded: ui.searchExpanded,
            query: ui.searchQuery,
            onToggle: () => ref.read(radarUiProvider.notifier).toggleSearch(),
            onChanged: (v) => ref.read(radarUiProvider.notifier).setSearch(v),
          ),
          const SizedBox(height: RadarTokens.cardGap),
          RadarFilterChips(
            selected: ui.filter,
            onChanged: ref.read(radarUiProvider.notifier).setFilter,
            showMyRegions: myRegions.isNotEmpty,
          ),
          const SizedBox(height: 6),
          Text(
            'Вікно $historyMinutes хв',
            style: GoogleFonts.plusJakartaSans(
              fontSize: 11,
              color: RadarTokens.textMuted,
            ),
          ),
          if (feed.showStaleBanner) ...[
            const SizedBox(height: RadarTokens.cardGap),
            _StaleChip(),
          ],
        ],
      ),
    );

    Widget feedBody;
    if (feed.isLoading && feed.markers.isEmpty) {
      feedBody = const Padding(
        padding: EdgeInsets.symmetric(horizontal: RadarTokens.screenPadH),
        child: Column(
          children: [
            NeptunShimmer(width: double.infinity, height: 88, borderRadius: 22),
            SizedBox(height: 10),
            NeptunShimmer(width: double.infinity, height: 88, borderRadius: 22),
            SizedBox(height: 10),
            NeptunShimmer(width: double.infinity, height: 88, borderRadius: 22),
          ],
        ),
      );
    } else if (feed.error != null && feed.markers.isEmpty) {
      feedBody = Padding(
        padding: const EdgeInsets.all(24),
        child: NeptunErrorBanner(
          message: 'Помилка завантаження',
          onRetry: _onRefresh,
        ),
      );
    } else if (events.isEmpty) {
      feedBody = RadarEmptyState(
        lastUpdated: feed.lastFetchedAt,
        onOpenMap: () {
          context.findAncestorStateOfType<AppShellState>()?.switchToMap();
        },
      );
    } else {
      feedBody = ListView.builder(
        controller: _scrollController,
        physics: const ClampingScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(
          RadarTokens.screenPadH,
          0,
          RadarTokens.screenPadH,
          120,
        ),
        itemCount: sections.length,
        itemBuilder: (context, index) {
          final item = sections[index];
          return switch (item) {
            RadarSectionHeaderItem() => Padding(
                padding: const EdgeInsets.only(top: 4, bottom: 10),
                child: Text(
                  'Активні зараз',
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.5,
                    color: RadarTokens.textMuted,
                    height: 1.2,
                  ),
                ),
              ),
            RadarSectionEventItem(:final event) => Padding(
                padding: const EdgeInsets.only(bottom: RadarTokens.cardGap),
                child: ThreatEventCard(event: event),
              ),
          };
        },
      );
    }

    return ColoredBox(
      color: RadarTokens.bg,
      child: Stack(
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              header,
              Expanded(
                child: RefreshIndicator(
                  color: RadarTokens.accent,
                  onRefresh: _onRefresh,
                  child: feedBody is ListView
                      ? feedBody
                      : SingleChildScrollView(
                          physics: const ClampingScrollPhysics(),
                          child: feedBody,
                        ),
                ),
              ),
            ],
          ),
          RadarNewUpdatesPill(
            count: ui.newUpdatesCount,
            onTap: () {
              ref.read(radarUiProvider.notifier).clearNewUpdates();
              if (_scrollController.hasClients) {
                _scrollController.animateTo(
                  0,
                  duration: const Duration(milliseconds: 320),
                  curve: Curves.easeOutCubic,
                );
              }
            },
          ),
        ],
      ),
    );
  }
}

class _SearchRow extends StatefulWidget {
  const _SearchRow({
    required this.expanded,
    required this.query,
    required this.onToggle,
    required this.onChanged,
  });

  final bool expanded;
  final String query;
  final VoidCallback onToggle;
  final ValueChanged<String> onChanged;

  @override
  State<_SearchRow> createState() => _SearchRowState();
}

class _SearchRowState extends State<_SearchRow> {
  late final TextEditingController _controller;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: widget.query);
  }

  @override
  void didUpdateWidget(covariant _SearchRow oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.query != widget.query && _controller.text != widget.query) {
      _controller.text = widget.query;
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.expanded) {
      return Align(
        alignment: Alignment.centerLeft,
        child: TextButton.icon(
          onPressed: widget.onToggle,
          icon: const Icon(Icons.search, size: 18, color: RadarTokens.textMuted),
          label: Text(
            'Пошук',
            style: GoogleFonts.plusJakartaSans(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: RadarTokens.textSecondary,
            ),
          ),
        ),
      );
    }
    return TextField(
      controller: _controller,
      onChanged: widget.onChanged,
      style: GoogleFonts.plusJakartaSans(color: RadarTokens.textPrimary),
      decoration: InputDecoration(
        hintText: 'Область, місто або подія',
        hintStyle: GoogleFonts.plusJakartaSans(color: RadarTokens.textMuted),
        prefixIcon: const Icon(Icons.search, color: RadarTokens.textMuted),
        suffixIcon: IconButton(
          onPressed: widget.onToggle,
          icon: const Icon(Icons.close, color: RadarTokens.textMuted),
        ),
        filled: true,
        fillColor: RadarTokens.card,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: RadarTokens.border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: RadarTokens.border),
        ),
      ),
    );
  }
}

class _StaleChip extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: RadarTokens.warning.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: RadarTokens.warning.withValues(alpha: 0.25)),
      ),
      child: Row(
        children: [
          const Icon(Icons.cloud_off_rounded, size: 16, color: RadarTokens.warning),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              'Показано збережені дані',
              style: GoogleFonts.plusJakartaSans(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: RadarTokens.warning,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

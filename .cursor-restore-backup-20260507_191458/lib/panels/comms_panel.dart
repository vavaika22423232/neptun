import 'package:flutter/material.dart';
import 'dart:async';

import '../core/widgets/neptun_shimmer.dart';
import '../models/threat_event.dart';
import '../services/map_data_service.dart';
import '../services/threat_feed_service.dart';
import '../core/widgets/neptun_card.dart';

class CommsPanel extends StatefulWidget {
  const CommsPanel({super.key});

  @override
  State<CommsPanel> createState() => _CommsPanelState();
}

class _CommsPanelState extends State<CommsPanel> {
  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    final colorScheme = Theme.of(context).colorScheme;

    return NeptunCard(
      variant: NeptunCardVariant.elevated,
      padding: EdgeInsets.zero,
      child: Column(
        children: [
          // Header
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 12),
            child: Row(
              children: [
                Icon(Icons.chat_bubble, color: colorScheme.primary, size: 18),
                const SizedBox(width: 8),
                Text(
                  'Зв’язок',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: colorScheme.onSurface,
                  ),
                ),
              ],
            ),
          ),

          Divider(
            height: 1,
            color: colorScheme.outlineVariant.withValues(alpha: 0.3),
          ),

          // Content
          Expanded(
            child: ListView(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 20),
              children: [
                // Threat Feed Section
                const _ThreatFeedPanel(),

                const SizedBox(height: 16),
                _buildSectionLabel('КАНАЛИ'),
                const SizedBox(height: 8),

                // Global Chat Tile
                _buildChannelTile(
                  context,
                  title: 'ЗАГАЛЬНИЙ ЧАТ',
                  subtitle: 'Офіційна спільнота',
                  icon: Icons.public,
                  isDark: isDark,
                  onTap: () {
                    // Chat is now a tab in AppShell, not a standalone page
                    Navigator.of(context).popUntil((route) => route.isFirst);
                  },
                  color: Theme.of(context).colorScheme.primary,
                ),

                const SizedBox(height: 8),

                // 1:1 Chats (Placeholder)
                _buildChannelTile(
                  context,
                  title: 'ПРИВАТНІ ПОВІДОМЛЕННЯ',
                  subtitle: 'Зашифровані канали (Скоро)',
                  icon: Icons.lock_outline,
                  isDark: isDark,
                  onTap: () {},
                  isInactive: true,
                  color: Theme.of(context).colorScheme.tertiary,
                ),

                const SizedBox(height: 16),
                _buildSectionLabel('ІНФОРМАЦІЯ'),
                const SizedBox(height: 8),

                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.surfaceContainer,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: Theme.of(context).colorScheme.outlineVariant,
                    ),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        Icons.info_outline,
                        color: colorScheme.onSurface.withValues(alpha: 0.6),
                        size: 16,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'Утримуйте повідомлення для дій',
                          style: TextStyle(
                            color: colorScheme.onSurface.withValues(alpha: 0.6),
                            fontSize: 11,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSectionLabel(String label) {
    final colorScheme = Theme.of(context).colorScheme;
    return Text(
      label,
      style: TextStyle(
        fontSize: 10,
        fontWeight: FontWeight.w900,
        letterSpacing: 1.5,
        color: colorScheme.outline,
      ),
    );
  }

  Widget _buildChannelTile(
    BuildContext context, {
    required String title,
    required String subtitle,
    required IconData icon,
    required bool isDark,
    required VoidCallback onTap,
    bool isInactive = false,
    required Color color,
  }) {
    final colorScheme = Theme.of(context).colorScheme;
    final effectiveColor = isInactive ? colorScheme.outline : color;

    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: effectiveColor.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: effectiveColor.withValues(alpha: 0.2)),
        ),
        child: Row(
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: effectiveColor.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, color: effectiveColor, size: 20),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      fontWeight: FontWeight.w600,
                      color: isInactive
                          ? colorScheme.outline
                          : colorScheme.onSurface,
                      fontSize: 13,
                      letterSpacing: 0.5,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    subtitle,
                    style: TextStyle(
                      color: Theme.of(
                        context,
                      ).colorScheme.onSurface.withValues(alpha: 0.5),
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
            ),
            if (!isInactive)
              Icon(
                Icons.chevron_right_rounded,
                color: effectiveColor.withValues(alpha: 0.5),
                size: 18,
              ),
          ],
        ),
      ),
    );
  }
}

class _ThreatFeedPanel extends StatefulWidget {
  const _ThreatFeedPanel();

  @override
  State<_ThreatFeedPanel> createState() => _ThreatFeedPanelState();
}

class _ThreatFeedPanelState extends State<_ThreatFeedPanel> {
  static const int _timeRangeMinutes = 60;
  static const int _maxEvents = 5;
  static const Duration _refreshInterval = Duration(seconds: 60);

  final MapDataService _mapDataService = MapDataService();
  final ThreatFeedService _threatFeedService = ThreatFeedService();
  Timer? _refreshTimer;

  bool _isLoading = true;
  String? _error;
  List<ThreatEvent> _events = [];

  @override
  void initState() {
    super.initState();
    _loadThreatFeed();
    _refreshTimer = Timer.periodic(
      _refreshInterval,
      (_) => _loadThreatFeed(showLoading: false),
    );
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadThreatFeed({bool showLoading = true}) async {
    if (showLoading && mounted) {
      setState(() => _isLoading = true);
    }

    try {
      final markerData = await _mapDataService.fetchThreatMarkers(
        timeRange: _timeRangeMinutes,
      );
      final events = _threatFeedService
          .buildEvents(markerData.markers)
          .take(_maxEvents)
          .toList();

      if (!mounted) return;
      setState(() {
        _events = events;
        _error = null;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = 'Failed to load feed';
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.secondary.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Theme.of(context).colorScheme.secondary.withValues(alpha: 0.1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                'СТРІЧКА ЗАГРОЗ',
                style: TextStyle(
                  fontWeight: FontWeight.w900,
                  color: Theme.of(context).colorScheme.secondary,
                  fontSize: 10,
                  letterSpacing: 1.5,
                ),
              ),
              const Spacer(),
              Text(
                'ОСТАННІ $_timeRangeMinutes ХВ',
                style: TextStyle(
                  fontSize: 9,
                  color: Theme.of(context).colorScheme.outline,
                  letterSpacing: 1.0,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          if (_isLoading)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: Column(
                children: const [
                  NeptunShimmer(height: 12),
                  SizedBox(height: 8),
                  NeptunShimmer(height: 12, width: 200),
                ],
              ),
            )
          else if (_error != null)
            Text(
              _error!,
              style: TextStyle(
                color: Theme.of(context).colorScheme.outline,
                fontSize: 10,
              ),
            )
          else if (_events.isEmpty)
            Text(
              'Загроз не виявлено',
              style: TextStyle(
                color: Theme.of(context).colorScheme.outline,
                fontSize: 11,
                fontStyle: FontStyle.italic,
              ),
            )
          else
            Column(
              children: _events.map((event) {
                final time = event.timestamp != null
                    ? '${event.timestamp!.hour.toString().padLeft(2, '0')}:${event.timestamp!.minute.toString().padLeft(2, '0')}'
                    : '--:--';
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 6),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _getThreatEmoji(event.threatType),
                        style: const TextStyle(fontSize: 13),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              event.title,
                              style: TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                                color: Theme.of(context).colorScheme.onSurface,
                              ),
                            ),
                            Text(
                              '${event.location} · $time',
                              style: TextStyle(
                                fontSize: 11,
                                color: Theme.of(context).colorScheme.outline,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              }).toList(),
            ),
        ],
      ),
    );
  }

  String _getThreatEmoji(String type) {
    switch (type) {
      case 'shahed':
        return '🛩️';
      case 'raketa':
        return '🚀';
      case 'kab':
        return '💣';
      case 'rozved':
        return '🔍';
      case 'avia':
        return '✈️';
      default:
        return '⚠️';
    }
  }
}

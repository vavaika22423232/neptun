import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'dart:async';
import '../models/threat_event.dart';
import '../services/map_data_service.dart';
import '../services/threat_feed_service.dart';

class ChatHomePage extends StatefulWidget {
  const ChatHomePage({super.key});

  @override
  State<ChatHomePage> createState() => _ChatHomePageState();
}

class _ChatHomePageState extends State<ChatHomePage>
    with SingleTickerProviderStateMixin {
  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return DefaultTabController(
      length: 3,
      child: Container(
        color: cs.surface,
        child: Column(
          children: [
            Container(
              margin: const EdgeInsets.fromLTRB(16, 8, 16, 6),
              decoration: BoxDecoration(
                color: cs.surfaceContainer,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: cs.outline),
              ),
              child: TabBar(
                indicator: BoxDecoration(
                  color: cs.surfaceContainerHighest,
                  borderRadius: BorderRadius.circular(10),
                ),
                labelColor: cs.onSurface,
                unselectedLabelColor: cs.onSurface.withValues(alpha: 0.5),
                dividerColor: Colors.transparent,
                tabs: const [
                  Tab(text: 'Головний'),
                  Tab(text: '1:1'),
                  Tab(text: 'Групи'),
                ],
              ),
            ),
            Expanded(
              child: TabBarView(
                children: [
                  _buildGlobalChat(context),
                  _buildEmptySection(
                    title: '1:1 чати',
                    subtitle:
                        'Запустимо персональні діалоги після оновлення API.',
                    actionLabel: 'Створити діалог',
                  ),
                  _buildEmptySection(
                    title: 'Групи та канали',
                    subtitle: 'Групові чати в процесі підготовки.',
                    actionLabel: 'Створити групу',
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildGlobalChat(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const _ThreatFeedPanel(),
        const SizedBox(height: 12),
        _chatTile(
          context,
          title: 'Глобальний чат',
          subtitle: 'Офіційна спільнота · живе обговорення',
          icon: Icons.public,
          onTap: () => context.push('/chat'),
        ),
        const SizedBox(height: 12),
        _infoCard(
          title: 'Підтримка відповідей та пересилань',
          subtitle: 'Використовуй довге натискання на повідомлення для дій.',
        ),
      ],
    );
  }

  Widget _buildEmptySection({
    required String title,
    required String subtitle,
    required String actionLabel,
  }) {
    final cs = Theme.of(context).colorScheme;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.chat_bubble_outline,
              size: 42,
              color: cs.onSurface.withValues(alpha: 0.4),
            ),
            const SizedBox(height: 12),
            Text(
              title,
              style: TextStyle(
                color: cs.onSurface,
                fontSize: 16,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              subtitle,
              textAlign: TextAlign.center,
              style: TextStyle(
                color: cs.onSurface.withValues(alpha: 0.5),
                fontSize: 13,
              ),
            ),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('$actionLabel скоро буде доступно')),
                );
              },
              child: Text(actionLabel),
            ),
          ],
        ),
      ),
    );
  }

  Widget _chatTile(
    BuildContext context, {
    required String title,
    required String subtitle,
    required IconData icon,
    required VoidCallback onTap,
  }) {
    final cs = Theme.of(context).colorScheme;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(14),
      child: Ink(
        decoration: BoxDecoration(
          color: cs.surfaceContainer,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: cs.outline),
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          child: Row(
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: cs.surfaceContainerHighest,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(icon, color: cs.onSurface),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: TextStyle(
                        fontWeight: FontWeight.w600,
                        color: cs.onSurface,
                        fontSize: 14,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      subtitle,
                      style: TextStyle(
                        color: cs.onSurface.withValues(alpha: 0.5),
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
              Icon(
                Icons.chevron_right,
                color: cs.onSurface.withValues(alpha: 0.4),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _infoCard({
    required String title,
    required String subtitle,
  }) {
    final cs = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: cs.surfaceContainer,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: cs.outline),
      ),
      child: Row(
        children: [
          Icon(
            Icons.info_outline,
            color: cs.onSurface.withValues(alpha: 0.4),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    color: cs.onSurface,
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  subtitle,
                  style: TextStyle(
                    color: cs.onSurface.withValues(alpha: 0.5),
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
        ],
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
        _error = 'Не вдалося оновити ленту';
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final cardColor = cs.surfaceContainer;
    final borderColor = cs.outline;
    final titleColor = cs.onSurface;
    final subtitleColor = cs.onSurface.withValues(alpha: 0.5);

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: cardColor,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: borderColor),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                'Лента',
                style: TextStyle(
                  fontWeight: FontWeight.w700,
                  color: titleColor,
                  fontSize: 14,
                ),
              ),
              const Spacer(),
              Text(
                'Останні $_timeRangeMinutes хв',
                style: TextStyle(fontSize: 11, color: subtitleColor),
              ),
            ],
          ),
          const SizedBox(height: 10),
          if (_isLoading)
            Center(
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 6),
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: cs.primary,
                ),
              ),
            )
          else if (_error != null)
            Text(_error!, style: TextStyle(color: subtitleColor, fontSize: 12))
          else if (_events.isEmpty)
            Text(
              'Немає подій за останні $_timeRangeMinutes хв',
              style: TextStyle(color: subtitleColor, fontSize: 12),
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
                                color: titleColor,
                              ),
                            ),
                            Text(
                              '${event.location} · $time',
                              style: TextStyle(
                                fontSize: 11,
                                color: subtitleColor,
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

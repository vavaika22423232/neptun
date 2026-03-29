import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import '../../config/config.dart';
import '../../core/di/service_locator.dart';
import '../../core/pro/pro_features.dart';
import '../../core/widgets/tab_index_scope.dart';
import '../../services/data_stream_service.dart';
import '../../core/widgets/neptun_empty_state.dart';
import '../../core/widgets/neptun_shimmer.dart';
import '../../core/widgets/neptun_error_state.dart';
import '../../widgets/threat_timeline.dart';
import '../../design/design_exports.dart';

/// Radar tab -- native threat dashboard replacing WebView DashboardTab.
class RadarTab extends StatefulWidget {
  const RadarTab({super.key});

  @override
  State<RadarTab> createState() => _RadarTabState();
}

class _RadarTabState extends State<RadarTab>
    with AutomaticKeepAliveClientMixin {
  @override
  bool get wantKeepAlive => true;

  List<Map<String, dynamic>> _markers = [];
  Map<String, int> _summary = {};
  int _activeAlarms = 0;
  bool _isLoading = true;
  String? _error;
  Timer? _refreshTimer;
  int? _lastTabIndex;
  StreamSubscription<List<dynamic>>? _alarmSub;

  static const int _radarTabIndex = 1;

  @override
  void initState() {
    super.initState();
    _loadData();
    _refreshTimer = Timer.periodic(
      const Duration(seconds: 30),
      (_) => _loadData(),
    );
    _alarmSub = sl<DataStreamService>().alarmStream.listen(_onAlarmUpdate);
  }

  void _onAlarmUpdate(List<dynamic> rawData) {
    int count = 0;
    for (final r in rawData) {
      if (r is Map && (r['activeAlerts'] as List?)?.isNotEmpty == true) {
        count++;
      }
    }
    if (mounted) setState(() => _activeAlarms = count);
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    _alarmSub?.cancel();
    super.dispose();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final idx = TabIndexScope.maybeOf(context)?.index ?? -1;
    if (idx == _radarTabIndex && _lastTabIndex != _radarTabIndex) {
      _lastTabIndex = _radarTabIndex;
      WidgetsBinding.instance.addPostFrameCallback((_) => _loadData());
    } else if (idx != _radarTabIndex) {
      _lastTabIndex = idx;
    }
  }

  static int _intVal(dynamic v) {
    if (v == null) return 0;
    if (v is int) return v;
    if (v is num) return v.toInt();
    return 0;
  }

  Future<void> _loadData() async {
    try {
      final timeRange = ProGate.isPro ? 180 : 60;
      final threatsUrl = '${ApiConfig.threats}?timeRange=$timeRange';
      final responses = await Future.wait([
        http
            .get(Uri.parse(threatsUrl))
            .timeout(ApiConfig.httpTimeout),
        http
            .get(Uri.parse(ApiConfig.alarmStatus))
            .timeout(ApiConfig.httpTimeout),
      ]);

      if (!mounted) return;

      setState(() {
        _isLoading = false;
        _error = null;

        if (responses[0].statusCode == 200) {
          final data = jsonDecode(responses[0].body);
          if (data is List) {
            _markers = data.cast<Map<String, dynamic>>();
            _summary = {};
          } else if (data is Map) {
            if (data['threats'] is List) {
              _markers =
                  (data['threats'] as List).cast<Map<String, dynamic>>();
            } else if (data['markers'] is List) {
              _markers =
                  (data['markers'] as List).cast<Map<String, dynamic>>();
            } else {
              _markers = [];
            }
            final s = data['summary'];
            _summary = s is Map
                ? {
                    'drones': _intVal(s['drones']),
                    'missiles': _intVal(s['missiles']),
                    'kab': _intVal(s['kab']),
                    'ballistic': _intVal(s['ballistic']),
                    'avia': _intVal(s['avia']),
                  }
                : {};
          }
        }

        if (responses[1].statusCode == 200) {
          final alarm = jsonDecode(responses[1].body);
          final alerts = alarm['alerts'];
          _activeAlarms = alerts is Map ? alerts.length : 0;
        }
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _error = e.toString();
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final cs = Theme.of(context).colorScheme;
    final topInset = MediaQuery.of(context).padding.top + 52 + NeptunSpacing.lg;

    return RefreshIndicator(
      onRefresh: _loadData,
      child: ListView(
        padding: EdgeInsets.fromLTRB(NeptunSpacing.lg, topInset, NeptunSpacing.lg, NeptunSpacing.xxxl),
        children: [
          // Hero header
          Padding(
            padding: const EdgeInsets.fromLTRB(NeptunSpacing.lg, 0, NeptunSpacing.lg, NeptunSpacing.lg),
            child: Row(
              children: [
                Text(
                  'Радар',
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: NeptunTypography.hero,
                    fontWeight: FontWeight.w800,
                    color: cs.onSurface,
                    letterSpacing: -0.5,
                  ),
                ),
                const Spacer(),
                StatusPill(
                  label: 'ОНЛАЙН',
                  variant: StatusPillVariant.safe,
                  icon: Icons.circle,
                ),
              ],
            ),
          ),

          if (_isLoading)
            Padding(
              padding: const EdgeInsets.only(top: 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const NeptunShimmer(width: 120, height: 28, borderRadius: 8),
                  const SizedBox(height: 24),
                  Row(
                    children: [
                      Expanded(
                        child: TacticalSurface(
                          style: TacticalSurfaceStyle.flat,
                          padding: const EdgeInsets.all(NeptunSpacing.lg),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const NeptunShimmer(width: 80, height: 16, borderRadius: 4),
                              const SizedBox(height: 8),
                              const NeptunShimmer(width: 120, height: 12, borderRadius: 4),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: TacticalSurface(
                          style: TacticalSurfaceStyle.flat,
                          padding: const EdgeInsets.all(NeptunSpacing.lg),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const NeptunShimmer(width: 80, height: 16, borderRadius: 4),
                              const SizedBox(height: 8),
                              const NeptunShimmer(width: 100, height: 12, borderRadius: 4),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),
                  ...List.generate(3, (_) => Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: TacticalSurface(
                      style: TacticalSurfaceStyle.flat,
                      padding: const EdgeInsets.all(NeptunSpacing.lg),
                      child: Row(
                        children: [
                          const NeptunShimmer(width: 20, height: 20, borderRadius: 6),
                          const SizedBox(width: 12),
                          Expanded(
                            child: NeptunShimmer(
                              width: double.infinity,
                              height: 14,
                              borderRadius: 4,
                            ),
                          ),
                        ],
                      ),
                    ),
                  )),
                ],
              ),
            )
          else if (_error != null)
            NeptunErrorBanner(
              message: 'Помилка завантаження',
              onRetry: _loadData,
            )
          else ...[
            // Status hero
            DashboardStatusBar(
              hasAlarms: _activeAlarms > 0,
              alarmCount: _activeAlarms,
              subtitle: 'Загроз сьогодні: ${_markers.length}',
              onTap: () => context.push('/briefing'),
            ),

            // Briefing CTA
            TacticalSurface(
              style: TacticalSurfaceStyle.flat,
              onTap: () => context.push('/briefing'),
              child: Row(
                children: [
                  Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      color: cs.primary.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(NeptunRadius.md),
                    ),
                    child: Icon(Icons.auto_stories_rounded, color: cs.primary, size: 24),
                  ),
                  const SizedBox(width: NeptunSpacing.lg),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Брифінг ситуації',
                          style: GoogleFonts.plusJakartaSans(
                            fontSize: NeptunTypography.h3,
                            fontWeight: FontWeight.w600,
                            color: cs.onSurface,
                          ),
                        ),
                        Text(
                          'Ранковий та вечірній огляд',
                          style: GoogleFonts.plusJakartaSans(
                            fontSize: NeptunTypography.caption,
                            color: cs.onSurface.withValues(alpha: 0.55),
                          ),
                        ),
                      ],
                    ),
                  ),
                  Icon(Icons.chevron_right_rounded, color: cs.onSurface.withValues(alpha: 0.4)),
                ],
              ),
            ),

            // Threat timeline
            SectionHeader(title: 'Події сьогодні', icon: Icons.timeline_rounded),
            ThreatTimeline(
              markers: _markers,
              onRefresh: _loadData,
            ),
            const SizedBox(height: NeptunSpacing.sm),

            // Summary grid
            if (_summary.isNotEmpty) ...[
              SectionHeader(title: 'Загрози', icon: Icons.crisis_alert_rounded),
              _buildSummaryGrid(cs),
              const SizedBox(height: NeptunSpacing.lg),
            ],

            // Quick actions
            SectionHeader(title: 'Дії', icon: Icons.touch_app_rounded),
            TacticalSurface(
              style: TacticalSurfaceStyle.flat,
              padding: const EdgeInsets.symmetric(vertical: NeptunSpacing.sm, horizontal: NeptunSpacing.sm),
              child: Row(
                children: [
                  Expanded(
                    child: ActionTile(
                      icon: Icons.history_rounded,
                      label: 'Історія',
                      onTap: () => context.push('/history'),
                    ),
                  ),
                  Expanded(
                    child: ActionTile(
                      icon: Icons.analytics_rounded,
                      label: 'Аналітика',
                      onTap: () => context.push('/analytics'),
                    ),
                  ),
                  Expanded(
                    child: ActionTile(
                      icon: Icons.whatshot_rounded,
                      label: 'Теплова карта',
                      onTap: () => context.push('/heatmap'),
                    ),
                  ),
                ],
              ),
            ),

            // Active threats
            if (_markers.isNotEmpty) ...[
              SectionHeader(title: 'Активні загрози', icon: Icons.warning_amber_rounded),
              ..._buildThreatList(cs),
            ] else
              const Padding(
                padding: EdgeInsets.only(top: 40),
                child: NeptunEmptyState(
                  icon: Icons.shield_rounded,
                  title: 'Активних загроз немає',
                  subtitle: 'Наразі ситуація спокійна',
                ),
              ),
          ],
        ],
      ),
    );
  }

  Widget _buildSummaryGrid(ColorScheme cs) {
    final items = [
      ('drones', 'Шахеди', Icons.flight_rounded),
      ('missiles', 'Ракети', Icons.rocket_launch_rounded),
      ('ballistic', 'Балістика', Icons.warning_rounded),
      ('kab', 'КАБ / УМПК', Icons.gps_fixed_rounded),
      ('avia', 'Авіація', Icons.airplanemode_active_rounded),
    ];
    return LayoutBuilder(
      builder: (context, constraints) {
        final crossCount = constraints.maxWidth > 320 ? 3 : 2;
        return Wrap(
          spacing: 8,
          runSpacing: 8,
          children: items.map((e) {
            final count = _summary[e.$1] ?? 0;
            return SizedBox(
              width: (constraints.maxWidth - NeptunSpacing.sm * (crossCount - 1)) / crossCount,
              child: TacticalSurface(
                style: TacticalSurfaceStyle.flat,
                padding: const EdgeInsets.symmetric(vertical: NeptunSpacing.md, horizontal: NeptunSpacing.sm),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      '$count',
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 20,
                        fontWeight: FontWeight.w700,
                        color: count > 0 ? cs.error : cs.onSurface.withValues(alpha: 0.5),
                      ),
                    ),
                    const SizedBox(height: 4),
                    Icon(e.$3, size: 18, color: cs.onSurface.withValues(alpha: 0.6)),
                    const SizedBox(height: 2),
                    Text(
                      e.$2,
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 11,
                        fontWeight: FontWeight.w500,
                        color: cs.onSurface.withValues(alpha: 0.7),
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
            );
          }).toList(),
        );
      },
    );
  }

  List<Widget> _buildThreatList(ColorScheme cs) {
    final grouped = <String, List<Map<String, dynamic>>>{};
    for (final m in _markers) {
      final type = (m['threatType'] ?? m['type'] ?? 'unknown') as String;
      grouped.putIfAbsent(type, () => []).add(m);
    }

    return grouped.entries.map((entry) {
      return TacticalSurface(
        style: TacticalSurfaceStyle.flat,
        padding: const EdgeInsets.all(NeptunSpacing.lg),
        child: Row(
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: cs.error.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(NeptunRadius.sm),
              ),
              child: Icon(_threatIcon(entry.key), size: 20, color: cs.error),
            ),
            const SizedBox(width: NeptunSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _threatLabel(entry.key),
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: NeptunTypography.body,
                      fontWeight: FontWeight.w600,
                      color: cs.onSurface,
                    ),
                  ),
                  Text(
                    entry.value
                        .map((m) => m['place'] ?? '')
                        .where((s) => s.isNotEmpty)
                        .take(2)
                        .join(', '),
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: NeptunTypography.caption,
                      color: cs.onSurface.withValues(alpha: 0.55),
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
            StatusPill(
              label: '${entry.value.length}',
              variant: StatusPillVariant.alarm,
              icon: Icons.warning_rounded,
            ),
          ],
        ),
      );
    }).toList();
  }

  IconData _threatIcon(String type) {
    switch (type.toLowerCase()) {
      case 'shahed':
      case 'drone':
        return Icons.flight_rounded;
      case 'raketa':
      case 'missile':
        return Icons.rocket_launch_rounded;
      case 'ballistic':
        return Icons.warning_rounded;
      case 'avia':
        return Icons.airplanemode_active_rounded;
      case 'kab':
        return Icons.gps_fixed_rounded;
      default:
        return Icons.crisis_alert_rounded;
    }
  }

  String _threatLabel(String type) {
    switch (type.toLowerCase()) {
      case 'shahed':
      case 'drone':
        return 'Ударні БПЛА';
      case 'raketa':
      case 'missile':
        return 'Крилаті ракети';
      case 'ballistic':
        return 'Балістика';
      case 'avia':
        return 'Авіація';
      case 'kab':
        return 'КАБ';
      default:
        return type;
    }
  }
}


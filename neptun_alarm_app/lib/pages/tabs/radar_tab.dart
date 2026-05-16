import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import '../../config/config.dart';
import '../../core/pro/pro_features.dart';
import '../../core/widgets/tab_index_scope.dart';
import '../../core/widgets/neptun_shimmer.dart';
import '../../core/widgets/neptun_error_state.dart';
import '../../core/widgets/neptun_empty_state.dart';
import '../../design/design_exports.dart';
import '../app_shell.dart';

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
  bool _isLoading = true;
  String? _error;
  Timer? _refreshTimer;
  int? _lastTabIndex;

  static const int _radarTabIndex = 1;

  @override
  void initState() {
    super.initState();
    _loadData();
    _refreshTimer = Timer.periodic(
      const Duration(seconds: 30),
      (_) => _loadData(),
    );
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
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

  Future<void> _loadData() async {
    try {
      final timeRange = ProGate.isPro ? 180 : 60;
      final threatsUrl = '${ApiConfig.threats}?timeRange=$timeRange';
      final response = await http
          .get(Uri.parse(threatsUrl))
          .timeout(ApiConfig.httpTimeout);

      if (!mounted) return;

      setState(() {
        _isLoading = false;
        _error = null;

        if (response.statusCode == 200) {
          final data = jsonDecode(response.body);
          if (data is List) {
            _markers = data.cast<Map<String, dynamic>>();
          } else if (data is Map) {
            if (data['threats'] is List) {
              _markers = (data['threats'] as List).cast<Map<String, dynamic>>();
            } else if (data['markers'] is List) {
              _markers = (data['markers'] as List).cast<Map<String, dynamic>>();
            } else {
              _markers = [];
            }
          }
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
    final topInset =
        MediaQuery.of(context).padding.top +
        AppShellState.chromeHeight +
        AppShellState.contentTopGap;

    return RefreshIndicator(
      onRefresh: _loadData,
      child: ListView(
        padding: EdgeInsets.fromLTRB(
          NeptunSpacing.lg,
          topInset + 2,
          NeptunSpacing.lg,
          NeptunSpacing.xxxl,
        ),
        children: [
          if (_isLoading)
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                ...List.generate(
                  7,
                  (_) => Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: TacticalSurface(
                      style: TacticalSurfaceStyle.flat,
                      padding: const EdgeInsets.all(NeptunSpacing.lg),
                      child: Row(
                        children: [
                          const NeptunShimmer(
                            width: 20,
                            height: 20,
                            borderRadius: 6,
                          ),
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
                  ),
                ),
              ],
            )
          else if (_error != null)
            NeptunErrorBanner(
              message: 'Помилка завантаження',
              onRetry: _loadData,
            )
          else ...[
            if (_markers.isNotEmpty)
              ..._buildThreatList(cs)
            else
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

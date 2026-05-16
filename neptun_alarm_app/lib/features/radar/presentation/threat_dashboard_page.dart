import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import '../../../core/widgets/neptun_card.dart';
import '../../../core/widgets/neptun_badge.dart';
import '../../../core/widgets/neptun_empty_state.dart';
import '../../../core/widgets/neptun_error_state.dart';
import '../../../config/config.dart';

/// Native threat dashboard replacing the WebView dashboard tab.
class ThreatDashboardPage extends StatefulWidget {
  const ThreatDashboardPage({super.key});

  @override
  State<ThreatDashboardPage> createState() => _ThreatDashboardPageState();
}

class _ThreatDashboardPageState extends State<ThreatDashboardPage> {
  List<Map<String, dynamic>> _markers = [];
  Map<String, dynamic>? _alarmData;
  bool _isLoading = true;
  String? _error;
  Timer? _refreshTimer;

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

  Future<void> _loadData() async {
    try {
      final responses = await Future.wait([
        http
            .get(Uri.parse(ApiConfig.threats))
            .timeout(ApiConfig.httpTimeout),
        http
            .get(Uri.parse(ApiConfig.alarmStatus))
            .timeout(ApiConfig.httpTimeout),
      ]);

      if (!mounted) return;

      final markersResponse = responses[0];
      final alarmResponse = responses[1];

      setState(() {
        _isLoading = false;
        _error = null;

        if (markersResponse.statusCode == 200) {
          final data = jsonDecode(markersResponse.body);
          if (data is List) {
            _markers = data.cast<Map<String, dynamic>>();
          } else if (data is Map && data['markers'] is List) {
            _markers = (data['markers'] as List).cast<Map<String, dynamic>>();
          }
        }

        if (alarmResponse.statusCode == 200) {
          _alarmData = jsonDecode(alarmResponse.body) as Map<String, dynamic>?;
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
    final cs = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: Text(
          'Радар загроз',
          style: GoogleFonts.plusJakartaSans(fontWeight: FontWeight.w600),
        ),
        centerTitle: false,
      ),
      body: RefreshIndicator(
        onRefresh: _loadData,
        child: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? NeptunErrorState(
                    message: 'Не вдалося завантажити дані',
                    onRetry: _loadData,
                  )
                : _buildContent(cs),
      ),
    );
  }

  Widget _buildContent(ColorScheme cs) {
    final activeAlarms = _alarmData?['activeAlarms'] as int? ?? 0;

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        NeptunCard(
          child: Row(
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: activeAlarms > 0
                      ? cs.error.withValues(alpha: 0.15)
                      : cs.secondary.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Icon(
                  activeAlarms > 0
                      ? Icons.warning_amber_rounded
                      : Icons.shield_rounded,
                  color: activeAlarms > 0 ? cs.error : cs.secondary,
                  size: 24,
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      activeAlarms > 0
                          ? 'Активні тривоги: $activeAlarms'
                          : 'Тривог немає',
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                        color: cs.onSurface,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'Загрози на карті: ${_markers.length}',
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 13,
                        color: cs.onSurface.withValues(alpha: 0.5),
                      ),
                    ),
                  ],
                ),
              ),
              NeptunBadge(
                label: activeAlarms > 0 ? 'ТРИВОГА' : 'БЕЗПЕЧНО',
                type: activeAlarms > 0
                    ? NeptunBadgeType.danger
                    : NeptunBadgeType.success,
                pulse: activeAlarms > 0,
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        if (_markers.isNotEmpty) ...[
          Text(
            'Активні загрози',
            style: GoogleFonts.plusJakartaSans(
              fontSize: 15,
              fontWeight: FontWeight.w600,
              color: cs.onSurface,
            ),
          ),
          const SizedBox(height: 8),
          ..._buildThreatCards(context, cs),
        ] else
          const NeptunEmptyState(
            icon: Icons.shield_rounded,
            title: 'Активних загроз немає',
            subtitle: 'Наразі ситуація спокійна',
          ),
      ],
    );
  }

  List<Widget> _buildThreatCards(BuildContext context, ColorScheme cs) {
    final grouped = <String, List<Map<String, dynamic>>>{};
    for (final m in _markers) {
      final type = (m['threatType'] ?? m['type'] ?? 'unknown') as String;
      grouped.putIfAbsent(type, () => []).add(m);
    }

    return grouped.entries.map((entry) {
      return Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: NeptunCard(
          onTap: () {
            HapticFeedback.lightImpact();
            context.go('/');
          },
          child: Row(
            children: [
              Icon(
                _threatIcon(entry.key),
                size: 20,
                color: cs.error,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _threatLabel(entry.key),
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: cs.onSurface,
                      ),
                    ),
                    if (entry.value.isNotEmpty)
                      Text(
                        entry.value
                            .map((m) => m['place'] ?? m['location'] ?? '')
                            .where((s) => s.isNotEmpty)
                            .take(3)
                            .join(', '),
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 12,
                          color: cs.onSurface.withValues(alpha: 0.5),
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                  ],
                ),
              ),
              NeptunBadge.danger(label: '${entry.value.length}'),
            ],
          ),
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
      case 'artillery':
        return 'Артилерія';
      case 'rozved':
        return 'Розвідка';
      default:
        return type;
    }
  }
}

import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../../../config/api_config.dart';
import '../../../core/error/error_handler.dart';
import '../../../core/pro/pro_features.dart';
import '../../../core/widgets/neptun_empty_state.dart';
import '../../../core/widgets/neptun_error_state.dart';
import '../../../core/widgets/neptun_shimmer.dart';

class AlarmHistoryPage extends StatefulWidget {
  const AlarmHistoryPage({super.key});

  @override
  State<AlarmHistoryPage> createState() => _AlarmHistoryPageState();
}

class _AlarmHistoryPageState extends State<AlarmHistoryPage> {
  String _selectedFilter = 'all';
  bool _loading = true;
  String? _error;
  List<_AlarmRecord> _records = [];
  bool _fromCache = false;

  static const _cacheKey = 'alarm_history_cache';
  static const _cacheTsKey = 'alarm_history_cache_ts';
  static const _cacheMaxAgeHours = 24;

  @override
  void initState() {
    super.initState();
    _loadHistory();
  }

  List<_AlarmRecord> _parseRecords(dynamic data) {
    final records = <_AlarmRecord>[];
    final List items = data is List ? data : (data is Map && data['alarms'] is List ? data['alarms'] : []);
    for (final alarm in items) {
      if (alarm is! Map) continue;
      final regionName = alarm['regionName'] as String? ?? alarm['regionId']?.toString() ?? 'Невідомо';
      final alerts = alarm['activeAlerts'];
      if (alerts is List && alerts.isNotEmpty) {
        for (final alert in alerts) {
          final alertType = (alert is Map ? alert['type']?.toString() : null) ?? 'alarm';
          final lastUpdate = alert is Map ? alert['lastUpdate']?.toString() : null;
          final ts = lastUpdate != null
              ? (DateTime.tryParse(lastUpdate) ?? DateTime.now())
              : DateTime.now();
          records.add(_AlarmRecord(
            region: regionName,
            type: _mapAlertType(alertType),
            timestamp: ts,
            isActive: true,
          ));
        }
      }
    }
    return records;
  }

  Future<void> _loadHistory() async {
    setState(() {
      _loading = true;
      _error = null;
      _fromCache = false;
    });

    try {
      final resp = await http
          .get(Uri.parse(ApiConfig.alarmsAll))
          .timeout(const Duration(seconds: 10));

      if (resp.statusCode == 200) {
        final data = json.decode(resp.body);
        final records = _parseRecords(data);
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString(_cacheKey, resp.body);
        await prefs.setInt(_cacheTsKey, DateTime.now().millisecondsSinceEpoch);
        if (mounted) {
          setState(() {
            _records = records;
            _loading = false;
          });
        }
      } else {
        throw Exception('Status ${resp.statusCode}');
      }
    } catch (e) {
      final prefs = await SharedPreferences.getInstance();
      final ts = prefs.getInt(_cacheTsKey);
      final ageHours = ts != null
          ? (DateTime.now().millisecondsSinceEpoch - ts) / (1000 * 60 * 60)
          : 999.0;
      if (ageHours < _cacheMaxAgeHours) {
        final cached = prefs.getString(_cacheKey);
        if (cached != null) {
          try {
            final data = json.decode(cached);
            final records = _parseRecords(data);
            if (mounted) {
              setState(() {
                _records = records;
                _loading = false;
                _fromCache = true;
              });
            }
            return;
          } catch (_) {}
        }
      }
      if (mounted) {
        setState(() {
          _error = userFriendlyErrorMessage(e);
          _loading = false;
        });
      }
    }
  }

  static String _mapAlertType(String apiType) {
    switch (apiType.toUpperCase()) {
      case 'AIR':
        return 'air';
      case 'ARTILLERY':
        return 'artillery';
      case 'URBAN_FIGHTS':
        return 'urban';
      case 'CHEMICAL':
      case 'NUCLEAR':
        return 'special';
      case 'UNKNOWN':
      default:
        return 'alarm';
    }
  }

  List<_AlarmRecord> get _filtered {
    if (_selectedFilter == 'all') return _records;
    if (_selectedFilter == 'alarm') {
      return _records.where((r) => ['alarm', 'urban', 'special'].contains(r.type)).toList();
    }
    return _records.where((r) => r.type == _selectedFilter).toList();
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    if (!ProGate.isPro) {
      return Scaffold(
        appBar: AppBar(
          title: Text(
            'Історія тривог',
            style: GoogleFonts.plusJakartaSans(fontWeight: FontWeight.w600),
          ),
          centerTitle: false,
        ),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(32),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 64,
                  height: 64,
                  decoration: BoxDecoration(
                    color: Colors.amber.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: const Icon(Icons.lock_rounded,
                      size: 32, color: Colors.amber),
                ),
                const SizedBox(height: 20),
                Text(
                  'PRO функція',
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                    color: cs.onSurface,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  ProGate.featureDescriptions[ProFeature.alarmHistory] ?? '',
                  textAlign: TextAlign.center,
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 14,
                    color: cs.onSurface.withValues(alpha: 0.6),
                  ),
                ),
                const SizedBox(height: 24),
                FilledButton.icon(
                  onPressed: () => context.push('/premium'),
                  icon: const Icon(Icons.star_rounded),
                  label: const Text('Отримати PRO'),
                ),
              ],
            ),
          ),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(
          'Історія тривог',
          style: GoogleFonts.plusJakartaSans(fontWeight: FontWeight.w600),
        ),
        centerTitle: false,
      ),
      body: Column(
        children: [
          if (_fromCache)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(vertical: 8),
              color: Colors.orange.withValues(alpha: 0.15),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.cloud_off_rounded, size: 18, color: Colors.orange.shade700),
                  const SizedBox(width: 8),
                  Text(
                    'Офлайн. Показуємо останні збережені дані',
                    style: TextStyle(fontSize: 13, color: Colors.orange.shade800),
                  ),
                ],
              ),
            ),
          SizedBox(
            height: 48,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              children: [
                _FilterChip(
                  label: 'Усі',
                  isSelected: _selectedFilter == 'all',
                  onTap: () => setState(() => _selectedFilter = 'all'),
                ),
                _FilterChip(
                  label: 'Повітряна',
                  isSelected: _selectedFilter == 'air',
                  onTap: () => setState(() => _selectedFilter = 'air'),
                ),
                _FilterChip(
                  label: 'Артобстріл',
                  isSelected: _selectedFilter == 'artillery',
                  onTap: () => setState(() => _selectedFilter = 'artillery'),
                ),
                _FilterChip(
                  label: 'Інші',
                  isSelected: _selectedFilter == 'alarm',
                  onTap: () => setState(() => _selectedFilter = 'alarm'),
                ),
              ],
            ),
          ),
          Expanded(
            child: _buildBody(cs),
          ),
        ],
      ),
    );
  }

  Widget _buildBody(ColorScheme cs) {
    if (_loading) {
      return Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: List.generate(
            6,
            (_) => const Padding(
              padding: EdgeInsets.only(bottom: 12),
              child: NeptunShimmer(
                width: double.infinity,
                height: 64,
                borderRadius: 14,
              ),
            ),
          ),
        ),
      );
    }

    if (_error != null) {
      return NeptunErrorState(
        message: 'Помилка завантаження',
        detail: _error,
        onRetry: _loadHistory,
      );
    }

    final items = _filtered;
    if (items.isEmpty) {
      return const NeptunEmptyState(
        icon: Icons.history_rounded,
        title: 'Нема записів',
        subtitle: 'Записи про тривоги з\'являться тут',
      );
    }

    return RefreshIndicator(
      onRefresh: _loadHistory,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: items.length,
        itemBuilder: (context, index) {
          final record = items[index];
          return KeyedSubtree(
            key: ValueKey(
              '${record.region}|${record.timestamp.millisecondsSinceEpoch}|${record.type}|${record.isActive}',
            ),
            child: _AlarmTile(record: record, cs: cs),
          );
        },
      ),
    );
  }
}

class _AlarmRecord {
  final String region;
  final String type;
  final DateTime timestamp;
  final bool isActive;

  _AlarmRecord({
    required this.region,
    required this.type,
    required this.timestamp,
    this.isActive = false,
  });
}

class _AlarmTile extends StatelessWidget {
  final _AlarmRecord record;
  final ColorScheme cs;

  const _AlarmTile({required this.record, required this.cs});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: cs.surfaceContainer,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: record.isActive
              ? cs.error.withValues(alpha: 0.3)
              : cs.outline.withValues(alpha: 0.1),
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: record.isActive
                  ? cs.error.withValues(alpha: 0.1)
                  : cs.secondary.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(
              record.isActive
                  ? Icons.warning_amber_rounded
                  : Icons.check_circle_outline_rounded,
              color: record.isActive ? cs.error : cs.secondary,
              size: 20,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  record.region,
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: cs.onSurface,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  record.isActive ? 'Активна тривога' : 'Відбій',
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 12,
                    color: record.isActive
                        ? cs.error
                        : cs.onSurface.withValues(alpha: 0.5),
                  ),
                ),
              ],
            ),
          ),
          Text(
            '${record.timestamp.hour.toString().padLeft(2, '0')}:${record.timestamp.minute.toString().padLeft(2, '0')}',
            style: GoogleFonts.plusJakartaSans(
              fontSize: 12,
              color: cs.onSurface.withValues(alpha: 0.4),
            ),
          ),
        ],
      ),
    );
  }
}

class _FilterChip extends StatelessWidget {
  final String label;
  final bool isSelected;
  final VoidCallback onTap;

  const _FilterChip({
    required this.label,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: GestureDetector(
        onTap: onTap,
        child: Chip(
          label: Text(
            label,
            style: GoogleFonts.plusJakartaSans(
              fontSize: 13,
              fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
              color: isSelected
                  ? cs.primary
                  : cs.onSurface.withValues(alpha: 0.6),
            ),
          ),
          backgroundColor: isSelected
              ? cs.primary.withValues(alpha: 0.1)
              : Colors.transparent,
          side: BorderSide(
            color: isSelected
                ? cs.primary.withValues(alpha: 0.3)
                : cs.outline.withValues(alpha: 0.3),
          ),
        ),
      ),
    );
  }
}

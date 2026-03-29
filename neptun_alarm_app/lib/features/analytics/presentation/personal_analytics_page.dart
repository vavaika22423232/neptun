import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../core/widgets/neptun_card.dart';
import '../../../core/widgets/neptun_badge.dart';
import '../../../core/pro/pro_features.dart';

class PersonalAnalyticsPage extends StatefulWidget {
  const PersonalAnalyticsPage({super.key});

  @override
  State<PersonalAnalyticsPage> createState() => _PersonalAnalyticsPageState();
}

class _PersonalAnalyticsPageState extends State<PersonalAnalyticsPage> {
  int _totalAlarms = 0;
  int _totalMinutes = 0;
  String _region = '';

  @override
  void initState() {
    super.initState();
    _loadStats();
  }

  Future<void> _loadStats() async {
    final prefs = await SharedPreferences.getInstance();
    if (mounted) {
      final selectedRegions = prefs.getStringList('selected_regions') ?? [];
      final oblasts = selectedRegions
          .where((r) => r.contains('область') || r.contains('місто'))
          .toList();

      String regionLabel;
      if (oblasts.isEmpty) {
        regionLabel =
            prefs.getString('onboarding_region') ?? 'Невизначено';
      } else if (oblasts.length == 1) {
        regionLabel = oblasts.first;
      } else {
        regionLabel = '${oblasts.length} регіонів';
      }

      setState(() {
        _totalAlarms = prefs.getInt('stats_total_alarms') ?? 0;
        _totalMinutes = prefs.getInt('stats_total_minutes') ?? 0;
        _region = regionLabel;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    if (!ProGate.isPro) {
      return Scaffold(
        appBar: AppBar(
          title: Text(
            'Персональна аналітика',
            style: GoogleFonts.inter(fontWeight: FontWeight.w600),
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
                  style: GoogleFonts.inter(
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                    color: cs.onSurface,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  ProGate.featureDescriptions[ProFeature.personalAnalytics] ??
                      '',
                  textAlign: TextAlign.center,
                  style: GoogleFonts.inter(
                    fontSize: 14,
                    color: cs.onSurface.withValues(alpha: 0.6),
                  ),
                ),
                const SizedBox(height: 24),
                FilledButton.icon(
                  onPressed: () =>
                      context.push('/premium'),
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
          'Персональна аналітика',
          style: GoogleFonts.inter(fontWeight: FontWeight.w600),
        ),
        centerTitle: false,
        actions: const [
          Padding(
            padding: EdgeInsets.only(right: 16),
            child: NeptunBadge.pro(),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadStats,
        child: ListView(
          padding: const EdgeInsets.all(16),
          physics: const AlwaysScrollableScrollPhysics(),
          children: [
          if (_totalAlarms == 0 && _totalMinutes == 0)
            Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: NeptunCard(
                child: Row(
                  children: [
                    Container(
                      width: 44,
                      height: 44,
                      decoration: BoxDecoration(
                        color: cs.primary.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Icon(Icons.info_outline_rounded,
                          size: 22, color: cs.primary),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Text(
                        _region == 'Невизначено'
                            ? 'Оберіть регіони сповіщень у вкладці Регіони. Статистика оновлюватиметься під час тривог у ваших регіонах.'
                            : 'Регіон обрано. Статистика почне збиратися при наступній тривозі у ваших регіонах.',
                        style: GoogleFonts.inter(
                          fontSize: 14,
                          color: cs.onSurface.withValues(alpha: 0.8),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          // Region card
          NeptunCard(
            child: Row(
              children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: cs.primary.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(Icons.location_on_rounded,
                      size: 22, color: cs.primary),
                ),
                const SizedBox(width: 14),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Ваш регіон',
                      style: GoogleFonts.inter(
                        fontSize: 12,
                        color: cs.onSurface.withValues(alpha: 0.5),
                      ),
                    ),
                    Text(
                      _region,
                      style: GoogleFonts.inter(
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                        color: cs.onSurface,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),

          // Summary stats
          Row(
            children: [
              Expanded(
                child: _StatCard(
                  icon: Icons.notifications_active_rounded,
                  label: 'Тривог',
                  value: '$_totalAlarms',
                  color: cs.error,
                  cs: cs,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _StatCard(
                  icon: Icons.timer_rounded,
                  label: 'Хвилин',
                  value: '$_totalMinutes',
                  color: cs.primary,
                  cs: cs,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Time in alarm details
          NeptunCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.timer_rounded, size: 20, color: cs.primary),
                    const SizedBox(width: 8),
                    Text(
                      'Час під тривогами',
                      style: GoogleFonts.inter(
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                        color: cs.onSurface,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                _StatRow(
                  label: 'Сьогодні',
                  value: _totalMinutes > 0 ? '${_totalMinutes % 60} хв' : '—',
                ),
                _StatRow(
                  label: 'Цього тижня',
                  value: _totalMinutes > 0 ? '${_totalMinutes ~/ 60} г' : '—',
                ),
                _StatRow(
                  label: 'Цього місяця',
                  value: _totalMinutes > 0 ? '${_totalMinutes ~/ 60} г' : '—',
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Safety score
          NeptunCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.health_and_safety_rounded,
                        size: 20, color: cs.secondary),
                    const SizedBox(width: 8),
                    Text(
                      'Рейтинг безпеки',
                      style: GoogleFonts.inter(
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                        color: cs.onSurface,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Center(
                  child: Column(
                    children: [
                      Text(
                        _totalAlarms > 0
                            ? '${((1 - (_totalAlarms / 100).clamp(0.0, 1.0)) * 100).round()}'
                            : '—',
                        style: GoogleFonts.inter(
                          fontSize: 48,
                          fontWeight: FontWeight.w800,
                          color: cs.secondary,
                        ),
                      ),
                      Text(
                        _totalAlarms > 0
                            ? 'Ваш рейтинг безпеки'
                            : 'Використовуйте додаток для збору статистики',
                        style: GoogleFonts.inter(
                          fontSize: 12,
                          color: cs.onSurface.withValues(alpha: 0.5),
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
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final Color color;
  final ColorScheme cs;

  const _StatCard({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
    required this.cs,
  });

  @override
  Widget build(BuildContext context) {
    return NeptunCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 20, color: color),
          const SizedBox(height: 10),
          Text(
            value,
            style: GoogleFonts.inter(
              fontSize: 28,
              fontWeight: FontWeight.w800,
              color: cs.onSurface,
            ),
          ),
          Text(
            label,
            style: GoogleFonts.inter(
              fontSize: 12,
              color: cs.onSurface.withValues(alpha: 0.5),
            ),
          ),
        ],
      ),
    );
  }
}

class _StatRow extends StatelessWidget {
  final String label;
  final String value;

  const _StatRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: GoogleFonts.inter(
              fontSize: 13,
              color: cs.onSurface.withValues(alpha: 0.6),
            ),
          ),
          Text(
            value,
            style: GoogleFonts.inter(
              fontSize: 14,
              fontWeight: FontWeight.w600,
              color: cs.onSurface,
            ),
          ),
        ],
      ),
    );
  }
}

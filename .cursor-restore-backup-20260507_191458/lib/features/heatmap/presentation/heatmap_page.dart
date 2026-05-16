import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../core/widgets/neptun_card.dart';
import '../../../core/widgets/neptun_shimmer.dart';
import '../../../core/widgets/neptun_badge.dart';
import '../../../core/pro/pro_features.dart';
import '../../../services/region_database.dart';

/// PRO: Heatmap of user's alarms by region (from local stats).
class HeatmapPage extends StatefulWidget {
  const HeatmapPage({super.key});

  @override
  State<HeatmapPage> createState() => _HeatmapPageState();
}

class _HeatmapPageState extends State<HeatmapPage> {
  List<({String region, int count})> _regionCounts = [];
  bool _loading = true;
  bool _hasRegions = false;

  @override
  void initState() {
    super.initState();
    _loadHeatmap();
  }

  Future<void> _loadHeatmap() async {
    final prefs = await SharedPreferences.getInstance();
    if (!mounted) return;

    // Збираємо лічильники з heatmap_count_*
    final counts = <String, int>{};
    for (final key in prefs.getKeys()) {
      if (key.startsWith('heatmap_count_')) {
        final safeKey = key.replaceFirst('heatmap_count_', '');
        final region = safeKey.replaceAll('_', ' ');
        final count = prefs.getInt(key) ?? 0;
        if (count > 0) {
          counts[region] = (counts[region] ?? 0) + count;
        }
      }
    }

    // Збираємо всі обрані регіони (з різних джерел)
    final selectedNames = <String>{};
    selectedNames.addAll(prefs.getStringList('selected_regions') ?? []);

    final regionDb = RegionDatabase()..initialize();
    for (final id in prefs.getStringList('selected_oblast_ids') ?? []) {
      final name = regionDb.getRegionNameById(id);
      if (name != null) selectedNames.add(name);
    }
    for (final id in prefs.getStringList('selected_raion_ids') ?? []) {
      final name = regionDb.getRegionNameById(id);
      if (name != null) selectedNames.add(name);
    }

    final hasRegions = selectedNames.isNotEmpty;

    // Об'єднуємо: обрані регіони + регіони з лічильниками (0 якщо немає)
    final merged = <String, int>{};
    for (final name in selectedNames) {
      merged[name] = counts[name] ?? 0;
    }
    for (final e in counts.entries) {
      merged.putIfAbsent(e.key, () => e.value);
    }

    final list = merged.entries
        .map((e) => (region: e.key, count: e.value))
        .toList()
      ..sort((a, b) => b.count.compareTo(a.count));

    if (mounted) {
      setState(() {
        _regionCounts = list;
        _hasRegions = hasRegions;
        _loading = false;
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
            'Теплова карта',
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
                  child: const Icon(
                    Icons.lock_rounded,
                    size: 32,
                    color: Colors.amber,
                  ),
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
                  ProGate.featureDescriptions[ProFeature.heatmap] ?? '',
                  textAlign: TextAlign.center,
                  style: GoogleFonts.inter(
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
          'Теплова карта тривог',
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
        onRefresh: _loadHeatmap,
        child: _loading
            ? Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  children: List.generate(
                    6,
                    (_) => const Padding(
                      padding: EdgeInsets.only(bottom: 12),
                      child: NeptunShimmer(
                        width: double.infinity,
                        height: 56,
                        borderRadius: 12,
                      ),
                    ),
                  ),
                ),
              )
            : _regionCounts.isEmpty
                ? ListView(
                    padding: const EdgeInsets.all(24),
                    children: [
                      NeptunCard(
                        child: Column(
                          children: [
                            Icon(
                              Icons.whatshot_rounded,
                              size: 48,
                              color: cs.primary.withValues(alpha: 0.5),
                            ),
                            const SizedBox(height: 16),
                            Text(
                              'Поки немає даних',
                              style: GoogleFonts.inter(
                                fontSize: 16,
                                fontWeight: FontWeight.w600,
                                color: cs.onSurface,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              _hasRegions
                                  ? 'Дані з\'являться після відбою тривог у ваших регіонах.'
                                  : 'Додайте регіони у налаштуваннях, щоб отримувати тривоги.',
                              textAlign: TextAlign.center,
                              style: GoogleFonts.inter(
                                fontSize: 14,
                                color: cs.onSurface.withValues(alpha: 0.6),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  )
                : ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: _regionCounts.length,
                    itemBuilder: (context, index) {
                      final item = _regionCounts[index];
                      final maxCount =
                          _regionCounts.isNotEmpty ? _regionCounts.first.count : 1;
                      final intensity = maxCount > 0
                          ? (item.count / maxCount).clamp(0.0, 1.0)
                          : 0.0;
                      final color = Color.lerp(
                        Colors.green.shade400,
                        Colors.red.shade700,
                        intensity,
                      )!;
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: NeptunCard(
                          child: Row(
                            children: [
                              Container(
                                width: 8,
                                height: 48,
                                decoration: BoxDecoration(
                                  color: color,
                                  borderRadius: BorderRadius.circular(4),
                                ),
                              ),
                              const SizedBox(width: 16),
                              Expanded(
                                child: Text(
                                  item.region,
                                  style: GoogleFonts.inter(
                                    fontSize: 15,
                                    fontWeight: FontWeight.w500,
                                    color: cs.onSurface,
                                  ),
                                ),
                              ),
                              Text(
                                '${item.count}',
                                style: GoogleFonts.inter(
                                  fontSize: 16,
                                  fontWeight: FontWeight.w700,
                                  color: color,
                                ),
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
      ),
    );
  }
}

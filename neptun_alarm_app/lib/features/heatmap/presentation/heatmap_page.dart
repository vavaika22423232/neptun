import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../config/prefs_keys.dart';
import '../../../core/widgets/neptun_card.dart';
import '../../../core/widgets/neptun_shimmer.dart';
import '../../../core/widgets/neptun_badge.dart';
import '../../../core/pro/pro_features.dart';
import '../../../services/region_database.dart';
import '../data/heatmap_oblast_state_ids.dart';
import '../data/ukraine_oblast_geo_loader.dart';
import '../logic/heatmap_aggregate.dart';
import 'widgets/alarm_heatmap_map_view.dart';

/// PRO: Heatmap of user's alarms by region (from local stats).
class HeatmapPage extends StatefulWidget {
  const HeatmapPage({super.key});

  @override
  State<HeatmapPage> createState() => _HeatmapPageState();
}

class _HeatmapPageState extends State<HeatmapPage> {
  /// Лічильники по id області для карти (`'1'`…`'27'`).
  Map<String, int> _countsByOblastStateId = {};
  List<({String name, int count})> _oblastRanking = [];
  bool _loading = true;
  bool _hasRegions = false;
  bool _hasAnyMergedRow = false;

  UkraineOblastGeoData? _geoData;
  String? _geoLoadError;

  @override
  void initState() {
    super.initState();
    if (ProGate.isPro) {
      _loadHeatmap();
    } else {
      _loading = false;
    }
  }

  Future<void> _loadHeatmap() async {
    final prefs = await SharedPreferences.getInstance();
    if (!mounted) return;
    if (mounted) {
      setState(() => _geoLoadError = null);
    }

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
    selectedNames.addAll(prefs.getStringList(PrefsKeys.selectedRegions) ?? []);

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

    UkraineOblastGeoData? geo;
    String? geoErr;
    try {
      geo = await UkraineOblastGeoData.load();
    } catch (e, st) {
      geoErr = 'Не вдалося завантажити межі областей';
      assert(() {
        debugPrint('Heatmap geo load: $e\n$st');
        return true;
      }());
    }
    final byState = aggregateHeatmapCountsByStateId(merged, regionDb);
    final ranking = byState.entries
        .where((e) => e.value > 0)
        .map(
          (e) => (
            name: kHeatmapStateIdToShortNameUk[e.key] ?? 'Область ${e.key}',
            count: e.value,
          ),
        )
        .toList()
      ..sort((a, b) => b.count.compareTo(a.count));

    if (mounted) {
      setState(() {
        _geoData = geo;
        _geoLoadError = geoErr;
        _countsByOblastStateId = byState;
        _oblastRanking = ranking;
        _hasRegions = hasRegions;
        _hasAnyMergedRow = merged.isNotEmpty;
        _loading = false;
      });
    }
  }

  String _tileUrl(bool isDark) {
    if (isDark) {
      return 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png';
    }
    return 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}@2x.png';
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    if (!ProGate.isPro) {
      return Scaffold(
        appBar: AppBar(
          title: Text(
            'Теплова карта',
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
                  child: const Icon(
                    Icons.lock_rounded,
                    size: 32,
                    color: Colors.amber,
                  ),
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
                  ProGate.featureDescriptions[ProFeature.heatmap] ?? '',
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
          'Теплова карта тривог',
          style: GoogleFonts.plusJakartaSans(fontWeight: FontWeight.w600),
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
            : !_hasAnyMergedRow
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
                              style: GoogleFonts.plusJakartaSans(
                                fontSize: 16,
                                fontWeight: FontWeight.w600,
                                color: cs.onSurface,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              _hasRegions
                                  ? 'Лічильник оновлюється, коли додаток отримує відбій тривоги по регіону '
                                      '(початок і кінець мають бути зафіксовані трекером). '
                                      'Потягніть вниз, щоб оновити.'
                                  : 'Додайте регіони у налаштуваннях, щоб отримувати тривоги.',
                              textAlign: TextAlign.center,
                              style: GoogleFonts.plusJakartaSans(
                                fontSize: 14,
                                color: cs.onSurface.withValues(alpha: 0.6),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  )
                : CustomScrollView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    slivers: [
                      SliverToBoxAdapter(
                        child: Padding(
                          padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Теплова інтенсивність по областях',
                                style: GoogleFonts.plusJakartaSans(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w600,
                                  color: cs.onSurface.withValues(alpha: 0.7),
                                ),
                              ),
                              const SizedBox(height: 8),
                              SizedBox(
                                height: MediaQuery.sizeOf(context).height * 0.42,
                                child: ClipRRect(
                                  borderRadius: BorderRadius.circular(12),
                                  child: _geoLoadError != null
                                      ? ColoredBox(
                                          color: cs.surfaceContainerHighest
                                              .withValues(alpha: 0.4),
                                          child: Center(
                                            child: Padding(
                                              padding: const EdgeInsets.all(16),
                                              child: Text(
                                                _geoLoadError!,
                                                textAlign: TextAlign.center,
                                                style: GoogleFonts.plusJakartaSans(
                                                  fontSize: 14,
                                                  color: cs.error,
                                                ),
                                              ),
                                            ),
                                          ),
                                        )
                                      : _geoData == null
                                          ? ColoredBox(
                                              color: cs.surfaceContainerHighest
                                                  .withValues(alpha: 0.3),
                                              child: Center(
                                                child: SizedBox(
                                                  width: 28,
                                                  height: 28,
                                                  child: CircularProgressIndicator(
                                                    strokeWidth: 2,
                                                    color: cs.primary,
                                                  ),
                                                ),
                                              ),
                                            )
                                          : AlarmHeatmapMapView(
                                              geo: _geoData!,
                                              countsByOblastStateId:
                                                  _countsByOblastStateId,
                                              isDark: isDark,
                                              tileUrl: _tileUrl(isDark),
                                            ),
                                ),
                              ),
                              const SizedBox(height: 10),
                              Row(
                                children: [
                                  Expanded(
                                    child: Container(
                                      height: 8,
                                      decoration: BoxDecoration(
                                        borderRadius: BorderRadius.circular(4),
                                        gradient: LinearGradient(
                                          colors: [
                                            cs.primary,
                                            cs.tertiary,
                                            cs.error,
                                          ],
                                        ),
                                      ),
                                    ),
                                  ),
                                  const SizedBox(width: 12),
                                  Text(
                                    'менше',
                                    style: GoogleFonts.plusJakartaSans(
                                      fontSize: 11,
                                      color: cs.onSurface.withValues(alpha: 0.5),
                                    ),
                                  ),
                                  Text(
                                    ' → ',
                                    style: GoogleFonts.plusJakartaSans(
                                      fontSize: 11,
                                      color: cs.onSurface.withValues(alpha: 0.35),
                                    ),
                                  ),
                                  Text(
                                    'більше',
                                    style: GoogleFonts.plusJakartaSans(
                                      fontSize: 11,
                                      color: cs.onSurface.withValues(alpha: 0.5),
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ),
                      if (_oblastRanking.isEmpty)
                        SliverToBoxAdapter(
                          child: Padding(
                            padding: const EdgeInsets.fromLTRB(24, 20, 24, 24),
                            child: Text(
                              _hasRegions
                                  ? 'Ще немає завершених тривог для відображення на карті. '
                                      'Після відбою з трекінгом дані з’являться тут.'
                                  : 'Додайте регіони в налаштуваннях.',
                              textAlign: TextAlign.center,
                              style: GoogleFonts.plusJakartaSans(
                                fontSize: 14,
                                color: cs.onSurface.withValues(alpha: 0.55),
                              ),
                            ),
                          ),
                        )
                      else
                        SliverPadding(
                          padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
                          sliver: SliverList.separated(
                            itemCount: _oblastRanking.length,
                            separatorBuilder: (_, _) =>
                                const SizedBox(height: 8),
                            itemBuilder: (context, index) {
                              final item = _oblastRanking[index];
                              final top = _oblastRanking.first.count;
                              final intensity = top > 0
                                  ? (item.count / top).clamp(0.0, 1.0)
                                  : 0.0;
                              final color = Color.lerp(
                                const Color(0xFF22C55E),
                                const Color(0xFFB91C1C),
                                intensity,
                              )!;
                              return KeyedSubtree(
                                key: ValueKey('heatmap_oblast_${item.name}'),
                                child: NeptunCard(
                                  child: Row(
                                    children: [
                                      Container(
                                        width: 8,
                                        height: 44,
                                        decoration: BoxDecoration(
                                          color: color,
                                          borderRadius: BorderRadius.circular(4),
                                        ),
                                      ),
                                      const SizedBox(width: 16),
                                      Expanded(
                                        child: Text(
                                          item.name.startsWith('м.') ||
                                                  item.name == 'АР Крим'
                                              ? item.name
                                              : '${item.name} область',
                                          style: GoogleFonts.plusJakartaSans(
                                            fontSize: 15,
                                            fontWeight: FontWeight.w500,
                                            color: cs.onSurface,
                                          ),
                                        ),
                                      ),
                                      Text(
                                        '${item.count}',
                                        style: GoogleFonts.plusJakartaSans(
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
                    ],
                  ),
      ),
    );
  }
}

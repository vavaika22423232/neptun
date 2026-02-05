// ignore_for_file: deprecated_member_use
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'dart:ui' as ui;
import 'dart:async';
import 'dart:math' as math;
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart' hide Path;
import 'package:shared_preferences/shared_preferences.dart';
import '../data/ukraine_region_paths.dart';
import '../data/ukraine_district_paths.dart';
import '../models/map_models.dart';
import '../services/map_data_service.dart';
import '../utils/svg_path_parser.dart';
import '../services/ballistic_alert_service.dart';
import '../services/widget_service.dart';
import '../services/threat_icon_manager.dart';
import '../theme/map_colors.dart';

// Для сумісності залишаємо старий клас
class NeptunColors {
  static const Color bgDark = Color(0xFF141414);
  static const Color bgGradientMid = Color(0xFF1F1F1F);
  static const Color bgGradientEnd = Color(0xFF1F1F1F);
  static const Color normalFill = Color(0xFF262626);
  static const Color normalStroke = Color(0xFF525252);
  static const Color alarmFillState = Color(0xFF991B1B);
  static const Color alarmStrokeState = Color(0xFFB45555);
  static const Color districtNormalFill = Colors.transparent;
  static const Color districtNormalStroke = Color(0x263B82F6);
  static const Color districtAlarmFill = Color(0xFFDC2626);
  static const Color districtAlarmStroke = Color(0xFFF87171);
  static const Color alarmActive = Color(0xFFDC2626);
  static const Color borderDark = Color(0xFF454545);
  static const Color textWhite = Colors.white;
  static const Color textGray = Color(0xFFA3A3A3);
  static const Color textCyan = Color(0xFF3B82F6);
}

// ===== ГОЛОВНА СТОРІНКА КАРТИ =====
class NativeMapPage extends StatefulWidget {
  const NativeMapPage({super.key});

  @override
  State<NativeMapPage> createState() => _NativeMapPageState();
}

class _NativeMapPageState extends State<NativeMapPage> with TickerProviderStateMixin, WidgetsBindingObserver {
  // Стан тривог
  Map<String, bool> stateAlarms = {}; // Області (oblasts)
  Map<String, bool> districtAlarms = {}; // Райони
  Map<String, String> stateThreatTypes = {}; // Тип загрози по області (для іконок)
  
  // Маркери загроз
  List<ThreatMarker> threatMarkers = [];
  Map<String, int> markerCounts = {};
  
  // Стан UI
  bool isLoading = true;
  String? error;
  DateTime? lastUpdate;
  int stateAlarmCount = 0;
  int districtAlarmCount = 0;
  
  // Балістична загроза
  bool _ballisticThreatActive = false;
  bool _ballisticAllClear = false;
  String _ballisticMessage = '';
  Timer? _ballisticTimer;
  Set<String> _previousBallisticRegions = {}; // Для відстеження нових загроз
  
  // Таймери оновлення
  Timer? _alarmTimer;
  Timer? _markerTimer;
  bool _alarmsFetching = false;
  bool _markersFetching = false;
  final MapDataService _mapDataService = MapDataService();
  
  // Інтервали оновлення (зменшено для швидшого оновлення)
  static const int alarmUpdateInterval = 5; // секунд
  static const int markerUpdateInterval = 5; // секунд
  static const int timeRange = 15; // хвилин для маркерів

  // Threat history (for tracker)
  final List<ThreatHistoryEntry> _threatHistory = [];
  DateTime? _lastHistoryEntryAt;
  static const Duration _historyMinInterval = Duration(minutes: 1);

  // Operator mode (advanced controls)
  bool _operatorModeEnabled = false;
  
  // Parsed paths cache
  final Map<String, List<Path>> _statePathsCache = {};
  final Map<String, List<Path>> _districtPathsCache = {};
  
  // Zoom/pan - now using flutter_map
  final MapController _mapController = MapController();
  double _currentZoom = 6.0;
  
  // Hybrid map: SVG fades at high zoom, tiles appear
  static const double _svgFadeStartZoom = 8.0;
  static const double _svgFadeEndZoom = 10.0;
  
  // Legacy transform controller (for compatibility)
  final TransformationController _transformController = TransformationController();
  
  // Анімація пульсації тривоги
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;
  
  // Анімація балістичної загрози (для автозакриття)
  late AnimationController _ballisticController;
  
  // Анімація відбою балістики
  late AnimationController _allClearController;
  late Animation<double> _allClearAnimation;
  
  // SVG opacity based on zoom
  double get _svgOpacity {
    if (_currentZoom < _svgFadeStartZoom) return 1.0;
    if (_currentZoom >= _svgFadeEndZoom) return 0.0;
    return 1.0 - ((_currentZoom - _svgFadeStartZoom) / (_svgFadeEndZoom - _svgFadeStartZoom));
  }
  
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    
    // Завантаження іконок загроз
    ThreatIconManager().loadIcons().then((_) {
      debugPrint('✅ Icons loaded: ${ThreatIconManager().isLoaded}');
      if (mounted) setState(() {});
    });
    
    // Підписуємося на глобальний сервіс балістичних тривог
    BallisticAlertService().onBallisticThreat(_handleGlobalBallisticThreat);
    BallisticAlertService().onBallisticAllClear(_handleGlobalBallisticAllClear);
    
    // Анімація пульсації (уповільнена для продуктивності)
    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 2000), // було 1500
      vsync: this,
    )..repeat(reverse: true);
    
    _pulseAnimation = Tween<double>(begin: 0.92, end: 1.0).animate( // зменшено амплітуду
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );
    
    // Анімація балістичної загрози (мінімальна)
    _ballisticController = AnimationController(
      duration: const Duration(milliseconds: 300),
      vsync: this,
    );
    
    // Анімація відбою
    _allClearController = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    );
    
    _allClearAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _allClearController, curve: Curves.easeOut),
    );
    
    _parseAllPaths();
    _loadOperatorMode();
    _fetchAlarms();
    _fetchThreatMarkers();
    
    // Періодичне оновлення
    _alarmTimer = Timer.periodic(
      Duration(seconds: alarmUpdateInterval),
      (_) => _fetchAlarms(),
    );
    _markerTimer = Timer.periodic(
      Duration(seconds: markerUpdateInterval),
      (_) => _fetchThreatMarkers(),
    );
  }

  Future<void> _loadOperatorMode() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final enabled = prefs.getBool('operator_mode_enabled') ?? false;
      if (mounted) {
        setState(() => _operatorModeEnabled = enabled);
      }
    } catch (_) {}
  }

  Future<void> _toggleOperatorMode() async {
    final newValue = !_operatorModeEnabled;
    setState(() => _operatorModeEnabled = newValue);
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool('operator_mode_enabled', newValue);
    } catch (_) {}
  }
  
  void _handleGlobalBallisticThreat(String? region) {
    showBallisticThreat(region: region);
  }
  
  void _handleGlobalBallisticAllClear(String? region) {
    showBallisticAllClear(region: region);
  }
  
  @override
  void dispose() {
    _alarmTimer?.cancel();
    _markerTimer?.cancel();
    _ballisticTimer?.cancel();
    _pulseController.dispose();
    _ballisticController.dispose();
    _allClearController.dispose();
    _transformController.dispose();
    _mapController.dispose();
    
    // Відписуємося від глобального сервісу
    BallisticAlertService().removeCallback(_handleGlobalBallisticThreat);
    BallisticAlertService().removeCallback(_handleGlobalBallisticAllClear);
    WidgetsBinding.instance.removeObserver(this);
    
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused || state == AppLifecycleState.inactive) {
      _alarmTimer?.cancel();
      _markerTimer?.cancel();
      return;
    }
    if (state == AppLifecycleState.resumed) {
      _alarmTimer?.cancel();
      _markerTimer?.cancel();
      _alarmTimer = Timer.periodic(
        Duration(seconds: alarmUpdateInterval),
        (_) => _fetchAlarms(),
      );
      _markerTimer = Timer.periodic(
        Duration(seconds: markerUpdateInterval),
        (_) => _fetchThreatMarkers(),
      );
      _fetchAlarms();
      _fetchThreatMarkers();
    }
  }
  
  // ===== BALLISTIC THREAT ALERT SYSTEM =====
  void showBallisticThreat({String? region}) {
    if (!mounted) return;
    
    debugPrint('🚀 showBallisticThreat called with region: $region');
    
    setState(() {
      _ballisticThreatActive = true;
      _ballisticAllClear = false;
      _ballisticMessage = region != null 
          ? 'Загроза балістики!\n$region' 
          : 'Загроза балістики!';
    });
    
    // Запускаємо анімацію з реверсом для пульсації
    _ballisticController.repeat(reverse: true);
    
    debugPrint('🚀 Animation started, _ballisticThreatActive = $_ballisticThreatActive');
    
    // Вібрація (якщо доступна)
    HapticFeedback.heavyImpact();
    
    // НЕ приховуємо автоматично - тільки при "Відбій загрози балістики!"
    _ballisticTimer?.cancel();
  }
  
  void showBallisticAllClear({String? region}) {
    if (!mounted) return;
    
    debugPrint('✅ showBallisticAllClear called with region: $region');
    
    // Зупиняємо загрозу якщо активна
    _ballisticController.stop();
    _ballisticController.reset();
    _ballisticTimer?.cancel();
    
    setState(() {
      _ballisticThreatActive = false;
      _ballisticAllClear = true;
      _ballisticMessage = region != null 
          ? 'Відбій загрози балістики!\n$region' 
          : 'Відбій загрози балістики!';
    });
    
    // Запускаємо анімацію відбою
    _allClearController.forward(from: 0.0);
    
    // М'яка вібрація
    HapticFeedback.mediumImpact();
    
    // Автоматично приховуємо через 5 секунд
    _ballisticTimer = Timer(const Duration(seconds: 5), () {
      if (mounted) {
        setState(() => _ballisticAllClear = false);
        debugPrint('✅ All clear auto-hidden');
      }
    });
  }
  
  // Публічний метод для тестування (можна викликати з зовні)
  void triggerBallisticDemo() {
    showBallisticThreat(region: 'Київська область');
    
    // Показуємо відбій через 5 секунд
    Timer(const Duration(seconds: 5), () {
      showBallisticAllClear(region: 'Київська область');
    });
  }
  
  void _parseAllPaths() {
    // Parse state (oblast) paths
    for (final entry in UkraineRegionPaths.regionPaths.entries) {
      final regionId = entry.key;
      final pathStrings = entry.value;
      final paths = <Path>[];
      
      for (final pathData in pathStrings) {
        try {
          final path = SvgPathParser.parsePath(pathData);
          paths.add(path);
        } catch (e) {
          debugPrint('Error parsing state path for region $regionId: $e');
        }
      }
      
      _statePathsCache[regionId] = paths;
    }
    debugPrint('Parsed ${_statePathsCache.length} state regions');
    
    // Parse district paths
    for (final entry in UkraineDistrictPaths.districtPaths.entries) {
      final districtId = entry.key;
      final pathStrings = entry.value;
      final paths = <Path>[];
      
      for (final pathData in pathStrings) {
        try {
          final path = SvgPathParser.parsePath(pathData);
          paths.add(path);
        } catch (e) {
          debugPrint('Error parsing district path for $districtId: $e');
        }
      }
      
      _districtPathsCache[districtId] = paths;
    }
    debugPrint('Parsed ${_districtPathsCache.length} district regions');
  }
  
  // ===== FETCH ALARMS (як fetchAlarms в index_map.html) =====
  Future<void> _fetchAlarms() async {
    if (_alarmsFetching) return;
    _alarmsFetching = true;
    try {
      final alarmData = await _mapDataService.fetchAlarms();

      // Перевіряємо чи дані змінились
      bool alarmsChanged =
          alarmData.stateAlarms.length != stateAlarms.length ||
              alarmData.districtAlarms.length != districtAlarms.length ||
              alarmData.stateCount != stateAlarmCount ||
              alarmData.districtCount != districtAlarmCount;

      if (!alarmsChanged) {
        for (final key in alarmData.stateAlarms.keys) {
          if (stateAlarms[key] != alarmData.stateAlarms[key]) {
            alarmsChanged = true;
            break;
          }
        }
      }

      if (alarmsChanged || isLoading) {
        final newBallisticRegions =
            alarmData.ballisticRegions.difference(_previousBallisticRegions);
        final clearedBallisticRegions =
            _previousBallisticRegions.difference(alarmData.ballisticRegions);

        if (newBallisticRegions.isNotEmpty && !isLoading) {
          final regionsText = newBallisticRegions.join(', ');
          showBallisticThreat(region: regionsText);
        }

        if (clearedBallisticRegions.isNotEmpty &&
            alarmData.ballisticRegions.isEmpty &&
            !isLoading) {
          final regionsText = clearedBallisticRegions.join(', ');
          showBallisticAllClear(region: regionsText);
        }

        _previousBallisticRegions = alarmData.ballisticRegions;

        if (mounted) {
          setState(() {
            stateAlarms = alarmData.stateAlarms;
            districtAlarms = alarmData.districtAlarms;
            stateThreatTypes = alarmData.stateThreatTypes;
            stateAlarmCount = alarmData.stateCount;
            districtAlarmCount = alarmData.districtCount;
            lastUpdate = DateTime.now();
            isLoading = false;
            error = null;
          });
        }
        debugPrint(
            'Alarms updated: ${alarmData.stateCount} oblasts, ${alarmData.districtCount} districts');
        if (alarmData.ballisticRegions.isNotEmpty) {
          debugPrint('🚀 Ballistic threats active in: ${alarmData.ballisticRegions}');
        }

        _updateHomeWidget(alarmData.stateCount > 0, alarmData.stateCount);
      } else {
        debugPrint('Alarms unchanged, skipping setState');
      }
    } catch (e) {
      debugPrint('Error fetching alarms: $e');
      if (mounted && lastUpdate == null) {
        setState(() {
          error = 'Не вдалося завантажити дані';
          isLoading = false;
        });
      }
    } finally {
      _alarmsFetching = false;
    }
  }
  
  /// Оновлення віджета на робочому столі
  void _updateHomeWidget(bool hasAlarm, int alarmsCount) {
    try {
      // Отримуємо збережений регіон користувача
      WidgetService().getUserRegion().then((userRegion) {
        final region = userRegion ?? 'Україна';
        
        WidgetService().updateWidget(
          region: region,
          isAlarm: hasAlarm,
          threatsCount: alarmsCount,
          timerMinutes: 0, // Таймер буде оновлюватись окремо
        );
      });
    } catch (e) {
      debugPrint('Widget update error: $e');
    }
  }
  
  // ===== FETCH THREAT MARKERS (як fetchThreatMarkers в index_map.html) =====
  Future<void> _fetchThreatMarkers() async {
    if (_markersFetching) return;
    _markersFetching = true;
    try {
      final markerData =
          await _mapDataService.fetchThreatMarkers(timeRange: timeRange);

      if (markerData.ballisticActive != null) {
        debugPrint(
            '🚀 Ballistic threat from API: active=${markerData.ballisticActive}, region=${markerData.ballisticRegion}');
        if (markerData.ballisticActive == true &&
            !BallisticAlertService().isBallisticThreatActive) {
          BallisticAlertService()
              .triggerBallisticThreat(region: markerData.ballisticRegion);
        } else if (markerData.ballisticActive == false &&
            BallisticAlertService().isBallisticThreatActive) {
          BallisticAlertService()
              .triggerBallisticAllClear(region: markerData.ballisticRegion);
        }
      }

      debugPrint('📊 Received ${markerData.markers.length} markers from API:');
      for (final marker in markerData.markers) {
        String trajInfo = '';
        if (marker.hasAITrajectory) {
          final t = marker.trajectory!;
          trajInfo =
              ' [AI TRAJ: ${t.sourceName} → ${t.targetName}${t.predicted ? " (прогноз)" : ""}]';
        }
        debugPrint('  📍 type="${marker.threatType}", place="${marker.place}"$trajInfo');
      }

      final trajCount =
          markerData.markers.where((m) => m.hasAITrajectory).length;
      if (trajCount > 0) {
        debugPrint('🎯 $trajCount markers have AI trajectories');
      }

      bool markersChanged = markerData.markers.length != threatMarkers.length ||
          markerData.counts.length != markerCounts.length;

      if (!markersChanged) {
        for (final entry in markerData.counts.entries) {
          if (markerCounts[entry.key] != entry.value) {
            markersChanged = true;
            break;
          }
        }
      }

      if (markersChanged) {
        if (mounted) {
          setState(() {
            threatMarkers = markerData.markers;
            markerCounts = markerData.counts;
          });
        }
        _addThreatHistoryEntry(markerData.counts);
        debugPrint('Markers updated: ${markerData.markers.length} threat markers');
      } else {
        debugPrint('Markers unchanged, skipping setState');
      }
    } catch (e) {
      debugPrint('Error fetching threat markers: $e');
    } finally {
      _markersFetching = false;
    }
  }

  void _addThreatHistoryEntry(Map<String, int> counts) {
    final now = DateTime.now();
    if (_lastHistoryEntryAt != null &&
        now.difference(_lastHistoryEntryAt!) < _historyMinInterval) {
      return;
    }
    _lastHistoryEntryAt = now;
    _threatHistory.add(ThreatHistoryEntry(
      timestamp: now,
      counts: Map<String, int>.from(counts),
    ));
    if (_threatHistory.length > 12) {
      _threatHistory.removeAt(0);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final colors = MapColors(isDark: isDark);
    
    return Scaffold(
      backgroundColor: colors.bgMain,
      body: Stack(
        children: [
          // Фон з градієнтом
          Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  colors.bgMain,
                  colors.bgGradientMid,
                  colors.bgGradientEnd,
                ],
              ),
            ),
          ),
          
          // Карта
          SafeArea(
            child: Column(
              children: [
                // Карта з zoom/pan
                Expanded(
                  child: isLoading
                      ? Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              CircularProgressIndicator(color: colors.textAccent),
                              const SizedBox(height: 16),
                              Text('Завантаження карти...',
                                  style: TextStyle(color: colors.textSecondary)),
                            ],
                          ),
                        )
                      : error != null && lastUpdate == null
                          ? _buildError(colors)
                          : _buildMap(colors),
                ),
              ],
            ),
          ),
          
          // ===== BALLISTIC THREAT OVERLAY =====
          if (_ballisticThreatActive)
            _buildBallisticThreatOverlay(colors),
          
          // ===== ALL CLEAR OVERLAY =====
          if (_ballisticAllClear)
            AnimatedBuilder(
              animation: _allClearController,
              builder: (context, child) => _buildAllClearOverlay(colors),
            ),
          
          // Legend (внизу по центру)
          Positioned(
            bottom: 24,
            left: 0,
            right: 0,
            child: _buildLegend(colors),
          ),
          
          // ===== THREAT STATS WIDGET =====
          // Опускаємо нижче якщо активний банер балістики або відбою
          if (markerCounts.isNotEmpty)
            Positioned(
              top: MediaQuery.of(context).padding.top + 
                   ((_ballisticThreatActive || _allClearController.value > 0) ? 80 : 8),
              right: 12,
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 300),
                curve: Curves.easeOut,
                child: _buildThreatStats(colors),
              ),
            ),

          // ===== OPERATOR MODE TOGGLE + PANEL =====
          Positioned(
            top: MediaQuery.of(context).padding.top + 8,
            left: 12,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildOperatorToggle(colors),
                if (_operatorModeEnabled) ...[
                  const SizedBox(height: 8),
                  _buildOperatorPanel(colors),
                ],
              ],
            ),
          ),

        ],
      ),
    );
  }

  Widget _buildOperatorToggle(MapColors colors) {
    return GestureDetector(
      onTap: _toggleOperatorMode,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: colors.panelBg,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: colors.panelBorder),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.1),
              blurRadius: 6,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.settings,
              size: 16,
              color: _operatorModeEnabled ? colors.textAccent : colors.textSecondary,
            ),
            const SizedBox(width: 6),
            Text(
              _operatorModeEnabled ? 'OP' : 'OP',
              style: TextStyle(
                color: _operatorModeEnabled ? colors.textAccent : colors.textSecondary,
                fontSize: 11,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildOperatorPanel(MapColors colors) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: colors.panelBg,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: colors.panelBorder),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 6,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          IconButton(
            visualDensity: VisualDensity.compact,
            icon: Icon(Icons.refresh, size: 18, color: colors.textAccent),
            onPressed: () {
              _fetchAlarms();
              _fetchThreatMarkers();
            },
          ),
          IconButton(
            visualDensity: VisualDensity.compact,
            icon: Icon(Icons.my_location, size: 18, color: colors.textAccent),
            onPressed: () {
              _mapController.move(const LatLng(48.5, 31.5), 6.0);
            },
          ),
          IconButton(
            visualDensity: VisualDensity.compact,
            icon: Icon(Icons.history, size: 18, color: colors.textAccent),
            onPressed: () => _showThreatStatsDialog(colors),
          ),
        ],
      ),
    );
  }
  
  // ===== BALLISTIC THREAT VISUAL EFFECT =====
  Widget _buildBallisticThreatOverlay(MapColors colors) {
    return Stack(
      children: [
        // Мінімалістичне повідомлення зверху
        Positioned(
          top: MediaQuery.of(context).padding.top + 12,
          left: 16,
          right: 16,
          child: Center(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
              decoration: BoxDecoration(
                color: const Color(0xFFDC2626),
                borderRadius: BorderRadius.circular(14),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.15),
                    blurRadius: 10,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(
                    Icons.rocket_launch_rounded,
                    color: Colors.white,
                    size: 22,
                  ),
                  const SizedBox(width: 12),
                  Flexible(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Загроза балістики',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 15,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const Padding(
                          padding: EdgeInsets.only(top: 2),
                          child: Text(
                            'де зараз повітряна тривога',
                            style: TextStyle(
                              color: Colors.white70,
                              fontSize: 13,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  GestureDetector(
                    onTap: () {
                      _ballisticController.stop();
                      _ballisticController.reset();
                      _ballisticTimer?.cancel();
                      setState(() => _ballisticThreatActive = false);
                    },
                    child: Icon(
                      Icons.close_rounded,
                      color: Colors.white.withOpacity(0.8),
                      size: 20,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
  
  // ===== ALL CLEAR VISUAL EFFECT =====
  Widget _buildAllClearOverlay(MapColors colors) {
    final progress = _allClearAnimation.value;
    
    return Stack(
      children: [
        // Мінімалістичне повідомлення зверху
        Positioned(
          top: MediaQuery.of(context).padding.top + 12,
          left: 16,
          right: 16,
          child: Center(
            child: AnimatedOpacity(
              opacity: progress < 0.7 ? 1.0 : (1.0 - (progress - 0.7) * 3.3),
              duration: const Duration(milliseconds: 200),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                decoration: BoxDecoration(
                  color: const Color(0xFF16A34A),
                  borderRadius: BorderRadius.circular(14),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.15),
                      blurRadius: 10,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(
                      Icons.check_circle_rounded,
                      color: Colors.white,
                      size: 22,
                    ),
                    const SizedBox(width: 12),
                    Flexible(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Відбій балістики',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 15,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          if (_ballisticMessage.contains('\n'))
                            Padding(
                              padding: const EdgeInsets.only(top: 2),
                              child: Text(
                                _ballisticMessage.split('\n').last,
                                style: TextStyle(
                                  color: Colors.white.withOpacity(0.85),
                                  fontSize: 13,
                                ),
                              ),
                            ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
  
  Widget _buildLegend(MapColors colors) {
    return Center(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        decoration: BoxDecoration(
          color: colors.panelBg,
          border: Border.all(color: colors.panelBorder),
          borderRadius: BorderRadius.circular(12),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.1),
              blurRadius: 6,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            _legendItem(colors.normalFill, 'Немає тривоги', colors),
            const SizedBox(width: 24),
            _legendItem(colors.alarmFillState, 'Тривога', colors),
          ],
        ),
      ),
    );
  }
  
  // ===== THREAT STATS PANEL =====
  Widget _buildThreatStats(MapColors colors) {
    // Групуємо типи загроз для кращого відображення
    final groupedCounts = <String, int>{};
    
    for (final entry in markerCounts.entries) {
      final type = entry.key;
      final count = entry.value;
      
      // Групуємо схожі типи
      if (type == 'shahed' || type == 'fpv') {
        groupedCounts['shahed'] = (groupedCounts['shahed'] ?? 0) + count;
      } else if (type == 'raketa' || type == 'pusk') {
        groupedCounts['raketa'] = (groupedCounts['raketa'] ?? 0) + count;
      } else if (type == 'kab' || type == 'rszv') {
        groupedCounts['kab'] = (groupedCounts['kab'] ?? 0) + count;
      } else if (type == 'rozved') {
        groupedCounts['rozved'] = (groupedCounts['rozved'] ?? 0) + count;
      } else if (type == 'avia') {
        groupedCounts['avia'] = (groupedCounts['avia'] ?? 0) + count;
      }
    }
    
    // Сортуємо за кількістю (найбільше спочатку)
    final sortedEntries = groupedCounts.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    
    // Якщо немає загроз
    if (sortedEntries.isEmpty) return const SizedBox.shrink();
    
    // Загальна кількість
    final total = sortedEntries.fold<int>(0, (sum, e) => sum + e.value);
    
    return GestureDetector(
      onTap: () => _showThreatStatsDialog(colors),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        decoration: BoxDecoration(
          color: colors.panelBg,
          border: Border.all(color: colors.panelBorder),
          borderRadius: BorderRadius.circular(12),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.15),
              blurRadius: 8,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            // Заголовок
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.flight_rounded,
                  size: 14,
                  color: Colors.orange,
                ),
                const SizedBox(width: 4),
                Text(
                  'Загрози ($total)',
                  style: TextStyle(
                    color: colors.textPrimary,
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            // Список загроз (максимум 4)
            ...sortedEntries.take(4).map((entry) => _buildThreatStatItem(
              entry.key,
              entry.value,
              colors,
            )),
          ],
        ),
      ),
    );
  }
  
  Widget _buildThreatStatItem(String type, int count, MapColors colors) {
    final icon = _getThreatEmoji(type);
    final label = _getThreatLabel(type);
    final color = _getThreatColor(type);
    
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            icon,
            style: const TextStyle(fontSize: 12),
          ),
          const SizedBox(width: 4),
          Text(
            '$count',
            style: TextStyle(
              color: color,
              fontSize: 12,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(width: 4),
          Text(
            label,
            style: TextStyle(
              color: colors.textSecondary,
              fontSize: 10,
            ),
          ),
        ],
      ),
    );
  }
  
  String _getThreatEmoji(String type) {
    switch (type) {
      case 'shahed': return '🛩️';
      case 'raketa': return '🚀';
      case 'kab': return '💣';
      case 'rozved': return '🔍';
      case 'avia': return '✈️';
      default: return '⚠️';
    }
  }
  
  String _getThreatLabel(String type) {
    switch (type) {
      case 'shahed': return 'БПЛА';
      case 'raketa': return 'Ракети';
      case 'kab': return 'КАБи';
      case 'rozved': return 'Розвідники';
      case 'avia': return 'Авіація';
      default: return 'Інше';
    }
  }
  
  Color _getThreatColor(String type) {
    switch (type) {
      case 'shahed': return Colors.orange;
      case 'raketa': return Colors.red;
      case 'kab': return Colors.redAccent;
      case 'rozved': return Colors.amber;
      case 'avia': return Colors.purple;
      default: return Colors.white;
    }
  }
  
  void _showThreatStatsDialog(MapColors colors) {
    final total = markerCounts.values.fold<int>(0, (sum, v) => sum + v);
    
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: colors.panelBg,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Row(
          children: [
            const Text('🎯', style: TextStyle(fontSize: 24)),
            const SizedBox(width: 8),
            Text(
              'Статистика загроз',
              style: TextStyle(
                color: colors.textPrimary,
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: colors.isDark 
                    ? Colors.orange.withOpacity(0.1)
                    : Colors.orange.withOpacity(0.05),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.orange.withOpacity(0.3)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.info_outline, color: Colors.orange, size: 18),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Орієнтовно за останні $timeRange хв',
                      style: TextStyle(
                        color: colors.textSecondary,
                        fontSize: 12,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            // Загальна кількість
            Center(
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      Colors.red.withOpacity(0.2),
                      Colors.orange.withOpacity(0.2),
                    ],
                  ),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Column(
                  children: [
                    Text(
                      '$total',
                      style: TextStyle(
                        color: colors.textPrimary,
                        fontSize: 36,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    Text(
                      'об\'єктів у повітрі',
                      style: TextStyle(
                        color: colors.textSecondary,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            // Деталізація
            ...markerCounts.entries.map((entry) {
              final icon = _getThreatEmoji(entry.key);
              final name = ThreatType.names[entry.key] ?? entry.key;
              final color = _getThreatColor(entry.key);
              
              return Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Row(
                  children: [
                    Text(icon, style: const TextStyle(fontSize: 18)),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        name,
                        style: TextStyle(
                          color: colors.textPrimary,
                          fontSize: 14,
                        ),
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: color.withOpacity(0.2),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        '${entry.value}',
                        style: TextStyle(
                          color: color,
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ],
                ),
              );
            }),
            if (_threatHistory.isNotEmpty) ...[
              const SizedBox(height: 16),
              Text(
                'Історія (останні інтервали)',
                style: TextStyle(
                  color: colors.textPrimary,
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 8),
              ..._threatHistory.reversed.take(6).map((entry) {
                final time =
                    '${entry.timestamp.hour.toString().padLeft(2, '0')}:${entry.timestamp.minute.toString().padLeft(2, '0')}';
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 2),
                  child: Row(
                    children: [
                      Text(
                        time,
                        style: TextStyle(
                          color: colors.textSecondary,
                          fontSize: 12,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: LinearProgressIndicator(
                          value: (entry.total / (total == 0 ? 1 : total))
                              .clamp(0.0, 1.0),
                          minHeight: 6,
                          backgroundColor: colors.panelBorder,
                          valueColor: AlwaysStoppedAnimation<Color>(
                            colors.textAccent.withOpacity(0.6),
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        '${entry.total}',
                        style: TextStyle(
                          color: colors.textPrimary,
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                );
              }),
            ],
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text(
              'Закрити',
              style: TextStyle(color: colors.textAccent),
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _legendItem(Color color, String label, MapColors colors) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 16,
          height: 16,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(4),
            border: Border.all(color: colors.panelBorder),
          ),
        ),
        const SizedBox(width: 8),
        Text(label, style: TextStyle(color: colors.textSecondary, fontSize: 12)),
      ],
    );
  }
  
  Widget _buildError(MapColors colors) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.error_outline, color: Colors.red, size: 48),
          const SizedBox(height: 16),
          Text(error!, style: TextStyle(color: colors.textSecondary)),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: () {
              setState(() => isLoading = true);
              _fetchAlarms();
              _fetchThreatMarkers();
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: colors.textAccent,
            ),
            child: const Text('Спробувати знову'),
          ),
        ],
      ),
    );
  }
  
  /// Get tile URL for the current theme
  /// Using free tile providers
  String _getTileUrl(bool isDark) {
    if (isDark) {
      // CartoDB Dark Matter - dark theme (free, no API key)
      return 'https://cartodb-basemaps-{s}.global.ssl.fastly.net/dark_all/{z}/{x}/{y}.png';
    } else {
      // CartoDB Voyager - light theme with local labels (free, no API key)
      return 'https://cartodb-basemaps-{s}.global.ssl.fastly.net/rastertiles/voyager/{z}/{x}/{y}.png';
    }
  }
  
  Widget _buildMap(MapColors colors) {
    final isDark = colors.isDark;
    
    return FlutterMap(
      mapController: _mapController,
      options: MapOptions(
        initialCenter: const LatLng(48.5, 31.5), // Center of Ukraine
        initialZoom: 6.0,
        initialRotation: 0.0, // Force no rotation
        minZoom: 4.0,
        maxZoom: 18.0,
        backgroundColor: colors.bgMain,
        interactionOptions: InteractionOptions(
          flags: InteractiveFlag.drag | InteractiveFlag.pinchZoom | InteractiveFlag.doubleTapZoom,
          enableMultiFingerGestureRace: false,
          rotationThreshold: 999999.0, // Effectively disable rotation
          cursorKeyboardRotationOptions: CursorKeyboardRotationOptions.disabled(),
        ),
        // Use containCenter instead of contain to avoid assertion errors
        cameraConstraint: CameraConstraint.containCenter(
          bounds: LatLngBounds(
            const LatLng(44.0, 20.0),  // SW
            const LatLng(53.0, 42.0),  // NE
          ),
        ),
        onPositionChanged: (position, hasGesture) {
          if ((position.zoom - _currentZoom).abs() > 0.1) {
            setState(() {
              _currentZoom = position.zoom;
            });
          }
        },
        onMapEvent: (event) {
          // Immediately reset rotation on any rotation event
          if (event is MapEventRotate || event is MapEventRotateStart || event is MapEventRotateEnd) {
            _mapController.rotate(0);
          }
        },
      ),
      children: [
        // Map tiles (CartoDB - free, no API key needed)
        TileLayer(
          urlTemplate: _getTileUrl(isDark),
          subdomains: const ['a', 'b', 'c', 'd'],
          userAgentPackageName: 'com.neptun.alarm',
          maxZoom: 18,
        ),
        // Custom SVG overlay using MobileLayerTransformer
        if (_svgOpacity > 0)
          _SvgMapLayer(
            statePathsCache: _statePathsCache,
            districtPathsCache: _districtPathsCache,
            stateAlarms: stateAlarms,
            districtAlarms: districtAlarms,
            stateThreatTypes: stateThreatTypes,
            threatMarkers: threatMarkers,
            pulseValue: _pulseAnimation.value,
            mapColors: colors,
            opacity: _svgOpacity,
            onMarkerTap: _showMarkerInfo,
          ),
        // Labels and markers layer - always visible regardless of SVG opacity
        _LabelsMarkersLayer(
          threatMarkers: threatMarkers,
          mapColors: colors,
          onMarkerTap: _showMarkerInfo,
        ),
      ],
    );
  }
  
  void _showMarkerInfo(ThreatMarker marker) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final color = ThreatType.getColor(marker.threatType);
    final threatName = ThreatType.names[marker.threatType] ?? marker.threatType;
    
    showModalBottomSheet(
      context: context,
      backgroundColor: isDark ? const Color(0xFF1E1E1E) : Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header with threat type
              Row(
                children: [
                  Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      color: color.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(
                      _getThreatIcon(marker.threatType),
                      color: color,
                      size: 28,
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          threatName,
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                            color: isDark ? Colors.white : Colors.black87,
                          ),
                        ),
                        if (marker.date.isNotEmpty)
                          Text(
                            marker.date,
                            style: TextStyle(
                              fontSize: 14,
                              color: isDark ? Colors.grey[400] : Colors.grey[600],
                            ),
                          ),
                      ],
                    ),
                  ),
                ],
              ),
              
              const SizedBox(height: 16),
              
              // Location
              if (marker.place.isNotEmpty) ...[
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: isDark ? Colors.grey[850] : Colors.grey[100],
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        Icons.location_on_rounded,
                        color: color,
                        size: 22,
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          marker.place,
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w500,
                            color: isDark ? Colors.white : Colors.black87,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
              ],
              
              const SizedBox(height: 8),
            ],
          ),
        ),
      ),
    );
  }
  
  IconData _getThreatIcon(String threatType) {
    switch (threatType) {
      case 'shahed':
        return Icons.air_rounded;
      case 'raketa':
        return Icons.rocket_launch_rounded;
      case 'avia':
        return Icons.flight_rounded;
      case 'artillery':
        return Icons.gps_fixed_rounded;
      case 'obstril':
        return Icons.crisis_alert_rounded;
      case 'pusk':
        return Icons.rocket_rounded;
      case 'rszv':
        return Icons.multiple_stop_rounded;
      case 'rozved':
        return Icons.radar_rounded;
      case 'vibuh':
        return Icons.local_fire_department_rounded;
      case 'fpv':
        return Icons.videocam_rounded;
      default:
        return Icons.warning_rounded;
    }
  }
}

// ===== MAP PAINTER =====
class UkraineMapPainter extends CustomPainter {
  final Map<String, List<Path>> statePathsCache;
  final Map<String, List<Path>> districtPathsCache;
  final Map<String, bool> stateAlarms;
  final Map<String, bool> districtAlarms;
  final Map<String, String> stateThreatTypes;
  final List<ThreatMarker> threatMarkers;
  final double pulseValue;
  final MapColors mapColors;
  
  UkraineMapPainter({
    required this.statePathsCache,
    required this.districtPathsCache,
    required this.stateAlarms,
    required this.districtAlarms,
    required this.stateThreatTypes,
    required this.threatMarkers,
    required this.pulseValue,
    required this.mapColors,
  });
  
  @override
  void paint(Canvas canvas, Size size) {
    // ViewBox: 0 0 260 175
    const viewBoxWidth = 260.0;
    const viewBoxHeight = 175.0;
    
    final scaleX = size.width / viewBoxWidth;
    final scaleY = size.height / viewBoxHeight;
    final scale = scaleX < scaleY ? scaleX : scaleY;
    
    // Center the map
    final offsetX = (size.width - viewBoxWidth * scale) / 2;
    final offsetY = (size.height - viewBoxHeight * scale) / 2;
    
    canvas.save();
    canvas.translate(offsetX, offsetY);
    canvas.scale(scale);
    
    // === LAYER 1: ОБЛАСТІ (States) ===
    final normalStatePaint = Paint()
      ..color = mapColors.normalFill
      ..style = PaintingStyle.fill;
    
    // Для light theme - м'якіший червоний, для dark - темніший
    final alarmBaseLight = const Color(0xFFDC2626);
    final alarmBaseDark = const Color(0xFF7f1d1d);
    final alarmHighLight = const Color(0xFFF87171);
    final alarmHighDark = const Color(0xFF991b1b);
    
    final alarmStatePaint = Paint()
      ..color = Color.lerp(
        mapColors.isDark ? alarmBaseDark : alarmBaseLight.withOpacity(0.7),
        mapColors.isDark ? alarmHighDark : alarmHighLight.withOpacity(0.85),
        pulseValue,
      )!
      ..style = PaintingStyle.fill;
      
    final normalStrokePaint = Paint()
      ..color = mapColors.normalStroke.withOpacity(0.3)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 0.4;
      
    final alarmStrokePaint = Paint()
      ..color = mapColors.alarmStrokeState.withOpacity(0.35)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 0.4;
    
    // Малюємо області
    for (final entry in statePathsCache.entries) {
      final regionId = entry.key;
      final paths = entry.value;
      final hasAlarm = stateAlarms[regionId] ?? false;
      
      final fillPaint = hasAlarm ? alarmStatePaint : normalStatePaint;
      final strokePaint = hasAlarm ? alarmStrokePaint : normalStrokePaint;
      
      for (final path in paths) {
        canvas.drawPath(path, fillPaint);
        canvas.drawPath(path, strokePaint);
      }
    }
    
    // === LAYER 2: РАЙОНИ (Districts) ===
    // Малюємо тільки райони з тривогою (поверх областей)
    final districtAlarmLight = const Color(0xFFEF4444);
    final districtAlarmDark = const Color(0xFFB91C1C);
    final districtAlarmHighLight = const Color(0xFFF87171);
    final districtAlarmHighDark = const Color(0xFFDC2626);
    
    final districtAlarmColor = Color.lerp(
      mapColors.isDark ? districtAlarmDark : districtAlarmLight.withOpacity(0.5),
      mapColors.isDark ? districtAlarmHighDark : districtAlarmHighLight.withOpacity(0.7),
      pulseValue,
    )!.withOpacity(0.6);
    
    final districtAlarmPaint = Paint()
      ..color = districtAlarmColor
      ..style = PaintingStyle.fill;
      
    // Stroke same color as fill to avoid gaps
    final districtAlarmStrokePaint = Paint()
      ..color = districtAlarmColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = 0.3;
    
    // Красивий контур районів (в UkraineMapPainter без zoom, показуємо завжди)
    final showDistrictBorders = true;
    final districtBorderPaint = Paint()
      ..color = mapColors.isDark 
        ? Colors.white.withOpacity(0.15)
        : Colors.black.withOpacity(0.1)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 0.2;
    
    // Спочатку малюємо всі заливки районів з тривогою
    for (final entry in districtPathsCache.entries) {
      final districtId = entry.key;
      final paths = entry.value;
      final hasAlarm = districtAlarms[districtId] ?? false;
      
      if (hasAlarm) {
        for (final path in paths) {
          canvas.drawPath(path, districtAlarmPaint);
          canvas.drawPath(path, districtAlarmStrokePaint);
        }
      }
    }
    
    // Потім малюємо границі районів поверх (тільки при зумі)
    if (showDistrictBorders) {
      for (final entry in districtPathsCache.entries) {
        final paths = entry.value;
        for (final path in paths) {
          canvas.drawPath(path, districtBorderPaint);
        }
      }
    }
    
    // === LAYER 3: НАЗВИ ОБЛАСТЕЙ ===
    // Координати з ukraine_names.svg (точні позиції)
    const regionLabels = <String, Map<String, dynamic>>{
      'UA-68': {'name': 'Хмельницька', 'x': 68.5, 'y': 63.0},
      'UA-07': {'name': 'Волинська', 'x': 40.0, 'y': 28.2},
      'UA-56': {'name': 'Рівненська', 'x': 65.0, 'y': 30.0},
      'UA-18': {'name': 'Житомирська', 'x': 88.0, 'y': 42.3},
      'UA-32': {'name': 'Київська', 'x': 122.0, 'y': 56.0},
      'UA-30': {'name': 'м. Київ', 'x': 120.0, 'y': 41.5},
      'UA-74': {'name': 'Чернігівська', 'x': 139.0, 'y': 25.5},
      'UA-59': {'name': 'Сумська', 'x': 171.0, 'y': 33.0},
      'UA-63': {'name': 'Харківська', 'x': 203.5, 'y': 62.8},
      'UA-09': {'name': 'Луганська', 'x': 239.0, 'y': 79.0},
      'UA-14': {'name': 'Донецька', 'x': 221.0, 'y': 97.0},
      'UA-23': {'name': 'Запорізька', 'x': 195.0, 'y': 115.0},
      'UA-12': {'name': 'Дніпропетровська', 'x': 178.0, 'y': 89.0},
      'UA-48': {'name': 'Миколаївська', 'x': 139.0, 'y': 113.0},
      'UA-65': {'name': 'Херсонська', 'x': 163.0, 'y': 126.0},
      'UA-51': {'name': 'Одеська', 'x': 110.0, 'y': 138.0},
      'UA-35': {'name': 'Кіровоградська', 'x': 140.0, 'y': 88.4},
      'UA-53': {'name': 'Полтавська', 'x': 162.7, 'y': 58.0},
      'UA-71': {'name': 'Черкаська', 'x': 132.0, 'y': 73.0},
      'UA-05': {'name': 'Вінницька', 'x': 95.0, 'y': 80.0},
      'UA-61': {'name': 'Тернопільська', 'x': 47.0, 'y': 67.0},
      'UA-77': {'name': 'Чернівецька', 'x': 53.0, 'y': 94.0},
      'UA-26': {'name': 'Івано-Франківська', 'x': 32.0, 'y': 83.0},
      'UA-21': {'name': 'Закарпатська', 'x': 15.0, 'y': 91.0},
      'UA-46': {'name': 'Львівська', 'x': 29.0, 'y': 61.0},
      'UA-43': {'name': 'А. Р. Крим', 'x': 172.0, 'y': 152.7},
    };

    final labelStyle = TextStyle(
      color: mapColors.labelColor,
      fontSize: 3.5,
      fontWeight: FontWeight.w500,
      letterSpacing: 0.15,
      shadows: [
        Shadow(
          color: mapColors.labelShadow,
          blurRadius: 3,
          offset: const Offset(0.4, 0.4),
        ),
        Shadow(
          color: mapColors.labelShadow,
          blurRadius: 1,
          offset: const Offset(-0.2, -0.2),
        ),
      ],
    );

    for (final entry in regionLabels.entries) {
      final data = entry.value;
      final name = data['name'] as String;
      final x = data['x'] as double;
      final y = data['y'] as double;
      
      final textSpan = TextSpan(text: name, style: labelStyle);
      final textPainter = TextPainter(
        text: textSpan,
        textDirection: TextDirection.ltr,
        textAlign: TextAlign.center,
      );
      textPainter.layout();
      
      // Центруємо текст
      final offsetX = x - textPainter.width / 2;
      final offsetY = y - textPainter.height / 2;
      
      textPainter.paint(canvas, Offset(offsetX, offsetY));
    }

    // === LAYER 4: ТРАЄКТОРІЇ (стрілки шляху) ===
    for (final marker in threatMarkers) {
      // === AI TRAJECTORY (новий формат) ===
      if (marker.hasAITrajectory) {
        final traj = marker.trajectory!;
        
        // Конвертуємо координати в позиції на карті
        final startPos = MapBounds.latLngToPercent(traj.startLat, traj.startLng);
        final endPos = MapBounds.latLngToPercent(traj.endLat, traj.endLng);
        
        final startPoint = Offset(startPos.dx * viewBoxWidth, startPos.dy * viewBoxHeight);
        final endPoint = Offset(endPos.dx * viewBoxWidth, endPos.dy * viewBoxHeight);
        
        // Колір: жовтий для AI прогнозу, білий для підтвердженого
        final lineColor = traj.predicted 
            ? const Color(0xFFfbbf24) // Жовтий для AI predictions
            : Colors.white.withOpacity(0.7);
        
        // Тонка пунктирна лінія траєкторії (без світіння)
        final trajectoryPaint = Paint()
          ..color = lineColor
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.2
          ..strokeCap = StrokeCap.round;
        
        // Малюємо пунктирну лінію
        final totalDistance = (endPoint - startPoint).distance;
        const dashLength = 6.0;
        const gapLength = 4.0;
        final direction = (endPoint - startPoint) / totalDistance;
        
        double currentDistance = 0;
        while (currentDistance < totalDistance) {
          final dashStart = startPoint + direction * currentDistance;
          final dashEnd = startPoint + direction * math.min(currentDistance + dashLength, totalDistance);
          canvas.drawLine(dashStart, dashEnd, trajectoryPaint);
          currentDistance += dashLength + gapLength;
        }
        
        // Маленька стрілка на 70% траєкторії
        final arrowPos = Offset(
          startPoint.dx + (endPoint.dx - startPoint.dx) * 0.7,
          startPoint.dy + (endPoint.dy - startPoint.dy) * 0.7,
        );
        
        // Обчислюємо напрямок стрілки
        final dx = endPoint.dx - startPoint.dx;
        final dy = endPoint.dy - startPoint.dy;
        final angle = math.atan2(dy, dx);
        
        const arrowSize = 5.0;
        const arrowAngle = 0.5;
        
        final arrowPaint = Paint()
          ..color = lineColor
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.2
          ..strokeCap = StrokeCap.round;
        
        // Малюємо тільки дві лінії стрілки (V-форма)
        canvas.drawLine(
          arrowPos,
          Offset(
            arrowPos.dx - arrowSize * math.cos(angle - arrowAngle),
            arrowPos.dy - arrowSize * math.sin(angle - arrowAngle),
          ),
          arrowPaint,
        );
        canvas.drawLine(
          arrowPos,
          Offset(
            arrowPos.dx - arrowSize * math.cos(angle + arrowAngle),
            arrowPos.dy - arrowSize * math.sin(angle + arrowAngle),
          ),
          arrowPaint,
        );
        
        continue; // Пропускаємо старий формат для цього маркера
      }
      
      // === СТАРИЙ ФОРМАТ (projected_path) ===
      if (!marker.hasTrajectory) continue;
      
      final path = marker.projectedPath;
      if (path == null || path.length < 2) continue;
      
      // Конвертуємо точки траєкторії в координати карти
      final points = path.map((p) {
        final pos = MapBounds.latLngToPercent(p.lat, p.lng);
        return Offset(pos.dx * viewBoxWidth, pos.dy * viewBoxHeight);
      }).toList();
      
      // Фільтруємо точки за межами карти
      final visiblePoints = points.where((p) => 
        p.dx > -10 && p.dx < viewBoxWidth + 10 && 
        p.dy > -10 && p.dy < viewBoxHeight + 10
      ).toList();
      
      if (visiblePoints.length < 2) continue;
      
      // Градієнтна лінія траєкторії (від джерела до цілі)
      final trajectoryPaint = Paint()
        ..color = Colors.orange.withOpacity(0.6)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.5
        ..strokeCap = StrokeCap.round;
      
      // Малюємо пунктирну лінію
      final trajectoryPath = Path();
      trajectoryPath.moveTo(visiblePoints.first.dx, visiblePoints.first.dy);
      
      for (int i = 1; i < visiblePoints.length; i++) {
        // Пунктирна лінія через точки
        if (i % 2 == 1) {
          trajectoryPath.lineTo(visiblePoints[i].dx, visiblePoints[i].dy);
        } else {
          trajectoryPath.moveTo(visiblePoints[i].dx, visiblePoints[i].dy);
        }
      }
      
      // Світіння траєкторії
      final glowPaint = Paint()
        ..color = Colors.orange.withOpacity(0.2)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 4.0
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 3);
      canvas.drawPath(trajectoryPath, glowPaint);
      canvas.drawPath(trajectoryPath, trajectoryPaint);
      
      // Стрілка на кінці траєкторії
      if (visiblePoints.length >= 2) {
        final lastPoint = visiblePoints.last;
        final secondLast = visiblePoints[visiblePoints.length - 2];
        
        // Обчислюємо напрямок стрілки
        final dx = lastPoint.dx - secondLast.dx;
        final dy = lastPoint.dy - secondLast.dy;
        final angle = math.atan2(dy, dx);
        
        final arrowSize = 3.0;
        final arrowAngle = 0.5; // радіани
        
        final arrowPaint = Paint()
          ..color = Colors.orange.withOpacity(0.8)
          ..style = PaintingStyle.fill;
        
        final arrowPath = Path();
        arrowPath.moveTo(lastPoint.dx, lastPoint.dy);
        arrowPath.lineTo(
          lastPoint.dx - arrowSize * math.cos(angle - arrowAngle),
          lastPoint.dy - arrowSize * math.sin(angle - arrowAngle),
        );
        arrowPath.lineTo(
          lastPoint.dx - arrowSize * math.cos(angle + arrowAngle),
          lastPoint.dy - arrowSize * math.sin(angle + arrowAngle),
        );
        arrowPath.close();
        canvas.drawPath(arrowPath, arrowPaint);
      }
      
      // Проміжні точки траєкторії (маленькі кола)
      for (int i = 1; i < visiblePoints.length - 1; i++) {
        final point = visiblePoints[i];
        final dotPaint = Paint()
          ..color = Colors.orange.withOpacity(0.4)
          ..style = PaintingStyle.fill;
        canvas.drawCircle(point, 1.5, dotPaint);
      }
    }

    // === LAYER 6: МАРКЕРИ ЗАГРОЗ ===
    // NOTE: Marker rendering has been consolidated to _LabelsMarkersPainter 
    // to avoid duplicate rendering and coordinate system conflicts.
    // _LabelsMarkersPainter uses screen coordinates which are more reliable
    // for interactive elements and proper zoom handling.
    
    canvas.restore();
  }
  
  @override
  bool shouldRepaint(UkraineMapPainter oldDelegate) {
    // Тільки перемальовувати якщо є реальні зміни
    if (oldDelegate.mapColors.isDark != mapColors.isDark) return true;
    if (oldDelegate.stateAlarms.length != stateAlarms.length) return true;
    if (oldDelegate.districtAlarms.length != districtAlarms.length) return true;
    if (oldDelegate.threatMarkers.length != threatMarkers.length) return true;
    
    // Перевіряємо пульсацію тільки якщо є тривоги (збільшено поріг для меншої кількості перемалювань)
    if (stateAlarms.values.any((v) => v) || districtAlarms.values.any((v) => v)) {
      if ((oldDelegate.pulseValue - pulseValue).abs() > 0.1) return true; // було 0.05
    }
    
    return false;
  }
}

// ===== SVG MAP LAYER (for hybrid mode) =====
// This is a proper flutter_map layer that transforms with the map camera
class _SvgMapLayer extends StatelessWidget {
  final Map<String, List<Path>> statePathsCache;
  final Map<String, List<Path>> districtPathsCache;
  final Map<String, bool> stateAlarms;
  final Map<String, bool> districtAlarms;
  final Map<String, String> stateThreatTypes;
  final List<ThreatMarker> threatMarkers;
  final double pulseValue;
  final MapColors mapColors;
  final double opacity;
  final void Function(ThreatMarker) onMarkerTap;
  
  // SVG viewBox dimensions
  static const double svgWidth = 260.0;
  static const double svgHeight = 175.0;
  
  // Geographic bounds that SVG covers (must match MapBounds)
  static const double geoMinLat = 44.2;
  static const double geoMaxLat = 52.4;
  static const double geoMinLng = 22.0;
  static const double geoMaxLng = 40.2;

  const _SvgMapLayer({
    required this.statePathsCache,
    required this.districtPathsCache,
    required this.stateAlarms,
    required this.districtAlarms,
    required this.stateThreatTypes,
    required this.threatMarkers,
    required this.pulseValue,
    required this.mapColors,
    required this.opacity,
    required this.onMarkerTap,
  });
  
  /// Convert SVG coordinates to LatLng
  static LatLng svgToLatLng(double svgX, double svgY) {
    // SVG (0,0) = top-left = (geoMinLng, geoMaxLat)
    // SVG (svgWidth, svgHeight) = bottom-right = (geoMaxLng, geoMinLat)
    final lng = geoMinLng + (svgX / svgWidth) * (geoMaxLng - geoMinLng);
    final lat = geoMaxLat - (svgY / svgHeight) * (geoMaxLat - geoMinLat);
    return LatLng(lat, lng);
  }

  @override
  Widget build(BuildContext context) {
    final camera = MapCamera.of(context);
    
    return Opacity(
      opacity: opacity,
      child: GestureDetector(
        behavior: HitTestBehavior.translucent,
        onTapUp: (details) => _handleTap(context, details, camera),
        child: CustomPaint(
          size: Size.infinite,
          painter: _SvgMapPainter(
            camera: camera,
            statePathsCache: statePathsCache,
            districtPathsCache: districtPathsCache,
            stateAlarms: stateAlarms,
            districtAlarms: districtAlarms,
            threatMarkers: threatMarkers,
            pulseValue: pulseValue,
            mapColors: mapColors,
          ),
        ),
      ),
    );
  }
  
  void _handleTap(BuildContext context, TapUpDetails details, MapCamera camera) {
    const tapTolerancePixels = 30.0;
    
    ThreatMarker? tappedMarker;
    double minDistance = double.infinity;
    
    for (final marker in threatMarkers) {
      final markerOffset = camera.latLngToScreenOffset(
        LatLng(marker.lat, marker.lng),
      );
      
      final dx = details.localPosition.dx - markerOffset.dx;
      final dy = details.localPosition.dy - markerOffset.dy;
      final distance = math.sqrt(dx * dx + dy * dy);
      
      if (distance < tapTolerancePixels && distance < minDistance) {
        minDistance = distance;
        tappedMarker = marker;
      }
    }
    
    if (tappedMarker != null) {
      onMarkerTap(tappedMarker);
    }
  }
}

// ===== SVG MAP PAINTER =====
class _SvgMapPainter extends CustomPainter {
  final MapCamera camera;
  final Map<String, List<Path>> statePathsCache;
  final Map<String, List<Path>> districtPathsCache;
  final Map<String, bool> stateAlarms;
  final Map<String, bool> districtAlarms;
  final List<ThreatMarker> threatMarkers;
  final double pulseValue;
  final MapColors mapColors;
  
  _SvgMapPainter({
    required this.camera,
    required this.statePathsCache,
    required this.districtPathsCache,
    required this.stateAlarms,
    required this.districtAlarms,
    required this.threatMarkers,
    required this.pulseValue,
    required this.mapColors,
  });
  
  /// Convert SVG coordinates to screen offset using camera
  Offset svgToScreen(double svgX, double svgY) {
    final latLng = _SvgMapLayer.svgToLatLng(svgX, svgY);
    return camera.latLngToScreenOffset(latLng);
  }
  
  /// Get canvas transformation to map SVG coordinates to screen
  /// This transforms the entire canvas so paths can be drawn directly
  void applyCanvasTransform(Canvas canvas) {
    // Get screen positions of SVG corners (ignoring any camera rotation)
    final topLeft = svgToScreen(0, 0);
    final topRight = svgToScreen(_SvgMapLayer.svgWidth, 0);
    final bottomLeft = svgToScreen(0, _SvgMapLayer.svgHeight);
    
    // Calculate scale factors
    final scaleX = (topRight.dx - topLeft.dx) / _SvgMapLayer.svgWidth;
    final scaleY = (bottomLeft.dy - topLeft.dy) / _SvgMapLayer.svgHeight;
    
    // If camera has rotation, we need to counter-rotate
    // But since we disabled rotation, just apply translate + scale
    canvas.translate(topLeft.dx, topLeft.dy);
    canvas.scale(scaleX, scaleY);
  }
  
  @override
  void paint(Canvas canvas, Size size) {
    // === LAYER 0: BACKGROUND (hide tiles at low zoom) ===
    // Fill the entire canvas with background color first
    final bgPaint = Paint()
      ..color = mapColors.bgMain
      ..style = PaintingStyle.fill;
    canvas.drawRect(Rect.fromLTWH(0, 0, size.width, size.height), bgPaint);
    
    // Save canvas state before transformation
    canvas.save();
    
    // Apply SVG to screen transformation
    applyCanvasTransform(canvas);
    
    // Calculate stroke scale based on zoom (strokes need to be adjusted for canvas scale)
    final topLeft = svgToScreen(0, 0);
    final topRight = svgToScreen(_SvgMapLayer.svgWidth, 0);
    final canvasScale = (topRight.dx - topLeft.dx) / _SvgMapLayer.svgWidth;
    final strokeScale = (1.0 / canvasScale).clamp(0.3, 2.0);
    
    // === LAYER 1: STATES ===
    final normalStatePaint = Paint()
      ..color = mapColors.normalFill
      ..style = PaintingStyle.fill;
    
    final alarmBaseLight = const Color(0xFFDC2626);
    final alarmBaseDark = const Color(0xFF7f1d1d);
    final alarmHighLight = const Color(0xFFF87171);
    final alarmHighDark = const Color(0xFF991b1b);
    
    final alarmColor = Color.lerp(
      mapColors.isDark ? alarmBaseDark : alarmBaseLight.withOpacity(0.7),
      mapColors.isDark ? alarmHighDark : alarmHighLight.withOpacity(0.85),
      pulseValue,
    )!;
    
    final alarmStatePaint = Paint()
      ..color = alarmColor
      ..style = PaintingStyle.fill;
    
    final normalStrokePaint = Paint()
      ..color = mapColors.normalStroke.withOpacity(0.5)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.0 * strokeScale
      ..strokeJoin = StrokeJoin.round;
      
    // Alarm stroke uses same color as fill to eliminate gaps between alarm regions
    final alarmStrokePaint = Paint()
      ..color = alarmColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.2 * strokeScale
      ..strokeJoin = StrokeJoin.round;
    
    // Draw states (paths are in SVG coordinates, canvas is transformed)
    for (final entry in statePathsCache.entries) {
      final regionId = entry.key;
      final paths = entry.value;
      final hasAlarm = stateAlarms[regionId] ?? false;
      
      final fillPaint = hasAlarm ? alarmStatePaint : normalStatePaint;
      final strokePaint = hasAlarm ? alarmStrokePaint : normalStrokePaint;
      
      for (final svgPath in paths) {
        canvas.drawPath(svgPath, fillPaint);
        canvas.drawPath(svgPath, strokePaint);
      }
    }
    
    // === LAYER 2: DISTRICTS ===
    final districtAlarmPaint = Paint()
      ..color = Color.lerp(
        mapColors.isDark ? const Color(0xFFB91C1C) : const Color(0xFFEF4444).withOpacity(0.5),
        mapColors.isDark ? const Color(0xFFDC2626) : const Color(0xFFF87171).withOpacity(0.7),
        pulseValue,
      )!.withOpacity(0.6)
      ..style = PaintingStyle.fill;
      
    final districtBorderPaint = Paint()
      ..color = mapColors.normalStroke.withOpacity(0.08)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 0.3 * strokeScale;
    
    for (final entry in districtPathsCache.entries) {
      final districtId = entry.key;
      final paths = entry.value;
      final hasAlarm = districtAlarms[districtId] ?? false;
      
      for (final svgPath in paths) {
        // Only draw district border at high zoom
        if (camera.zoom > 8) {
          canvas.drawPath(svgPath, districtBorderPaint);
        }
        if (hasAlarm) {
          canvas.drawPath(svgPath, districtAlarmPaint);
        }
      }
    }
    
    // Restore canvas before drawing markers (they use screen coordinates)
    canvas.restore();
    
    // === LAYER 3: REGION LABELS ===
    // Region labels are now drawn in _LabelsMarkersLayer for better stability
    
    // === LAYER 4: THREAT MARKERS ===
    // Markers are now drawn in _LabelsMarkersLayer for proper layering
  }
  
  @override
  bool shouldRepaint(_SvgMapPainter oldDelegate) {
    // Only repaint when data actually changes
    return camera != oldDelegate.camera ||
           pulseValue != oldDelegate.pulseValue ||
           stateAlarms != oldDelegate.stateAlarms ||
           districtAlarms != oldDelegate.districtAlarms;
  }
}

/// Labels and markers layer - always visible regardless of SVG opacity
class _LabelsMarkersLayer extends StatelessWidget {
  final List<ThreatMarker> threatMarkers;
  final MapColors mapColors;
  final void Function(ThreatMarker) onMarkerTap;

  const _LabelsMarkersLayer({
    required this.threatMarkers,
    required this.mapColors,
    required this.onMarkerTap,
  });

  @override
  Widget build(BuildContext context) {
    final camera = MapCamera.of(context);
    
    return GestureDetector(
      behavior: HitTestBehavior.translucent,
      onTapUp: (details) => _handleTap(details, camera),
      child: CustomPaint(
        size: Size.infinite,
        painter: _LabelsMarkersPainter(
          camera: camera,
          threatMarkers: threatMarkers,
          mapColors: mapColors,
        ),
      ),
    );
  }
  
  void _handleTap(TapUpDetails details, MapCamera camera) {
    const tapTolerancePixels = 30.0;
    
    ThreatMarker? tappedMarker;
    double minDistance = double.infinity;
    
    for (final marker in threatMarkers) {
      final markerOffset = camera.latLngToScreenOffset(
        LatLng(marker.lat, marker.lng),
      );
      
      final dx = details.localPosition.dx - markerOffset.dx;
      final dy = details.localPosition.dy - markerOffset.dy;
      final distance = math.sqrt(dx * dx + dy * dy);
      
      if (distance < tapTolerancePixels && distance < minDistance) {
        minDistance = distance;
        tappedMarker = marker;
      }
    }
    
    if (tappedMarker != null) {
      onMarkerTap(tappedMarker);
    }
  }
}

class _LabelsMarkersPainter extends CustomPainter {
  final MapCamera camera;
  final List<ThreatMarker> threatMarkers;
  final MapColors mapColors;
  
  // Region labels with SVG coordinates
  static const regionLabels = <String, Map<String, dynamic>>{
    'UA-68': {'name': 'Хмельницька', 'x': 68.5, 'y': 63.0},
    'UA-07': {'name': 'Волинська', 'x': 40.0, 'y': 28.2},
    'UA-56': {'name': 'Рівненська', 'x': 65.0, 'y': 30.0},
    'UA-18': {'name': 'Житомирська', 'x': 88.0, 'y': 42.3},
    'UA-32': {'name': 'Київська', 'x': 122.0, 'y': 56.0},
    'UA-30': {'name': 'м. Київ', 'x': 120.0, 'y': 41.5},
    'UA-74': {'name': 'Чернігівська', 'x': 139.0, 'y': 25.5},
    'UA-59': {'name': 'Сумська', 'x': 171.0, 'y': 33.0},
    'UA-63': {'name': 'Харківська', 'x': 203.5, 'y': 62.8},
    'UA-09': {'name': 'Луганська', 'x': 239.0, 'y': 79.0},
    'UA-14': {'name': 'Донецька', 'x': 221.0, 'y': 97.0},
    'UA-23': {'name': 'Запорізька', 'x': 195.0, 'y': 115.0},
    'UA-12': {'name': 'Дніпропетровська', 'x': 178.0, 'y': 89.0},
    'UA-48': {'name': 'Миколаївська', 'x': 139.0, 'y': 113.0},
    'UA-65': {'name': 'Херсонська', 'x': 163.0, 'y': 126.0},
    'UA-51': {'name': 'Одеська', 'x': 110.0, 'y': 138.0},
    'UA-35': {'name': 'Кіровоградська', 'x': 140.0, 'y': 88.4},
    'UA-53': {'name': 'Полтавська', 'x': 162.7, 'y': 58.0},
    'UA-71': {'name': 'Черкаська', 'x': 132.0, 'y': 73.0},
    'UA-05': {'name': 'Вінницька', 'x': 95.0, 'y': 80.0},
    'UA-61': {'name': 'Тернопільська', 'x': 47.0, 'y': 67.0},
    'UA-77': {'name': 'Чернівецька', 'x': 53.0, 'y': 94.0},
    'UA-26': {'name': 'Івано-Франківська', 'x': 32.0, 'y': 83.0},
    'UA-21': {'name': 'Закарпатська', 'x': 15.0, 'y': 91.0},
    'UA-46': {'name': 'Львівська', 'x': 29.0, 'y': 61.0},
    'UA-43': {'name': 'А. Р. Крим', 'x': 172.0, 'y': 152.7},
  };
  
  _LabelsMarkersPainter({
    required this.camera,
    required this.threatMarkers,
    required this.mapColors,
  });
  
  /// Convert SVG coordinates to screen offset using camera
  Offset svgToScreen(double svgX, double svgY) {
    final latLng = _SvgMapLayer.svgToLatLng(svgX, svgY);
    return camera.latLngToScreenOffset(latLng);
  }

  @override
  void paint(Canvas canvas, Size size) {
    final strokeScale = (camera.zoom / 6.0).clamp(0.5, 3.0);
    
    // === REGION LABELS ===
    // Показуємо назви тільки при зумі > 4.5
    if (camera.zoom > 4.5) {
      final labelSize = (11.0 * strokeScale).clamp(9.0, 16.0);
      final labelStyle = TextStyle(
        color: mapColors.labelColor,
        fontSize: labelSize,
        fontWeight: FontWeight.w600,
        shadows: [
          Shadow(
            color: mapColors.labelShadow,
            blurRadius: 2,
            offset: const Offset(0.5, 0.5),
          ),
          Shadow(
            color: mapColors.labelShadow,
            blurRadius: 1,
            offset: const Offset(-0.3, -0.3),
          ),
        ],
      );

      for (final entry in regionLabels.entries) {
        final data = entry.value;
        final name = data['name'] as String;
        final svgX = data['x'] as double;
        final svgY = data['y'] as double;
        
        // Convert SVG coordinates to screen position
        final screenPos = svgToScreen(svgX, svgY);
        
        // Skip if outside visible area
        if (screenPos.dx < -100 || screenPos.dx > size.width + 100 ||
            screenPos.dy < -50 || screenPos.dy > size.height + 50) {
          continue;
        }
        
        final textSpan = TextSpan(text: name, style: labelStyle);
        final textPainter = TextPainter(
          text: textSpan,
          textDirection: TextDirection.ltr,
          textAlign: TextAlign.center,
        );
        textPainter.layout();
        
        // Center text at position
        final offsetX = screenPos.dx - textPainter.width / 2;
        final offsetY = screenPos.dy - textPainter.height / 2;
        
        textPainter.paint(canvas, Offset(offsetX, offsetY));
      }
    }
    
    // === THREAT MARKERS (consolidated rendering - removed from UkraineMapPainter to avoid duplication) ===
    final markerSize = (24.0 * strokeScale).clamp(20.0, 48.0);
    final iconManager = ThreatIconManager();
    
    for (final marker in threatMarkers) {
      final screenPos = camera.latLngToScreenOffset(
        LatLng(marker.lat, marker.lng),
      );
      
      // Skip if outside visible area (with margin for rotated icons)
      if (screenPos.dx < -markerSize || screenPos.dx > size.width + markerSize ||
          screenPos.dy < -markerSize || screenPos.dy > size.height + markerSize) {
        continue;
      }
      
      final color = ThreatType.getColor(marker.threatType);
      
      // Draw icon from cache with rotation
      final icon = iconManager.icons[marker.threatType] ?? 
                   iconManager.icons['default'];
      
      // Calculate rotation angle based on trajectory (icon points east by default)
      double rotationAngle = 0.0;
      if (marker.hasAITrajectory) {
        final traj = marker.trajectory!;
        final dx = traj.endLng - traj.startLng;
        final dy = traj.endLat - traj.startLat;
        // atan2(dx, dy) gives angle from north clockwise
        // Subtract π/2 because icon points east, not north
        rotationAngle = math.atan2(dx, dy) - math.pi / 2;
      } else if (marker.hasTrajectory && marker.projectedPath != null && marker.projectedPath!.length >= 2) {
        final path = marker.projectedPath!;
        final lastIdx = path.length - 1;
        final dx = path[lastIdx].lng - path[lastIdx - 1].lng;
        final dy = path[lastIdx].lat - path[lastIdx - 1].lat;
        rotationAngle = math.atan2(dx, dy) - math.pi / 2;
      }
      
      if (icon != null && iconManager.isLoaded) {
        canvas.save();
        canvas.translate(screenPos.dx, screenPos.dy);
        
        // Apply rotation if trajectory exists
        if (rotationAngle != 0.0) {
          canvas.rotate(rotationAngle);
        }
        
        final srcRect = Rect.fromLTWH(0, 0, icon.width.toDouble(), icon.height.toDouble());
        final dstRect = Rect.fromCenter(center: Offset.zero, width: markerSize, height: markerSize);
        final paint = Paint()..filterQuality = FilterQuality.high;
        canvas.drawImageRect(icon, srcRect, dstRect, paint);
        
        canvas.restore();
      } else {
        // Fallback circle when icon not loaded
        final markerPaint = Paint()
          ..color = color.withOpacity(0.9)
          ..style = PaintingStyle.fill;
        canvas.drawCircle(screenPos, markerSize / 2, markerPaint);
        
        final borderPaint = Paint()
          ..color = Colors.white.withOpacity(0.8)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2.0;
        canvas.drawCircle(screenPos, markerSize / 2, borderPaint);
      }
      
      // Draw trajectory line if available
      if (marker.trajectory != null) {
        final traj = marker.trajectory!;
        final startScreen = camera.latLngToScreenOffset(
          LatLng(traj.startLat, traj.startLng),
        );
        final endScreen = camera.latLngToScreenOffset(
          LatLng(traj.endLat, traj.endLng),
        );
        
        // Dashed line for predicted trajectory
        final trajPaint = Paint()
          ..color = traj.predicted ? const Color(0xFFfbbf24) : Colors.white.withOpacity(0.6)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2.0 * strokeScale;
        
        canvas.drawLine(startScreen, endScreen, trajPaint);
      }
    }
  }
  
  @override
  bool shouldRepaint(_LabelsMarkersPainter oldDelegate) {
    return camera != oldDelegate.camera ||
           threatMarkers.length != oldDelegate.threatMarkers.length;
  }
}

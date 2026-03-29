// ignore_for_file: deprecated_member_use
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'dart:async';
import 'dart:convert';
import 'dart:math' as math;
import 'package:flutter_map/flutter_map.dart';
import 'package:http/http.dart' as http;
import 'package:latlong2/latlong.dart' hide Path;
import 'package:shared_preferences/shared_preferences.dart';
import '../config/api_config.dart';
import '../core/pro/pro_features.dart';
import '../data/ukraine_region_paths.dart';
import '../data/ukraine_district_paths.dart';
import '../models/map_models.dart';
import '../services/map_data_service.dart';
import '../services/map_offline_cache.dart';
import '../utils/svg_path_parser.dart';
import '../services/ballistic_alert_service.dart';
import '../services/widget_service.dart';
import '../services/threat_icon_manager.dart';
import '../services/data_stream_service.dart';
import '../services/moderator_service.dart';
import '../services/map_ready_notifier.dart';
import '../theme/map_colors.dart';
import '../features/map/presentation/widgets/map_layers.dart';
import '../features/map/presentation/widgets/map_overlays.dart';
import '../features/map/presentation/widgets/marker_info_sheet.dart';

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
/// [appBarOverlayHeight] — висота шапки поверх body (для табу з extendBodyBehindAppBar).
/// Передай 52, якщо карта рендериться під AppBar.
class NativeMapPage extends StatefulWidget {
  const NativeMapPage({super.key, this.appBarOverlayHeight = 0});

  final double appBarOverlayHeight;

  @override
  State<NativeMapPage> createState() => _NativeMapPageState();
}

class _NativeMapPageState extends State<NativeMapPage>
    with TickerProviderStateMixin, WidgetsBindingObserver {
  // Стан тривог
  Map<String, bool> stateAlarms = {}; // Області (oblasts)
  Map<String, bool> districtAlarms = {}; // Райони
  Map<String, String> stateThreatTypes =
      {}; // Тип загрози по області (для іконок)

  // Маркери загроз
  List<ThreatMarker> threatMarkers = [];
  Map<String, int> markerCounts = {};
  List<ThreatMarker> _currentVisibleMarkers = [];

  // Стан UI
  bool isLoading = true;
  String? error;
  DateTime? lastUpdate;
  bool _fromCache = false; // true = показуємо кеш (офлайн або мережа недоступна)
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

  // SSE push subscriptions (primary data source)
  StreamSubscription? _alarmSSESub;
  StreamSubscription? _markerSSESub;
  StreamSubscription? _trackUpdateSSESub;
  StreamSubscription? _markerUpdateSSESub;
  StreamSubscription? _markerDeleteSSESub;

  // Інтервали оновлення (fallback — основні дані приходять через SSE push)
  static const int alarmUpdateInterval = 30; // секунд (fallback)
  static const int markerUpdateInterval = 30; // секунд (fallback)
  int get _timeRange => ProGate.isPro ? 180 : 60; // PRO: 3 год, FREE: 1 год історії

  // Threat history (for tracker)
  final List<ThreatHistoryEntry> _threatHistory = [];
  DateTime? _lastHistoryEntryAt;
  static const Duration _historyMinInterval = Duration(minutes: 1);

  final Set<String> _filterableThreatTypes = {
    ThreatType.shahed,
    ThreatType.raketa,
    ThreatType.kab,
    ThreatType.fpv,
    ThreatType.rszv,
    ThreatType.avia,
    ThreatType.artillery,
    ThreatType.obstril,
  };
  final Set<String> _visibleThreatTypes = {
    ThreatType.shahed,
    ThreatType.raketa,
    ThreatType.kab,
    ThreatType.fpv,
    ThreatType.rszv,
    ThreatType.avia,
  };

  // Operator mode (advanced controls)
  bool _operatorModeEnabled = false;
  final bool _showSvgLayer = true;
  final bool _showMarkersLayer = true;

  // Parsed paths cache
  final Map<String, List<Path>> _statePathsCache = {};
  final Map<String, List<Path>> _districtPathsCache = {};
  static final Map<String, List<Path>> _sharedStatePathsCache = {};
  static final Map<String, List<Path>> _sharedDistrictPathsCache = {};

  // Zoom/pan - now using flutter_map
  final MapController _mapController = MapController();
  double _currentZoom = 6.0;

  // Hybrid map: SVG fades at high zoom, tiles appear
  static const double _svgFadeStartZoom = 8.0;
  static const double _svgFadeEndZoom = 10.0;

  // Debounce rebuild during active pinch-zoom (prevents jank)
  Timer? _zoomDebounceTimer;
  bool _pulseInTransitionZone = false;

  // Legacy transform controller (for compatibility)
  final TransformationController _transformController =
      TransformationController();

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
    return 1.0 -
        ((_currentZoom - _svgFadeStartZoom) /
            (_svgFadeEndZoom - _svgFadeStartZoom));
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
    );
    // DON'T start immediately — only when alarms appear (_updatePulseAnimation)

    _pulseAnimation = Tween<double>(begin: 0.92, end: 1.0).animate(
      // зменшено амплітуду
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

    // Defer heavy path parsing to after first frame so UI appears immediately
    _statePathsCache.addAll(_sharedStatePathsCache);
    _districtPathsCache.addAll(_sharedDistrictPathsCache);
    if (_statePathsCache.isEmpty || _districtPathsCache.isEmpty) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _parseAllPathsDeferred();
      });
    }
    _loadOperatorMode();
    _loadFromCacheFirst();

    // Signal splash screen that map is ready after first frame
    WidgetsBinding.instance.addPostFrameCallback((_) {
      MapReadyNotifier.instance.markReady();
    });

    // SSE push subscriptions (primary data source — instant updates)
    final dataStream = DataStreamService.instance;
    dataStream.connect();

    _alarmSSESub = dataStream.alarmStream.listen((alarmData) {
      if (!mounted) return;
      _handlePushedAlarms(alarmData);
    });

    _markerSSESub = dataStream.markerNewStream.listen((markerData) {
      if (!mounted) return;
      // New marker arrived — fetch fresh data to get full list with filtering
      _fetchThreatMarkers();
    });

    // Incremental updates — no full refetch, apply in-place
    _trackUpdateSSESub = dataStream.trackUpdateStream.listen((data) {
      if (!mounted) return;
      _applyTrackUpdate(data);
    });
    _markerUpdateSSESub = dataStream.markerUpdateStream.listen((data) {
      if (!mounted) return;
      _applyMarkerUpdate(data);
    });
    _markerDeleteSSESub = dataStream.markerDeleteStream.listen((id) {
      if (!mounted) return;
      _applyMarkerDelete(id);
    });

    // Fallback polling timers (30s — only fires if SSE is down)
    _alarmTimer = Timer.periodic(
      Duration(seconds: alarmUpdateInterval),
      (_) => _fetchAlarms(),
    );
    _markerTimer = Timer.periodic(
      Duration(seconds: markerUpdateInterval),
      (_) => _fetchThreatMarkers(),
    );
  }

  /// Apply track_update SSE — update marker position in-place (no refetch).
  void _applyTrackUpdate(Map<String, dynamic> data) {
    final markerData = data['marker'] as Map<String, dynamic>?;
    if (markerData == null) return;
    final id = markerData['id']?.toString();
    final trackId = data['track_id']?.toString();
    if (id == null && trackId == null) return;

    final idx = threatMarkers.indexWhere((m) =>
        (id != null && m.id == id) || (trackId != null && m.trackId == trackId));
    if (idx < 0) return;

    final updated = threatMarkers[idx].applyPartialUpdate(markerData);
    if (mounted) {
      setState(() {
        threatMarkers = List.from(threatMarkers)..[idx] = updated;
        _cachedFilteredMarkers = null;
        _lastSourceMarkers = null;
      });
    }
  }

  /// Apply marker_update SSE — partial field update.
  void _applyMarkerUpdate(Map<String, dynamic> data) {
    final id = data['id']?.toString();
    if (id == null) return;

    final idx = threatMarkers.indexWhere((m) => m.id == id);
    if (idx < 0) return;

    final updates = Map<String, dynamic>.from(data)..remove('id');
    final updated = threatMarkers[idx].applyPartialUpdate(updates);
    if (mounted) {
      setState(() {
        threatMarkers = List.from(threatMarkers)..[idx] = updated;
        _cachedFilteredMarkers = null;
        _lastSourceMarkers = null;
      });
    }
  }

  /// Apply marker_delete SSE — remove marker immediately.
  void _applyMarkerDelete(String id) {
    if (id.isEmpty || !mounted) return;
    setState(() {
      final before = threatMarkers.length;
      threatMarkers = threatMarkers.where((m) => m.id != id).toList();
      if (threatMarkers.length < before) {
        _recomputeMarkerCounts();
        _cachedFilteredMarkers = null;
        _lastSourceMarkers = null;
      }
    });
  }

  void _recomputeMarkerCounts() {
    markerCounts.clear();
    for (final m in threatMarkers) {
      markerCounts[m.threatType] = (markerCounts[m.threatType] ?? 0) + 1;
    }
  }

  /// Offline-first: завантажити кеш одразу, показати карту без затримки, потім оновити з мережі.
  Future<void> _loadFromCacheFirst() async {
    try {
      final cachedAlarms = await MapOfflineCache.instance.loadAlarms();
      final cachedMarkers = await MapOfflineCache.instance.loadMarkers();
      final alarmsTs = await MapOfflineCache.instance.lastAlarmsUpdate();

      if (mounted && (cachedAlarms != null || cachedMarkers != null)) {
        setState(() {
          if (cachedAlarms != null) {
            stateAlarms = cachedAlarms.stateAlarms;
            districtAlarms = cachedAlarms.districtAlarms;
            stateThreatTypes = cachedAlarms.stateThreatTypes;
            stateAlarmCount = cachedAlarms.stateCount;
            districtAlarmCount = cachedAlarms.districtCount;
          }
          if (alarmsTs != null) lastUpdate = alarmsTs;
          if (cachedMarkers != null) {
            threatMarkers = cachedMarkers.markers;
            markerCounts = Map<String, int>.from(cachedMarkers.counts);
            _syncFilterTypes(cachedMarkers.markers);
          }
          isLoading = false;
          _fromCache = true;
          error = null;
        });
        _updatePulseAnimation();
      }
    } catch (e) {
      debugPrint('Map cache load: $e');
    }
    _fetchAlarms();
    _fetchThreatMarkers();
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
    _zoomDebounceTimer?.cancel();
    _alarmSSESub?.cancel();
    _markerSSESub?.cancel();
    _trackUpdateSSESub?.cancel();
    _markerUpdateSSESub?.cancel();
    _markerDeleteSSESub?.cancel();
    _pulseController.dispose();
    _ballisticController.dispose();
    _allClearController.dispose();
    _transformController.dispose();
    _mapController.dispose();
    _mapDataService.dispose();

    // Відписуємося від глобального сервісу
    BallisticAlertService().removeCallback(_handleGlobalBallisticThreat);
    BallisticAlertService().removeCallback(_handleGlobalBallisticAllClear);
    WidgetsBinding.instance.removeObserver(this);

    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused ||
        state == AppLifecycleState.inactive) {
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

    debugPrint(
      '🚀 Animation started, _ballisticThreatActive = $_ballisticThreatActive',
    );

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

  /// Parsing runs after first frame; yields every N regions so UI doesn't freeze.
  Future<void> _parseAllPathsDeferred() async {
    const yieldEvery = 8;
    if (_sharedStatePathsCache.isNotEmpty &&
        _sharedDistrictPathsCache.isNotEmpty) {
      _statePathsCache.addAll(_sharedStatePathsCache);
      _districtPathsCache.addAll(_sharedDistrictPathsCache);
      if (mounted) setState(() {});
      return;
    }

    // Parse state (oblast) paths
    int i = 0;
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
      if (++i % yieldEvery == 0) await Future.delayed(Duration.zero);
    }
    _sharedStatePathsCache
      ..clear()
      ..addAll(_statePathsCache);
    if (kDebugMode) {
      debugPrint('Parsed ${_statePathsCache.length} state regions');
    }
    // Don't setState here — wait until districts are also parsed

    // Parse district paths (yield so UI stays responsive)
    i = 0;
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
      if (++i % yieldEvery == 0) await Future.delayed(Duration.zero);
    }
    _sharedDistrictPathsCache
      ..clear()
      ..addAll(_districtPathsCache);
    if (kDebugMode) {
      debugPrint('Parsed ${_districtPathsCache.length} district regions');
    }
    // Single setState after ALL paths are parsed (was 3 separate setState calls)
    if (mounted) setState(() {});
  }

  // ===== HANDLE PUSHED ALARMS (from SSE — instant, no HTTP request) =====
  void _handlePushedAlarms(List<dynamic> rawData) {
    try {
      // Parse the raw alarm data using the same MapDataService logic
      // but synchronously since we already have the decoded JSON
      final alarmData = _parseAlarmData(rawData);

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

      if (!alarmsChanged) return;

      final newBallisticRegions = alarmData.ballisticRegions.difference(
        _previousBallisticRegions,
      );
      final clearedBallisticRegions = _previousBallisticRegions.difference(
        alarmData.ballisticRegions,
      );

      if (newBallisticRegions.isNotEmpty) {
        showBallisticThreat(region: newBallisticRegions.join(', '));
      }
      if (clearedBallisticRegions.isNotEmpty &&
          alarmData.ballisticRegions.isEmpty) {
        showBallisticAllClear(region: clearedBallisticRegions.join(', '));
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
          _fromCache = false;
        });
        _updatePulseAnimation();
      }

      _updateHomeWidget(alarmData.stateCount > 0, alarmData.stateCount);
      debugPrint('📡 Alarms pushed via SSE: ${alarmData.stateCount} oblasts');
    } catch (e) {
      debugPrint('📡 Error handling pushed alarms: $e');
    }
  }

  /// Parse raw alarm JSON into MapAlarmData (shared logic for both fetch and push)
  MapAlarmData _parseAlarmData(List<dynamic> data) {
    final Map<String, bool> newStateAlarms = {};
    final Map<String, bool> newDistrictAlarms = {};
    final Map<String, String> newStateThreatTypes = {};
    final Set<String> currentBallisticRegions = {};
    int stateCount = 0;
    int districtCount = 0;

    for (final region in data) {
      if (region is! Map) continue;
      final regionId = region['regionId']?.toString();
      final regionType = region['regionType'] ?? '';
      final activeAlerts = region['activeAlerts'] as List? ?? [];
      final regionName = region['regionName']?.toString() ?? '';

      if (regionId == null) continue;
      final hasAlarm = activeAlerts.isNotEmpty;

      if (regionType == 'State') {
        newStateAlarms[regionId] = hasAlarm;
        if (hasAlarm) {
          stateCount++;
          for (final alert in activeAlerts) {
            final alertType = alert['type']?.toString() ?? '';
            if (alertType == 'DRONES' || alertType.contains('DRONE')) {
              newStateThreatTypes[regionId] = ThreatType.shahed;
            } else if (alertType == 'BALLISTIC' ||
                alertType == 'MISSILE' ||
                alertType.contains('BALLISTIC')) {
              newStateThreatTypes[regionId] = ThreatType.raketa;
              currentBallisticRegions.add(
                regionName.isNotEmpty ? regionName : regionId,
              );
            } else if (alertType == 'AIR') {
              newStateThreatTypes[regionId] = ThreatType.avia;
            }
          }
        }
      } else if (regionType == 'District') {
        newDistrictAlarms[regionId] = hasAlarm;
        if (hasAlarm) {
          districtCount++;
          for (final alert in activeAlerts) {
            final alertType = alert['type']?.toString() ?? '';
            if (alertType == 'BALLISTIC' ||
                alertType == 'MISSILE' ||
                alertType.contains('BALLISTIC')) {
              currentBallisticRegions.add(
                regionName.isNotEmpty ? regionName : regionId,
              );
            }
          }
        }
      }
    }

    return MapAlarmData(
      stateAlarms: newStateAlarms,
      districtAlarms: newDistrictAlarms,
      stateThreatTypes: newStateThreatTypes,
      stateCount: stateCount,
      districtCount: districtCount,
      ballisticRegions: currentBallisticRegions,
    );
  }

  /// Start/stop pulse animation based on whether any alarms are active.
  /// Also pauses pulse in the SVG→tile transition zone (zoom 7–11) to avoid
  /// competing paint work while tiles are being decoded.
  void _updatePulseAnimation() {
    final hasAlarms =
        stateAlarms.values.any((v) => v) || districtAlarms.values.any((v) => v);
    if (hasAlarms && !_pulseInTransitionZone && !_pulseController.isAnimating) {
      _pulseController.repeat(reverse: true);
    } else if ((!hasAlarms || _pulseInTransitionZone) &&
        _pulseController.isAnimating) {
      _pulseController.stop();
      _pulseController.reset();
    }
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
        final newBallisticRegions = alarmData.ballisticRegions.difference(
          _previousBallisticRegions,
        );
        final clearedBallisticRegions = _previousBallisticRegions.difference(
          alarmData.ballisticRegions,
        );

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
            _fromCache = false;
          });
          _updatePulseAnimation();
        }
        if (kDebugMode) {
          debugPrint(
            'Alarms updated: ${alarmData.stateCount} oblasts, ${alarmData.districtCount} districts',
          );
          if (alarmData.ballisticRegions.isNotEmpty) {
            debugPrint(
              '🚀 Ballistic threats active in: ${alarmData.ballisticRegions}',
            );
          }
        }

        _updateHomeWidget(alarmData.stateCount > 0, alarmData.stateCount);
      } else if (kDebugMode) {
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
      final markerData = await _mapDataService.fetchThreatMarkers(
        timeRange: _timeRange,
      );

      if (markerData.ballisticActive != null) {
        if (kDebugMode) {
          debugPrint(
            '🚀 Ballistic threat from API: active=${markerData.ballisticActive}, region=${markerData.ballisticRegion}',
          );
        }
        if (markerData.ballisticActive == true &&
            !BallisticAlertService().isBallisticThreatActive) {
          BallisticAlertService().triggerBallisticThreat(
            region: markerData.ballisticRegion,
          );
        } else if (markerData.ballisticActive == false &&
            BallisticAlertService().isBallisticThreatActive) {
          BallisticAlertService().triggerBallisticAllClear(
            region: markerData.ballisticRegion,
          );
        }
      }

      if (kDebugMode) {
        debugPrint(
          '📊 Received ${markerData.markers.length} markers from API:',
        );
        for (final marker in markerData.markers) {
          String trajInfo = '';
          if (marker.hasAITrajectory) {
            final t = marker.trajectory!;
            trajInfo =
                ' [AI TRAJ: ${t.sourceName} → ${t.targetName}${t.predicted ? " (прогноз)" : ""}]';
          }
          debugPrint(
            '  📍 type="${marker.threatType}", place="${marker.place}"$trajInfo',
          );
        }

        final trajCount = markerData.markers
            .where((m) => m.hasAITrajectory)
            .length;
        if (trajCount > 0) {
          debugPrint('🎯 $trajCount markers have AI trajectories');
        }
      }

      bool markersChanged =
          markerData.markers.length != threatMarkers.length ||
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
            _syncFilterTypes(markerData.markers);
            _fromCache = false;
          });
        }
        _addThreatHistoryEntry(markerData.counts);
        debugPrint(
          'Markers updated: ${markerData.markers.length} threat markers',
        );
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
    _threatHistory.add(
      ThreatHistoryEntry(timestamp: now, counts: Map<String, int>.from(counts)),
    );
    if (_threatHistory.length > 12) {
      _threatHistory.removeAt(0);
    }
  }

  void _syncFilterTypes(List<ThreatMarker> markers) {
    for (final marker in markers) {
      _filterableThreatTypes.add(marker.threatType);
    }
  }

  List<ThreatMarker> _applyThreatFilter(List<ThreatMarker> markers) {
    if (_visibleThreatTypes.isEmpty) return markers;
    return markers
        .where((marker) => _visibleThreatTypes.contains(marker.threatType))
        .toList();
  }

  // Cached filtered marker list — so identical() check in _buildMarkerTapTargets works
  List<ThreatMarker>? _cachedFilteredMarkers;
  List<ThreatMarker>? _lastSourceMarkers;
  int _lastVisibleTypesHash = 0;

  List<ThreatMarker> _getVisibleMarkers() {
    final typesHash = _visibleThreatTypes.length;
    if (_cachedFilteredMarkers != null &&
        identical(_lastSourceMarkers, threatMarkers) &&
        _lastVisibleTypesHash == typesHash) {
      return _cachedFilteredMarkers!;
    }
    _lastSourceMarkers = threatMarkers;
    _lastVisibleTypesHash = typesHash;
    _cachedFilteredMarkers = _applyThreatFilter(threatMarkers);
    return _cachedFilteredMarkers!;
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final colors = MapColors(isDark: isDark);
    final visibleMarkers = _getVisibleMarkers();
    _currentVisibleMarkers = visibleMarkers;

    return Stack(
      children: [
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
                            Text(
                              'Завантаження карти...',
                              style: TextStyle(color: colors.textSecondary),
                            ),
                          ],
                        ),
                      )
                    : error != null && lastUpdate == null
                    ? _buildError(colors)
                    : _buildMap(colors, visibleMarkers),
              ),
            ],
          ),
        ),

        // ===== BALLISTIC THREAT OVERLAY =====
        if (_ballisticThreatActive)
          BallisticThreatOverlay(
            onDismiss: () {
              _ballisticController.stop();
              _ballisticController.reset();
              _ballisticTimer?.cancel();
              setState(() => _ballisticThreatActive = false);
            },
          ),

        // ===== ALL CLEAR OVERLAY =====
        if (_ballisticAllClear)
          AnimatedBuilder(
            animation: _allClearController,
            builder: (context, child) => AllClearOverlay(
              progress: _allClearAnimation.value,
              message: _ballisticMessage,
            ),
          ),

        // Legend (внизу по центру) + індикатор джерела даних
        Positioned(
          bottom: 24,
          left: 0,
          right: 0,
          child: MapLegend(
            colors: colors,
            fromCache: _fromCache,
            lastUpdate: lastUpdate,
          ),
        ),

        // ===== THREAT STATS WIDGET =====
        if (visibleMarkers.isNotEmpty)
          Positioned(
            top:
                widget.appBarOverlayHeight +
                MediaQuery.of(context).padding.top +
                ((_ballisticThreatActive || _allClearController.value > 0)
                    ? 80
                    : 8),
            right: 12,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 300),
              curve: Curves.easeOut,
              child: ThreatStatsPanel(
                colors: colors,
                visibleMarkers: visibleMarkers,
                onTap: () => _showThreatStatsDialog(colors, visibleMarkers),
              ),
            ),
          ),

        // ===== OPERATOR MODE TOGGLE (Debug only) =====
        if (kDebugMode)
          Positioned(
            top: widget.appBarOverlayHeight + MediaQuery.of(context).padding.top + 8,
            left: 12,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                MapOperatorToggle(
                  colors: colors,
                  onToggle: _toggleOperatorMode,
                ),
                if (_operatorModeEnabled) ...[
                  const SizedBox(height: 8),
                  MapOperatorPanel(
                    colors: colors,
                    onRefresh: () {
                      _fetchAlarms();
                      _fetchThreatMarkers();
                    },
                  ),
                ],
              ],
            ),
          ),
      ],
    );
  }

  void _showThreatStatsDialog(
    MapColors colors,
    List<ThreatMarker> visibleMarkers,
  ) {
    showThreatStatsDialog(
      context,
      colors: colors,
      threatMarkers: threatMarkers,
      filterableThreatTypes: _filterableThreatTypes,
      visibleThreatTypes: _visibleThreatTypes,
      onFilterToggled: (type, selected) {
        setState(() {
          if (selected) {
            _visibleThreatTypes.add(type);
          } else {
            _visibleThreatTypes.remove(type);
          }
        });
      },
      threatHistory: _threatHistory,
      timeRangeMinutes: _timeRange,
    );
  }

  Widget _buildError(MapColors colors) {
    return Center(
      child: Container(
        margin: const EdgeInsets.all(32),
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: colors.panelBg.withValues(alpha: 0.9),
          borderRadius: BorderRadius.circular(24),
          border: Border.all(color: colors.panelBorder),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, color: Colors.red, size: 48),
            const SizedBox(height: 16),
            Text(
              error!,
              textAlign: TextAlign.center,
              style: TextStyle(color: colors.textSecondary),
            ),
            const SizedBox(height: 24),
            TextButton(
              onPressed: () {
                setState(() => isLoading = true);
                _fetchAlarms();
                _fetchThreatMarkers();
              },
              child: Text(
                'Спробувати ще раз',
                style: TextStyle(color: colors.textAccent),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Get tile URL for the current theme (CARTO CDN with retina + local-language labels)
  String _getTileUrl(bool isDark) {
    if (isDark) {
      return 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png';
    } else {
      return 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}@2x.png';
    }
  }

  Widget _buildMap(MapColors colors, List<ThreatMarker> visibleMarkers) {
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
          flags:
              InteractiveFlag.drag |
              InteractiveFlag.pinchZoom |
              InteractiveFlag.doubleTapZoom,
          enableMultiFingerGestureRace: false,
          rotationThreshold: 999999.0, // Effectively disable rotation
          cursorKeyboardRotationOptions:
              CursorKeyboardRotationOptions.disabled(),
        ),
        // Use containCenter instead of contain to avoid assertion errors
        cameraConstraint: CameraConstraint.containCenter(
          bounds: LatLngBounds(
            const LatLng(44.0, 20.0), // SW
            const LatLng(53.0, 42.0), // NE
          ),
        ),
        onPositionChanged: (position, hasGesture) {
          final oldZoom = _currentZoom;
          final newZoom = position.zoom;
          _currentZoom =
              newZoom; // Always update immediately (used by _svgOpacity getter)

          // Pause/resume pulse in transition zone to free raster thread
          final inTransition =
              newZoom >= _svgFadeStartZoom - 1.0 &&
              newZoom <= _svgFadeEndZoom + 1.0;
          if (inTransition != _pulseInTransitionZone) {
            _pulseInTransitionZone = inTransition;
            _updatePulseAnimation();
          }

          // Debounce rebuilds during active gesture to batch zoom changes
          final needsRebuild =
              (newZoom - oldZoom).abs() > 0.5 ||
              (oldZoom < _svgFadeStartZoom) != (newZoom < _svgFadeStartZoom) ||
              (oldZoom >= _svgFadeEndZoom) != (newZoom >= _svgFadeEndZoom);
          if (needsRebuild) {
            if (hasGesture) {
              // During active pinch: debounce to avoid rapid rebuilds
              _zoomDebounceTimer?.cancel();
              _zoomDebounceTimer = Timer(const Duration(milliseconds: 80), () {
                if (mounted) setState(() {});
              });
            } else {
              // Programmatic zoom: update immediately
              _zoomDebounceTimer?.cancel();
              setState(() {});
            }
          }
        },
        // Rotation is already disabled via rotationThreshold: 999999.0
        // No onMapEvent handler needed — avoids unnecessary event cycle
        onTap: (tapPosition, latLng) => _onMapTap(tapPosition, latLng),
      ),
      children: [
        // Map tiles (CartoDB - free, no API key needed)
        TileLayer(
          urlTemplate: _getTileUrl(isDark),
          subdomains: const ['a', 'b', 'c', 'd'],
          userAgentPackageName: 'com.neptunalarm.neptun_alarm_app',
          maxZoom: 18,
        ),
        // SVG overlay — opacity passed directly to painter (avoids GPU saveLayer)
        if (_showSvgLayer && _statePathsCache.isNotEmpty)
          RepaintBoundary(
            child: SvgMapLayer(
              statePathsCache: _statePathsCache,
              districtPathsCache: _districtPathsCache,
              stateAlarms: stateAlarms,
              districtAlarms: districtAlarms,
              stateThreatTypes: stateThreatTypes,
              threatMarkers: visibleMarkers,
              mapColors: colors,
              opacity: _svgOpacity.clamp(0.0, 1.0),
              onMarkerTap: _showMarkerInfo,
            ),
          ),
        // Pulse layer — opacity passed directly to painter
        if (_showSvgLayer && _statePathsCache.isNotEmpty)
          RepaintBoundary(
            child: PulseAlarmLayer(
              statePathsCache: _statePathsCache,
              districtPathsCache: _districtPathsCache,
              stateAlarms: stateAlarms,
              districtAlarms: districtAlarms,
              pulseAnimation: _pulseAnimation,
              mapColors: colors,
              opacity: _svgOpacity.clamp(0.0, 1.0),
            ),
          ),
        // Labels and markers layer - always visible regardless of SVG opacity
        if (_showMarkersLayer)
          RepaintBoundary(
            child: LabelsMarkersLayer(
              threatMarkers: visibleMarkers,
              mapColors: colors,
              onMarkerTap: _showMarkerInfo,
            ),
          ),
        // Invisible tap targets for marker taps (reliable hit testing)
        MarkerLayer(markers: _buildMarkerTapTargets(visibleMarkers)),
      ],
    );
  }

  // Cached marker tap targets to avoid rebuilding on every frame
  List<ThreatMarker>? _lastTapTargetMarkers;
  List<Marker>? _cachedTapTargets;

  List<Marker> _buildMarkerTapTargets(List<ThreatMarker> markers) {
    if (identical(markers, _lastTapTargetMarkers) &&
        _cachedTapTargets != null) {
      return _cachedTapTargets!;
    }
    _lastTapTargetMarkers = markers;
    _cachedTapTargets = markers
        .map(
          (m) => Marker(
            point: LatLng(m.lat, m.lng),
            width: 44,
            height: 44,
            child: GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: () => _showMarkerInfo(m),
              child: const SizedBox.expand(),
            ),
          ),
        )
        .toList();
    return _cachedTapTargets!;
  }

  void _onMapTap(TapPosition tapPosition, LatLng latLng) {
    const tapToleranceKm = 50.0;
    final zoomFactor = math.pow(2, _currentZoom - 6).toDouble();
    final tolerance = tapToleranceKm / zoomFactor;

    ThreatMarker? tappedMarker;
    double minDist = double.infinity;

    for (final marker in _currentVisibleMarkers) {
      final dLat = marker.lat - latLng.latitude;
      final dLng = marker.lng - latLng.longitude;
      final dist = math.sqrt(dLat * dLat + dLng * dLng) * 111.0;
      if (dist < tolerance && dist < minDist) {
        minDist = dist;
        tappedMarker = marker;
      }
    }

    if (tappedMarker != null) {
      _showMarkerInfo(tappedMarker);
    }
  }

  void _showMarkerInfo(ThreatMarker marker) {
    showMarkerInfoSheet(
      context,
      marker,
      isModerator: ModeratorService.instance.isModerator,
      onDelete: _confirmDeleteMarker,
    );
  }

  void _confirmDeleteMarker(ThreatMarker marker) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: isDark ? const Color(0xFF2A2A2A) : Colors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Text(
          'Видалити мітку?',
          style: TextStyle(color: isDark ? Colors.white : Colors.black87),
        ),
        content: Text(
          'Ця мітка буде видалена з карти для всіх користувачів.',
          style: TextStyle(color: isDark ? Colors.grey[300] : Colors.grey[700]),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text(
              'Скасувати',
              style: TextStyle(
                color: isDark ? Colors.grey[400] : Colors.grey[600],
              ),
            ),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(ctx); // close dialog
              Navigator.pop(context); // close bottom sheet
              _deleteMarker(marker);
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red.shade700,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(10),
              ),
            ),
            child: const Text('Видалити'),
          ),
        ],
      ),
    );
  }

  Future<void> _deleteMarker(ThreatMarker marker) async {
    try {
      final secret = await ModeratorService.instance.getSecret();
      if (secret == null || secret.isEmpty) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Помилка: секрет модератора не знайдено'),
          ),
        );
        return;
      }

      final body = <String, dynamic>{
        'lat': marker.lat,
        'lng': marker.lng,
        'text': marker.text,
      };
      if (marker.id != null) body['id'] = marker.id;

      final response = await http
          .post(
            Uri.parse(ApiConfig.adminMarkersDelete),
            headers: {
              'Content-Type': 'application/json',
              'X-Auth-Secret': secret,
            },
            body: json.encode(body),
          )
          .timeout(const Duration(seconds: 10));

      if (!mounted) return;

      if (response.statusCode == 200) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Мітку видалено'),
            backgroundColor: Colors.green,
            duration: Duration(seconds: 2),
          ),
        );
        _fetchThreatMarkers();
      } else {
        final data = json.decode(utf8.decode(response.bodyBytes));
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Помилка: ${data['error'] ?? 'Невідома помилка'}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } catch (e) {
      debugPrint('❌ deleteMarker error: $e');
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Помилка з\'єднання'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

}

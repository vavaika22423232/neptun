// ignore_for_file: deprecated_member_use
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'dart:ui' as ui;
import 'dart:convert';
import 'dart:async';
import 'dart:math' as math;
import 'package:http/http.dart' as http;
import 'package:jovial_svg/jovial_svg.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart' hide Path;
import '../data/ukraine_region_paths.dart';
import '../data/ukraine_district_paths.dart';
import '../utils/svg_path_parser.dart';
import '../services/ballistic_alert_service.dart';
import '../services/widget_service.dart';

// ===== МЕНЕДЖЕР ІКОНОК ЗАГРОЗ =====
class ThreatIconManager {
  static final ThreatIconManager _instance = ThreatIconManager._internal();
  factory ThreatIconManager() => _instance;
  ThreatIconManager._internal();
  
  final Map<String, ui.Image?> _icons = {};
  bool _isLoading = false;
  bool _isLoaded = false;
  
  static const Map<String, String> iconAssets = {
    'shahed': 'assets/icons/shahed3.png',
    'raketa': 'assets/icons/icon_balistic.svg',
    'avia': 'assets/icons/avia.png',
    'artillery': 'assets/icons/artillery.png',
    'obstril': 'assets/icons/icon_obstril.svg',
    'fpv': 'assets/icons/fpv.png',
    'pusk': 'assets/icons/icon_balistic.svg',
    'kab': 'assets/icons/icon_missile.svg',
    'rszv': 'assets/icons/rszv.png',
    'rozved': 'assets/icons/rozvedka2.png',
    'vibuh': 'assets/icons/icon_vibuh.svg',
    'trivoga': 'assets/icons/trivoga.png',
    'vidboi': 'assets/icons/vidboi.png',
    'default': 'assets/icons/default.png',
  };
  
  bool get isLoaded => _isLoaded;
  
  // Render at higher resolution for better quality
  static const int iconSize = 64;
  
  Future<void> loadIcons() async {
    if (_isLoading || _isLoaded) return;
    _isLoading = true;
    
    for (final entry in iconAssets.entries) {
      try {
        final path = entry.value;
        if (path.endsWith('.svg')) {
          // Load SVG and render to ui.Image using jovial_svg
          final svgString = await rootBundle.loadString(path);
          final si = ScalableImage.fromSvgString(svgString);
          
          // Render at 2x resolution for crisp icons
          final double targetSize = iconSize.toDouble();
          final recorder = ui.PictureRecorder();
          final canvas = Canvas(recorder, Rect.fromLTWH(0, 0, targetSize, targetSize));
          
          // Calculate uniform scale to fit in square, maintaining aspect ratio
          final svgWidth = si.viewport.width;
          final svgHeight = si.viewport.height;
          final scale = targetSize / (svgWidth > svgHeight ? svgWidth : svgHeight);
          
          // Center the SVG in the square
          final scaledWidth = svgWidth * scale;
          final scaledHeight = svgHeight * scale;
          final offsetX = (targetSize - scaledWidth) / 2;
          final offsetY = (targetSize - scaledHeight) / 2;
          
          canvas.translate(offsetX, offsetY);
          canvas.scale(scale, scale);
          si.paint(canvas);
          
          final picture = recorder.endRecording();
          final image = await picture.toImage(iconSize, iconSize);
          _icons[entry.key] = image;
        } else {
          // Load PNG at higher resolution
          final data = await rootBundle.load(path);
          final codec = await ui.instantiateImageCodec(
            data.buffer.asUint8List(),
            targetWidth: iconSize,
            targetHeight: iconSize,
          );
          final frame = await codec.getNextFrame();
          _icons[entry.key] = frame.image;
        }
      } catch (e) {
        debugPrint('Failed to load icon ${entry.key}: $e');
        _icons[entry.key] = null;
      }
    }
    
    _isLoaded = true;
    _isLoading = false;
  }
  
  ui.Image? getIcon(String threatType) {
    return _icons[threatType] ?? _icons['default'];
  }
}

// ===== КОЛЬОРИ КАРТИ =====
// Кольори карти з підтримкою світлої та темної теми
class MapColors {
  final bool isDark;
  
  MapColors({required this.isDark});
  
  // Фон
  Color get bgMain => isDark ? const Color(0xFF141414) : const Color(0xFFFAF9F7);
  Color get bgGradientMid => isDark ? const Color(0xFF1F1F1F) : const Color(0xFFF5F3F0);
  Color get bgGradientEnd => isDark ? const Color(0xFF1F1F1F) : const Color(0xFFFCFBF9);
  
  // Області - нормальний стан
  Color get normalFill => isDark ? const Color(0xFF262626) : const Color(0xFFF0EBE3);
  Color get normalStroke => isDark ? const Color(0xFF525252) : const Color(0xFFD4C9BC);
  
  // Області - тривога
  Color get alarmFillState => isDark ? const Color(0xFF991B1B) : const Color(0xFFFECACA);
  Color get alarmStrokeState => isDark ? const Color(0xFFB45555) : const Color(0xFFF87171);
  
  // Райони - нормальний стан
  Color get districtNormalFill => Colors.transparent;
  Color get districtNormalStroke => isDark 
      ? const Color(0x263B82F6) 
      : const Color(0x40A89880);
  
  // Райони - тривога
  Color get districtAlarmFill => isDark ? const Color(0xFFDC2626) : const Color(0xFFEF4444);
  Color get districtAlarmStroke => isDark ? const Color(0xFFF87171) : const Color(0xFFDC2626);
  
  // Активна тривога (для пульсації)
  Color get alarmActive => const Color(0xFFDC2626);
  
  // Границі
  Color get borderDark => isDark ? const Color(0xFF454545) : const Color(0xFFDDD5CA);
  
  // Текст
  Color get textPrimary => isDark ? Colors.white : const Color(0xFF3D3529);
  Color get textSecondary => isDark ? const Color(0xFFA3A3A3) : const Color(0xFF78716C);
  Color get textAccent => isDark ? const Color(0xFF3B82F6) : const Color(0xFF9A7B4F);
  
  // Панелі
  Color get panelBg => isDark 
      ? const Color(0xFF1F1F1F).withOpacity(0.95) 
      : const Color(0xFFFFFEFC).withOpacity(0.95);
  Color get panelBorder => isDark ? const Color(0xFF454545) : const Color(0xFFE8E2D9);
  
  // Підписи областей
  Color get labelColor => isDark 
      ? Colors.white.withOpacity(0.85) 
      : const Color(0xFF3D3529).withOpacity(0.9);
  Color get labelShadow => isDark 
      ? Colors.black.withOpacity(0.8) 
      : const Color(0xFFFFFEFC).withOpacity(0.9);
}

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

// ===== ТИПИ ЗАГРОЗ (маркери) =====
class ThreatType {
  static const String shahed = 'shahed';
  static const String raketa = 'raketa';
  static const String avia = 'avia';
  static const String artillery = 'artillery';
  static const String obstril = 'obstril';
  static const String fpv = 'fpv';
  static const String pusk = 'pusk';
  static const String kab = 'kab';
  static const String rszv = 'rszv';
  static const String rozved = 'rozved';
  static const String vibuh = 'vibuh';
  static const String alarm = 'alarm';
  static const String alarmCancel = 'alarm_cancel';
  
  static const Map<String, String> names = {
    shahed: '🛩️ Шахеди/БПЛА',
    raketa: '🚀 Ракети',
    avia: '✈️ Авіація',
    artillery: '💥 Артилерія',
    obstril: '💥 Обстріл',
    fpv: '🎯 FPV дрони',
    pusk: '🚀 Пуски',
    kab: '💣 КАБи',
    rszv: '💣 РСЗВ',
    rozved: '🔍 Розвідники',
    vibuh: '💥 Вибухи',
    alarm: '🚨 Тривога',
    alarmCancel: '✅ Відбій',
  };
  
  static const Map<String, IconData> icons = {
    shahed: Icons.flight,
    raketa: Icons.rocket_launch,
    avia: Icons.airplanemode_active,
    artillery: Icons.local_fire_department,
    obstril: Icons.local_fire_department,
    fpv: Icons.sports_esports,
    pusk: Icons.rocket,
    kab: Icons.dangerous,
    rszv: Icons.whatshot,
    rozved: Icons.visibility,
    vibuh: Icons.warning,
    alarm: Icons.notifications_active,
    alarmCancel: Icons.check_circle,
  };
  
  static Color getColor(String type) {
    switch (type) {
      case shahed:
      case fpv:
      case rozved:
        return Colors.orange;
      case raketa:
      case pusk:
      case kab:
      case rszv:
        return Colors.red;
      case avia:
        return Colors.purple;
      case artillery:
      case obstril:
      case vibuh:
        return Colors.amber;
      case alarm:
        return Colors.red;
      case alarmCancel:
        return Colors.green;
      default:
        return Colors.white;
    }
  }
}

// ===== ТОЧКА ТРАЄКТОРІЇ =====
class TrajectoryPoint {
  final double lat;
  final double lng;
  final double etaMinutes;
  final double fraction;
  
  TrajectoryPoint({
    required this.lat,
    required this.lng,
    required this.etaMinutes,
    required this.fraction,
  });
  
  factory TrajectoryPoint.fromJson(Map<String, dynamic> json) {
    return TrajectoryPoint(
      lat: double.tryParse(json['lat']?.toString() ?? '0') ?? 0,
      lng: double.tryParse(json['lng']?.toString() ?? '0') ?? 0,
      etaMinutes: double.tryParse(json['eta_minutes']?.toString() ?? '0') ?? 0,
      fraction: double.tryParse(json['fraction']?.toString() ?? '0') ?? 0,
    );
  }
}

// ===== AI TRAJECTORY (новий формат з сервера) =====
class AITrajectory {
  final double startLat;
  final double startLng;
  final double endLat;
  final double endLng;
  final String sourceName;
  final String targetName;
  final bool predicted;

  AITrajectory({
    required this.startLat,
    required this.startLng,
    required this.endLat,
    required this.endLng,
    required this.sourceName,
    required this.targetName,
    this.predicted = false,
  });

  factory AITrajectory.fromJson(Map<String, dynamic> json) {
    final start = json['start'] as List?;
    final end = json['end'] as List?;
    return AITrajectory(
      startLat: (start?[0] as num?)?.toDouble() ?? 0,
      startLng: (start?[1] as num?)?.toDouble() ?? 0,
      endLat: (end?[0] as num?)?.toDouble() ?? 0,
      endLng: (end?[1] as num?)?.toDouble() ?? 0,
      sourceName: json['source_name'] ?? '',
      targetName: json['target_name'] ?? '',
      predicted: json['predicted'] == true,
    );
  }

  bool get isValid {
    // Trajectory is valid if start and end are different (at least 0.01 degree apart)
    return (startLat - endLat).abs() > 0.01 || (startLng - endLng).abs() > 0.01;
  }
}

// ===== МАРКЕР ЗАГРОЗИ =====
class ThreatMarker {
  final double lat;
  final double lng;
  final String threatType;
  final String place;
  final String text;
  final String date;
  final List<TrajectoryPoint>? projectedPath; // Для старих траєкторій
  final AITrajectory? trajectory; // Для AI траєкторій
  final double? etaMinutes;
  final double? distanceKm;
  
  ThreatMarker({
    required this.lat,
    required this.lng,
    required this.threatType,
    this.place = '',
    this.text = '',
    this.date = '',
    this.projectedPath,
    this.trajectory,
    this.etaMinutes,
    this.distanceKm,
  });
  
  factory ThreatMarker.fromJson(Map<String, dynamic> json) {
    // Парсимо стару траєкторію якщо є
    List<TrajectoryPoint>? path;
    if (json['projected_path'] != null && json['projected_path'] is List) {
      path = (json['projected_path'] as List)
          .map((p) => TrajectoryPoint.fromJson(p))
          .toList();
    }
    
    // Парсимо нову AI траєкторію якщо є
    AITrajectory? aiTrajectory;
    if (json['trajectory'] != null && json['trajectory'] is Map) {
      aiTrajectory = AITrajectory.fromJson(json['trajectory']);
    }
    
    return ThreatMarker(
      lat: double.tryParse(json['lat']?.toString() ?? '0') ?? 0,
      lng: double.tryParse(json['lng']?.toString() ?? '0') ?? 0,
      threatType: json['threat_type'] ?? 'default',
      place: json['place'] ?? '',
      text: json['text'] ?? '',
      date: json['date'] ?? '',
      projectedPath: path,
      trajectory: aiTrajectory,
      etaMinutes: double.tryParse(json['eta_minutes']?.toString() ?? ''),
      distanceKm: double.tryParse(json['distance_km']?.toString() ?? ''),
    );
  }
  
  bool get hasTrajectory => 
      (projectedPath != null && projectedPath!.length > 1) ||
      (trajectory != null && trajectory!.isValid);
      
  bool get hasAITrajectory => trajectory != null && trajectory!.isValid;
}

// ===== MAP BOUNDS (Україна) =====
class MapBounds {
  static const double minLat = 44.2;
  static const double maxLat = 52.4;
  static const double minLng = 22.0;
  static const double maxLng = 40.2;
  
  static Offset latLngToPercent(double lat, double lng) {
    final x = (lng - minLng) / (maxLng - minLng);
    final y = (maxLat - lat) / (maxLat - minLat);
    return Offset(x.clamp(0.0, 1.0), y.clamp(0.0, 1.0));
  }
  
  static bool isInBounds(double lat, double lng) {
    return lat >= minLat && lat <= maxLat && lng >= minLng && lng <= maxLng;
  }
}

// ===== ГОЛОВНА СТОРІНКА КАРТИ =====
class NativeMapPage extends StatefulWidget {
  const NativeMapPage({super.key});

  @override
  State<NativeMapPage> createState() => _NativeMapPageState();
}

class _NativeMapPageState extends State<NativeMapPage> with TickerProviderStateMixin {
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
  
  // Інтервали оновлення (зменшено для швидшого оновлення)
  static const int alarmUpdateInterval = 5; // секунд
  static const int markerUpdateInterval = 5; // секунд
  static const int timeRange = 15; // хвилин для маркерів
  
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
    
    super.dispose();
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
    try {
      final response = await http.get(
        Uri.parse('https://neptun.in.ua/api/alarms/all'),
      ).timeout(const Duration(seconds: 8));
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        
        final Map<String, bool> newStateAlarms = {};
        final Map<String, bool> newDistrictAlarms = {};
        final Map<String, String> newStateThreatTypes = {};
        final Set<String> currentBallisticRegions = {};
        int stateCount = 0;
        int districtCount = 0;
        
        // Назви областей для повідомлень
        const regionNames = <String, String>{
          '1': 'Вінницька область',
          '2': 'Волинська область',
          '3': 'Дніпропетровська область',
          '4': 'Донецька область',
          '5': 'Житомирська область',
          '6': 'Закарпатська область',
          '7': 'Запорізька область',
          '8': 'Івано-Франківська область',
          '9': 'Київська область',
          '10': 'Кіровоградська область',
          '11': 'Луганська область',
          '12': 'Львівська область',
          '13': 'Миколаївська область',
          '14': 'Одеська область',
          '15': 'Полтавська область',
          '16': 'Рівненська область',
          '17': 'Сумська область',
          '18': 'Тернопільська область',
          '19': 'Харківська область',
          '20': 'Херсонська область',
          '21': 'Хмельницька область',
          '22': 'Черкаська область',
          '23': 'Чернівецька область',
          '24': 'Чернігівська область',
          '25': 'м. Київ',
          '26': 'АР Крим',
          '27': 'м. Севастополь',
        };
        
        if (data is List) {
          // Формат: [{regionId: X, regionType: "State"/"District", activeAlerts: [...]}]
          for (final region in data) {
            final regionId = region['regionId']?.toString();
            final regionType = region['regionType'] ?? '';
            final activeAlerts = region['activeAlerts'] as List? ?? [];
            final regionName = region['regionName']?.toString() ?? regionNames[regionId] ?? '';
            
            if (regionId == null) continue;
            
            final hasAlarm = activeAlerts.isNotEmpty;
            
            if (regionType == 'State') {
              newStateAlarms[regionId] = hasAlarm;
              if (hasAlarm) {
                stateCount++;
                // Зберігаємо тип загрози для іконки
                for (final alert in activeAlerts) {
                  final alertType = alert['type']?.toString() ?? '';
                  debugPrint('🔔 Alert type: "$alertType" for region: $regionName ($regionId)');
                  if (alertType == 'DRONES' || alertType.contains('DRONE')) {
                    newStateThreatTypes[regionId] = ThreatType.shahed;
                  } else if (alertType == 'BALLISTIC' || alertType == 'MISSILE' || alertType.contains('BALLISTIC')) {
                    newStateThreatTypes[regionId] = ThreatType.raketa;
                    // Відстежуємо балістичну загрозу
                    currentBallisticRegions.add(regionName.isNotEmpty ? regionName : regionId);
                    debugPrint('🚀🚀🚀 BALLISTIC DETECTED: $regionName');
                  } else if (alertType == 'AIR') {
                    newStateThreatTypes[regionId] = ThreatType.avia;
                  }
                }
              }
            } else if (regionType == 'District') {
              newDistrictAlarms[regionId] = hasAlarm;
              if (hasAlarm) {
                districtCount++;
                // Перевіряємо балістику і для районів
                for (final alert in activeAlerts) {
                  final alertType = alert['type']?.toString() ?? '';
                  if (alertType == 'BALLISTIC' || alertType == 'MISSILE' || alertType.contains('BALLISTIC')) {
                    currentBallisticRegions.add(regionName.isNotEmpty ? regionName : regionId);
                    debugPrint('🚀🚀🚀 BALLISTIC DETECTED (district): $regionName');
                  }
                }
              }
            }
          }
        } else if (data is Map) {
          // Альтернативний формат: {"3": true, "4": false}
          data.forEach((key, value) {
            final regionId = key.toString();
            bool hasAlarm = false;
            
            if (value is bool) {
              hasAlarm = value;
            } else if (value is Map && value.containsKey('alarm')) {
              hasAlarm = value['alarm'] == true;
            }
            
            // За замовчуванням вважаємо як область
            newStateAlarms[regionId] = hasAlarm;
            if (hasAlarm) stateCount++;
          });
        }
        
        // Перевіряємо чи дані змінились
        bool alarmsChanged = newStateAlarms.length != stateAlarms.length ||
                              newDistrictAlarms.length != districtAlarms.length ||
                              stateCount != stateAlarmCount ||
                              districtCount != districtAlarmCount;
        
        if (!alarmsChanged) {
          // Перевіряємо значення
          for (final key in newStateAlarms.keys) {
            if (stateAlarms[key] != newStateAlarms[key]) {
              alarmsChanged = true;
              break;
            }
          }
        }
        
        if (alarmsChanged || isLoading) {
          // Перевіряємо балістичні загрози
          final newBallisticRegions = currentBallisticRegions.difference(_previousBallisticRegions);
          final clearedBallisticRegions = _previousBallisticRegions.difference(currentBallisticRegions);
          
          // Показуємо ефект для нових балістичних загроз
          if (newBallisticRegions.isNotEmpty && !isLoading) {
            final regionsText = newBallisticRegions.join(', ');
            showBallisticThreat(region: regionsText);
          }
          
          // Показуємо відбій для зняких балістичних загроз
          if (clearedBallisticRegions.isNotEmpty && currentBallisticRegions.isEmpty && !isLoading) {
            final regionsText = clearedBallisticRegions.join(', ');
            showBallisticAllClear(region: regionsText);
          }
          
          // Оновлюємо стан
          _previousBallisticRegions = currentBallisticRegions;
          
          setState(() {
            stateAlarms = newStateAlarms;
            districtAlarms = newDistrictAlarms;
            stateThreatTypes = newStateThreatTypes;
            stateAlarmCount = stateCount;
            districtAlarmCount = districtCount;
            lastUpdate = DateTime.now();
            isLoading = false;
            error = null;
          });
          debugPrint('Alarms updated: $stateCount oblasts, $districtCount districts');
          if (currentBallisticRegions.isNotEmpty) {
            debugPrint('🚀 Ballistic threats active in: $currentBallisticRegions');
          }
          
          // Оновлюємо віджет на робочому столі
          _updateHomeWidget(stateCount > 0, stateCount);
        } else {
          debugPrint('Alarms unchanged, skipping setState');
        }
      } else {
        throw Exception('HTTP ${response.statusCode}');
      }
    } catch (e) {
      debugPrint('Error fetching alarms: $e');
      if (mounted && lastUpdate == null) {
        setState(() {
          error = 'Не вдалося завантажити дані';
          isLoading = false;
        });
      }
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
    try {
      final response = await http.get(
        Uri.parse('https://neptun.in.ua/data?timeRange=$timeRange'),
      ).timeout(const Duration(seconds: 8));
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        
        final List<ThreatMarker> newMarkers = [];
        final Map<String, int> newCounts = {};
        
        // === CHECK BALLISTIC THREAT FROM API ===
        if (data is Map && data['ballistic_threat'] != null) {
          final ballisticThreat = data['ballistic_threat'];
          final isActive = ballisticThreat['active'] == true;
          final region = ballisticThreat['region'] as String?;
          
          debugPrint('🚀 Ballistic threat from API: active=$isActive, region=$region');
          
          if (isActive && !BallisticAlertService().isBallisticThreatActive) {
            BallisticAlertService().triggerBallisticThreat(region: region);
          } else if (!isActive && BallisticAlertService().isBallisticThreatActive) {
            BallisticAlertService().triggerBallisticAllClear(region: region);
          }
        }
        
        // Підтримка різних форматів
        List? markersData;
        if (data is Map) {
          markersData = data['tracks'] ?? data['items'] ?? [];
        } else if (data is List) {
          markersData = data;
        }
        
        if (markersData != null) {
          debugPrint('📊 Received ${markersData.length} markers from API:');
          for (final item in markersData) {
            if (item is! Map) continue;
            
            final lat = double.tryParse(item['lat']?.toString() ?? '');
            final lng = double.tryParse(item['lng']?.toString() ?? '');
            
            if (lat == null || lng == null) continue;
            if (!MapBounds.isInBounds(lat, lng)) continue;
            
            final itemMap = Map<String, dynamic>.from(item);
            final marker = ThreatMarker.fromJson(itemMap);
            newMarkers.add(marker);
            
            // Логуємо кожен маркер та траєкторію
            String trajInfo = '';
            if (marker.hasAITrajectory) {
              final t = marker.trajectory!;
              trajInfo = ' [AI TRAJ: ${t.sourceName} → ${t.targetName}${t.predicted ? " (прогноз)" : ""}]';
            }
            debugPrint('  📍 type="${marker.threatType}", place="${marker.place}"$trajInfo');
            
            newCounts[marker.threatType] = (newCounts[marker.threatType] ?? 0) + 1;
          }
          
          // Логуємо кількість траєкторій
          final trajCount = newMarkers.where((m) => m.hasAITrajectory).length;
          if (trajCount > 0) {
            debugPrint('🎯 $trajCount markers have AI trajectories');
          }
        }
        
        // Перевіряємо чи маркери змінились
        bool markersChanged = newMarkers.length != threatMarkers.length ||
                               newCounts.length != markerCounts.length;
        
        if (markersChanged) {
          setState(() {
            threatMarkers = newMarkers;
            markerCounts = newCounts;
          });
          debugPrint('Markers updated: ${newMarkers.length} threat markers');
        } else {
          debugPrint('Markers unchanged, skipping setState');
        }
      }
    } catch (e) {
      debugPrint('Error fetching threat markers: $e');
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
    final iconManager = ThreatIconManager();
    
    for (final marker in threatMarkers) {
      final pos = MapBounds.latLngToPercent(marker.lat, marker.lng);
      final x = pos.dx * viewBoxWidth;
      final y = pos.dy * viewBoxHeight;
      
      final color = ThreatType.getColor(marker.threatType);
      final icon = iconManager.getIcon(marker.threatType);
      
      // Обчислюємо кут повороту для маркера на основі траєкторії
      // ВАЖЛИВО: Іконка дрона за замовчуванням дивиться ВПРАВО (на схід)
      // Тому потрібно відняти π/2 (90°) від розрахованого кута
      double rotationAngle = 0.0;
      if (marker.hasAITrajectory) {
        final traj = marker.trajectory!;
        // dx = зміна долготи (схід +, захід -)
        // dy = зміна широти (північ +, південь -)
        final dx = traj.endLng - traj.startLng;
        final dy = traj.endLat - traj.startLat;
        // atan2(dx, dy) дає кут від півночі за годинниковою стрілкою
        // Віднімаємо π/2 бо іконка дивиться на схід, а не на північ
        rotationAngle = math.atan2(dx, dy) - math.pi / 2;
      } else if (marker.hasTrajectory && marker.projectedPath != null && marker.projectedPath!.length >= 2) {
        // Старий формат траєкторії
        final path = marker.projectedPath!;
        final lastIdx = path.length - 1;
        final dx = path[lastIdx].lng - path[lastIdx - 1].lng;
        final dy = path[lastIdx].lat - path[lastIdx - 1].lat;
        rotationAngle = math.atan2(dx, dy) - math.pi / 2;
      }
      
      if (icon != null && iconManager.isLoaded) {
        // Малюємо іконку з поворотом
        // Shahed icons are larger for better visibility
        final displaySize = marker.threatType == 'shahed' ? 10.0 : 7.0;
        
        canvas.save();
        canvas.translate(x, y);
        
        // Застосовуємо поворот якщо є траєкторія
        if (rotationAngle != 0.0) {
          canvas.rotate(rotationAngle);
        }
        
        final srcRect = Rect.fromLTWH(0, 0, icon.width.toDouble(), icon.height.toDouble());
        final dstRect = Rect.fromCenter(
          center: Offset.zero,
          width: displaySize,
          height: displaySize,
        );
        
        // Use filterQuality for smooth scaling
        final paint = Paint()..filterQuality = FilterQuality.high;
        canvas.drawImageRect(icon, srcRect, dstRect, paint);
        
        canvas.restore();
      } else {
        // Fallback: малюємо коло якщо іконка не завантажена
        final markerPaint = Paint()
          ..color = color.withOpacity(0.8)
          ..style = PaintingStyle.fill;
        canvas.drawCircle(Offset(x, y), 3.0, markerPaint);
        
        // Обводка
        final markerStroke = Paint()
          ..color = Colors.white.withOpacity(0.5)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 0.3;
        canvas.drawCircle(Offset(x, y), 3.0, markerStroke);
      }
    }
    
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
    
    // === THREAT MARKERS ===
    final markerSize = (24.0 * strokeScale).clamp(20.0, 48.0);
    
    for (final marker in threatMarkers) {
      final screenPos = camera.latLngToScreenOffset(
        LatLng(marker.lat, marker.lng),
      );
      
      // Skip if outside visible area
      if (screenPos.dx < -50 || screenPos.dx > size.width + 50 ||
          screenPos.dy < -50 || screenPos.dy > size.height + 50) {
        continue;
      }
      
      final color = ThreatType.getColor(marker.threatType);
      
      // Draw icon from cache
      final icon = ThreatIconManager()._icons[marker.threatType] ?? 
                   ThreatIconManager()._icons['default'];
      
      if (icon != null) {
        final srcRect = Rect.fromLTWH(0, 0, icon.width.toDouble(), icon.height.toDouble());
        final dstRect = Rect.fromCenter(center: screenPos, width: markerSize, height: markerSize);
        canvas.drawImageRect(icon, srcRect, dstRect, Paint());
      } else {
        // Fallback circle - larger
        final markerPaint = Paint()
          ..color = color.withOpacity(0.9)
          ..style = PaintingStyle.fill;
        canvas.drawCircle(screenPos, markerSize / 2, markerPaint);
        
        // Add border
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

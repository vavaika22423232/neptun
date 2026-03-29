import 'package:flutter/material.dart';

/// Сервіс для керування балістичними тривогами
/// Дозволяє показувати ефектні оповіщення на карті
class BallisticAlertService {
  static final BallisticAlertService _instance = BallisticAlertService._internal();
  factory BallisticAlertService() => _instance;
  BallisticAlertService._internal();

  // Callbacks для оповіщення UI
  final List<void Function(String? region)> _threatCallbacks = [];
  final List<void Function(String? region)> _allClearCallbacks = [];
  
  // Поточний стан
  bool _isBallisticThreatActive = false;
  String? _currentRegion;
  DateTime? _lastThreatTime;
  
  bool get isBallisticThreatActive => _isBallisticThreatActive;
  String? get currentRegion => _currentRegion;
  DateTime? get lastThreatTime => _lastThreatTime;
  
  /// Підписатися на оповіщення про балістичну загрозу
  void onBallisticThreat(void Function(String? region) callback) {
    _threatCallbacks.add(callback);
  }
  
  /// Підписатися на оповіщення про відбій
  void onBallisticAllClear(void Function(String? region) callback) {
    _allClearCallbacks.add(callback);
  }
  
  /// Відписатися від оповіщень
  void removeCallback(void Function(String? region) callback) {
    _threatCallbacks.remove(callback);
    _allClearCallbacks.remove(callback);
  }
  
  /// Мінімальний час (в секундах) перед тим як відбій може перекрити загрозу
  static const int _minThreatDurationSeconds = 10;
  
  /// Викликати балістичну загрозу
  void triggerBallisticThreat({String? region}) {
    _isBallisticThreatActive = true;
    _currentRegion = region;
    _lastThreatTime = DateTime.now();
    
    debugPrint('🚀 BallisticAlertService: Triggering threat for $region at $_lastThreatTime');
    
    for (final callback in _threatCallbacks) {
      callback(region);
    }
  }
  
  /// Викликати відбій балістичної загрози
  void triggerBallisticAllClear({String? region}) {
    // Захист: якщо загроза була менше ніж _minThreatDurationSeconds секунд тому,
    // ігноруємо відбій (щоб не перекривати загрозу)
    if (_lastThreatTime != null) {
      final elapsed = DateTime.now().difference(_lastThreatTime!).inSeconds;
      if (elapsed < _minThreatDurationSeconds) {
        debugPrint('⚠️ BallisticAlertService: Ignoring all-clear, threat was only ${elapsed}s ago (min: ${_minThreatDurationSeconds}s)');
        return;
      }
    }
    
    _isBallisticThreatActive = false;
    _currentRegion = null;
    
    debugPrint('✅ BallisticAlertService: All clear for $region');
    
    for (final callback in _allClearCallbacks) {
      callback(region);
    }
  }
  
  /// Перевірити чи це балістичне оповіщення за текстом
  static BallisticAlertType? detectAlertType(String message) {
    final lowerMessage = message.toLowerCase();
    
    // Пошук ключових слів для загрози балістики
    if (lowerMessage.contains('загроза балістики') ||
        lowerMessage.contains('загроза балистики') ||
        lowerMessage.contains('балістична загроза') ||
        lowerMessage.contains('ballistic threat') ||
        lowerMessage.contains('пуск') && lowerMessage.contains('балістик')) {
      return BallisticAlertType.threat;
    }
    
    // Пошук ключових слів для відбою
    if (lowerMessage.contains('відбій загрози балістики') ||
        lowerMessage.contains('відбій балістики') ||
        lowerMessage.contains('відбій балістичної') ||
        lowerMessage.contains('ballistic all clear')) {
      return BallisticAlertType.allClear;
    }
    
    return null;
  }
  
  /// Витягти назву регіону з повідомлення
  static String? extractRegion(String message) {
    // Типові паттерни: "Загроза балістики! Київська область"
    // або "Київська область - загроза балістики"
    
    final regionPatterns = [
      RegExp(r'([\w\-]+ська область)', caseSensitive: false),
      RegExp(r'(м\.\s*Київ)', caseSensitive: false),
      RegExp(r'(Київ(?:ська)?)', caseSensitive: false),
    ];
    
    for (final pattern in regionPatterns) {
      final match = pattern.firstMatch(message);
      if (match != null) {
        return match.group(1);
      }
    }
    
    return null;
  }
}

enum BallisticAlertType {
  threat,
  allClear,
}

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Сервіс "Режим сну" - управління сповіщеннями вночі
class SleepModeService {
  static final SleepModeService _instance = SleepModeService._internal();
  factory SleepModeService() => _instance;
  SleepModeService._internal();

  bool _isEnabled = false;
  int _startHour = 23;
  int _startMinute = 0;
  int _endHour = 7;
  int _endMinute = 0;
  
  bool _allowRockets = true;
  bool _allowDrones = false;
  bool _allowAllClear = false;

  bool get isEnabled => _isEnabled;
  int get startHour => _startHour;
  int get startMinute => _startMinute;
  int get endHour => _endHour;
  int get endMinute => _endMinute;
  bool get allowRockets => _allowRockets;
  bool get allowDrones => _allowDrones;
  bool get allowAllClear => _allowAllClear;

  Future<void> initialize() async {
    await _loadSettings();
  }

  Future<void> _loadSettings() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      _isEnabled = prefs.getBool('sleep_mode_enabled') ?? false;
      _startHour = prefs.getInt('sleep_mode_start_hour') ?? 23;
      _startMinute = prefs.getInt('sleep_mode_start_minute') ?? 0;
      _endHour = prefs.getInt('sleep_mode_end_hour') ?? 7;
      _endMinute = prefs.getInt('sleep_mode_end_minute') ?? 0;
      _allowRockets = prefs.getBool('sleep_mode_rockets') ?? true;
      _allowDrones = prefs.getBool('sleep_mode_drones') ?? false;
      _allowAllClear = prefs.getBool('sleep_mode_all_clear') ?? false;
    } catch (e) {
      debugPrint('Error loading sleep mode settings: $e');
    }
  }

  Future<void> setEnabled(bool enabled) async {
    _isEnabled = enabled;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('sleep_mode_enabled', enabled);
  }

  Future<void> setTimeRange(int startHour, int startMinute, int endHour, int endMinute) async {
    _startHour = startHour;
    _startMinute = startMinute;
    _endHour = endHour;
    _endMinute = endMinute;
    
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt('sleep_mode_start_hour', startHour);
    await prefs.setInt('sleep_mode_start_minute', startMinute);
    await prefs.setInt('sleep_mode_end_hour', endHour);
    await prefs.setInt('sleep_mode_end_minute', endMinute);
  }

  Future<void> setAlertFilters({bool? rockets, bool? drones, bool? allClear}) async {
    if (rockets != null) _allowRockets = rockets;
    if (drones != null) _allowDrones = drones;
    if (allClear != null) _allowAllClear = allClear;
    
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('sleep_mode_rockets', _allowRockets);
    await prefs.setBool('sleep_mode_drones', _allowDrones);
    await prefs.setBool('sleep_mode_all_clear', _allowAllClear);
  }

  /// Перевірити чи зараз час сну
  bool isInSleepTime() {
    if (!_isEnabled) return false;
    
    final now = DateTime.now();
    final currentMinutes = now.hour * 60 + now.minute;
    final startMinutes = _startHour * 60 + _startMinute;
    final endMinutes = _endHour * 60 + _endMinute;
    
    // Якщо кінець > початку (наприклад 23:00 - 07:00)
    if (startMinutes > endMinutes) {
      // Нічний режим: від startMinutes до 23:59 АБО від 00:00 до endMinutes
      return currentMinutes >= startMinutes || currentMinutes < endMinutes;
    } else {
      // Денний режим (наприклад 14:00 - 16:00)
      return currentMinutes >= startMinutes && currentMinutes < endMinutes;
    }
  }

  /// Перевірити чи потрібно блокувати сповіщення
  /// Повертає true якщо сповіщення потрібно заблокувати
  bool shouldBlockNotification(String body) {
    // Якщо не в режимі сну - не блокувати
    if (!isInSleepTime()) return false;
    
    final lowerBody = body.toLowerCase();
    
    // Перевіряємо тип загрози (ракети, КАБ, балістика — критичні)
    final isRocket = lowerBody.contains('ракет') || 
                     lowerBody.contains('балістичн') ||
                     lowerBody.contains('калібр') ||
                     lowerBody.contains('кинджал') ||
                     lowerBody.contains('каб') ||
                     lowerBody.contains('касет');
    final isDrone = lowerBody.contains('бпла') || 
                    lowerBody.contains('дрон') ||
                    lowerBody.contains('шахед');
    final isAllClear = lowerBody.contains('відбій');
    
    // Якщо це ракета і ракети дозволені - не блокувати
    if (isRocket && _allowRockets) return false;
    
    // Якщо це дрон і дрони дозволені - не блокувати
    if (isDrone && _allowDrones) return false;
    
    // Якщо це відбій і відбій дозволено - не блокувати
    if (isAllClear && _allowAllClear) return false;
    
    // Загальна тривога (без конкретного типу) - пропускаємо якщо ракети дозволені
    // Бо загальна тривога може бути про що завгодно
    if (!isRocket && !isDrone && !isAllClear && _allowRockets) {
      debugPrint('🌙 Sleep mode: allowing general alarm (rockets enabled)');
      return false;
    }
    
    // В усіх інших випадках - блокувати
    debugPrint('🌙 Sleep mode: blocking notification - isRocket=$isRocket, isDrone=$isDrone, isAllClear=$isAllClear');
    return true;
  }

  /// Статичний метод для перевірки з SharedPreferences (для background handler)
  static Future<bool> shouldBlockNotificationStatic(String body) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final isEnabled = prefs.getBool('sleep_mode_enabled') ?? false;
      
      if (!isEnabled) return false;
      
      final startHour = prefs.getInt('sleep_mode_start_hour') ?? 23;
      final startMinute = prefs.getInt('sleep_mode_start_minute') ?? 0;
      final endHour = prefs.getInt('sleep_mode_end_hour') ?? 7;
      final endMinute = prefs.getInt('sleep_mode_end_minute') ?? 0;
      
      // Перевірка часу
      final now = DateTime.now();
      final currentMinutes = now.hour * 60 + now.minute;
      final startMinutes = startHour * 60 + startMinute;
      final endMinutes = endHour * 60 + endMinute;
      
      bool isInSleepTime;
      if (startMinutes > endMinutes) {
        isInSleepTime = currentMinutes >= startMinutes || currentMinutes < endMinutes;
      } else {
        isInSleepTime = currentMinutes >= startMinutes && currentMinutes < endMinutes;
      }
      
      if (!isInSleepTime) return false;
      
      // Перевірка типу загрози
      final allowRockets = prefs.getBool('sleep_mode_rockets') ?? true;
      final allowDrones = prefs.getBool('sleep_mode_drones') ?? false;
      final allowAllClear = prefs.getBool('sleep_mode_all_clear') ?? false;
      
      final lowerBody = body.toLowerCase();
      final isRocket = lowerBody.contains('ракет') || 
                       lowerBody.contains('балістичн') ||
                       lowerBody.contains('калібр') ||
                       lowerBody.contains('кинджал') ||
                       lowerBody.contains('каб') ||
                       lowerBody.contains('касет');
      final isDrone = lowerBody.contains('бпла') || 
                      lowerBody.contains('дрон') ||
                      lowerBody.contains('шахед');
      final isAllClear = lowerBody.contains('відбій');
      
      if (isRocket && allowRockets) return false;
      if (isDrone && allowDrones) return false;
      if (isAllClear && allowAllClear) return false;
      
      // Загальна тривога (без конкретного типу) - пропускаємо якщо ракети дозволені
      if (!isRocket && !isDrone && !isAllClear && allowRockets) {
        debugPrint('🌙 Sleep mode (static): allowing general alarm (rockets enabled)');
        return false;
      }
      
      debugPrint('🌙 Sleep mode (static): blocking notification');
      return true;
    } catch (e) {
      debugPrint('Sleep mode check error: $e');
      return false;
    }
  }
}

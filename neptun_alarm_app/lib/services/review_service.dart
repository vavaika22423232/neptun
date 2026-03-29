import 'package:flutter/foundation.dart';
import 'package:in_app_review/in_app_review.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ReviewService {
  static const String _installDateKey = 'install_date';
  static const String _reviewRequestedKey = 'review_requested';
  static const String _appOpenCountKey = 'app_open_count';
  
  // Показуємо запит після 3 днів використання І 5+ відкриттів
  static const int _daysBeforeReview = 3;
  static const int _opensBeforeReview = 5;
  
  final InAppReview _inAppReview = InAppReview.instance;
  
  /// Викликати при кожному запуску додатку
  Future<void> trackAppOpen() async {
    final prefs = await SharedPreferences.getInstance();
    
    // Зберігаємо дату першого запуску
    if (!prefs.containsKey(_installDateKey)) {
      prefs.setInt(_installDateKey, DateTime.now().millisecondsSinceEpoch);
    }
    
    // Рахуємо відкриття
    final openCount = (prefs.getInt(_appOpenCountKey) ?? 0) + 1;
    prefs.setInt(_appOpenCountKey, openCount);
    
    // Перевіряємо чи можна показати запит
    await _checkAndRequestReview(prefs, openCount);
  }
  
  Future<void> _checkAndRequestReview(SharedPreferences prefs, int openCount) async {
    // Якщо вже просили - не турбуємо
    if (prefs.getBool(_reviewRequestedKey) ?? false) {
      return;
    }
    
    // Перевіряємо кількість відкриттів
    if (openCount < _opensBeforeReview) {
      return;
    }
    
    // Перевіряємо дні з моменту встановлення
    final installDate = prefs.getInt(_installDateKey);
    if (installDate == null) return;
    
    final daysSinceInstall = DateTime.now()
        .difference(DateTime.fromMillisecondsSinceEpoch(installDate))
        .inDays;
    
    if (daysSinceInstall < _daysBeforeReview) {
      return;
    }
    
    // Всі умови виконані - показуємо запит
    await requestReview();
    
    // Позначаємо що вже просили
    prefs.setBool(_reviewRequestedKey, true);
  }
  
  /// Показати нативний діалог оцінки Google Play
  Future<bool> requestReview() async {
    try {
      if (await _inAppReview.isAvailable()) {
        await _inAppReview.requestReview();
        return true;
      }
    } catch (e) {
      debugPrint('Error requesting review: $e');
    }
    return false;
  }
  
  /// Відкрити сторінку в Google Play або App Store (якщо нативний не працює)
  Future<void> openStoreListing() async {
    await _inAppReview.openStoreListing(
      // iOS App Store ID - update this after app is published to App Store
      // This is the numeric ID from App Store Connect
      appStoreId: '6743895428', // NOTE: Update with real App Store ID after publishing
      // Android package name is detected automatically
    );
  }
  
  /// Скинути для тестування
  Future<void> resetForTesting() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_installDateKey);
    await prefs.remove(_reviewRequestedKey);
    await prefs.remove(_appOpenCountKey);
  }
}

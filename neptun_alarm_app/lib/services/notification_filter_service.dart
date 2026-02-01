import 'package:flutter/foundation.dart';
import '../models/notification_event.dart';
import '../models/user_region_selection.dart';
import 'region_database.dart';

/// Сервіс фільтрації сповіщень за регіонами
/// Використовує ТІЛЬКИ ID, ніяких string matching
class NotificationFilterService {
  static final NotificationFilterService _instance = NotificationFilterService._internal();
  factory NotificationFilterService() => _instance;
  NotificationFilterService._internal();

  final RegionDatabase _db = RegionDatabase();

  /// Перевіряє чи потрібно показувати сповіщення користувачу
  /// 
  /// Алгоритм:
  /// 1. Якщо користувач обрав населений пункт → exact match по settlementId
  /// 2. Якщо користувач обрав райони → exact match по raionId
  /// 3. Якщо користувач обрав області → exact match по oblastId
  /// 
  /// Якщо подія не має валідного oblastId → НЕ показувати
  bool shouldShowNotification(NotificationEvent event, UserRegionSelection user) {
    // Якщо немає вибору користувача - не показувати
    if (user.isEmpty) {
      debugPrint('🚫 Filter: user has no selection');
      return false;
    }

    // Якщо подія не має валідної геолокації - не показувати
    if (!event.hasValidLocation) {
      debugPrint('🚫 Filter: event has no valid location (oblastId=${event.oblastId})');
      return false;
    }

    // 1. Перевірка по населеному пункту (найточніша)
    if (user.settlementId != null) {
      final match = event.settlementId == user.settlementId;
      debugPrint('🔍 Filter: settlement match ${user.settlementId} == ${event.settlementId} → $match');
      return match;
    }

    // 2. Перевірка по районах
    if (user.raionIds.isNotEmpty) {
      // Якщо подія має raionId - перевіряємо exact match
      if (event.raionId != null && event.raionId!.isNotEmpty) {
        final match = user.raionIds.contains(event.raionId);
        debugPrint('🔍 Filter: raion exact match ${event.raionId} in ${user.raionIds} → $match');
        return match;
      }
      
      // Якщо подія не має raionId (тільки oblast) - НЕ показуємо
      // Користувач вибрав конкретні райони, йому не потрібні загальні повідомлення про область
      debugPrint('🚫 Filter: user selected raions but event has no raionId (oblast=${event.oblastId})');
      return false;
    }

    // 3. Перевірка по області
    if (user.oblastIds.isNotEmpty) {
      // Перевіряємо чи подія належить до однієї з обраних областей
      final match = user.oblastIds.contains(event.oblastId);
      debugPrint('🔍 Filter: oblast match ${event.oblastId} in ${user.oblastIds} → $match');
      return match;
    }

    debugPrint('🚫 Filter: no matching criteria');
    return false;
  }

  /// Перевіряє валідність події
  bool isValidEvent(NotificationEvent event) {
    if (event.oblastId == null) {
      return false;
    }
    
    // Перевіряємо чи oblast існує в базі
    if (_db.getOblastById(event.oblastId!) == null) {
      debugPrint('⚠️ Unknown oblastId: ${event.oblastId}');
      return false;
    }
    
    // Якщо є raionId - перевіряємо його
    if (event.raionId != null) {
      final raion = _db.getRaionById(event.raionId!);
      if (raion == null) {
        debugPrint('⚠️ Unknown raionId: ${event.raionId}');
        return false;
      }
      
      // Перевіряємо чи raion належить до вказаної області
      if (raion.parentId != event.oblastId) {
        debugPrint('⚠️ Raion ${event.raionId} does not belong to oblast ${event.oblastId}');
        return false;
      }
    }
    
    return true;
  }

  /// Резолвить oblast для події якщо є тільки raionId
  String? resolveOblastId(String raionId) {
    return _db.getOblastIdForRaion(raionId);
  }
}

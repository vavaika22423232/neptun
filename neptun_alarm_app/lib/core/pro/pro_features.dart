import '../di/service_locator.dart';
import '../../services/purchase_service.dart';

/// Centralized gate for all PRO-only features.
/// Single source of truth for what's free vs PRO.
enum ProFeature {
  alarmHistory,
  personalAnalytics,
  heatmap,
  trajectories,
  customAlarmSounds,
  advancedFilters,
  noAds,
  priorityNotifications,
  offlineMode,
  extendedRadar,
  chatBadge,
  widgetCustomization,
  chatMedia,
  preciseRaionPush,
  sleepMode,
  detailedPush,
  chatThemes,
  animatedAvatar,
}

class ProGate {
  ProGate._();

  static bool get isPro => sl<PurchaseService>().isPremium;

  static int get mapThreatHistoryMinutes => isPro ? 120 : 30;

  static bool isUnlocked(ProFeature feature) {
    if (isPro) return true;

    // Some features are always free
    switch (feature) {
      case ProFeature.noAds:
      case ProFeature.customAlarmSounds:
      case ProFeature.priorityNotifications:
      case ProFeature.alarmHistory:
      case ProFeature.personalAnalytics:
      case ProFeature.heatmap:
      case ProFeature.trajectories:
      case ProFeature.advancedFilters:
      case ProFeature.offlineMode:
      case ProFeature.extendedRadar:
      case ProFeature.chatBadge:
      case ProFeature.widgetCustomization:
      case ProFeature.chatMedia:
      case ProFeature.preciseRaionPush:
      case ProFeature.sleepMode:
      case ProFeature.detailedPush:
      case ProFeature.chatThemes:
      case ProFeature.animatedAvatar:
        return false;
    }
  }

  static const Map<ProFeature, String> featureNames = {
    ProFeature.alarmHistory: 'Історія тривог',
    ProFeature.personalAnalytics: 'Персональна аналітика',
    ProFeature.heatmap: 'Теплова карта',
    ProFeature.trajectories: 'Траєкторії загроз',
    ProFeature.customAlarmSounds: 'Кастомні звуки',
    ProFeature.advancedFilters: 'Розширені фільтри',
    ProFeature.noAds: 'Без реклами',
    ProFeature.priorityNotifications: 'Пріоритетні сповіщення',
    ProFeature.offlineMode: 'Офлайн режим',
    ProFeature.extendedRadar: 'Розширений радар',
    ProFeature.chatBadge: 'PRO бейдж в чаті',
    ProFeature.widgetCustomization: 'Кастомізація віджетів',
    ProFeature.chatMedia: 'Медіа в чаті',
    ProFeature.preciseRaionPush: 'Точні пуші по району',
    ProFeature.sleepMode: 'Режим сну',
    ProFeature.detailedPush: 'Детальні сповіщення',
    ProFeature.chatThemes: 'Теми чату',
    ProFeature.animatedAvatar: 'Анімований аватар',
  };

  static const Map<ProFeature, String> featureDescriptions = {
    ProFeature.alarmHistory: 'Перегляд та аналіз усіх попередніх тривог',
    ProFeature.personalAnalytics: 'Час під тривогою, статистика по регіону',
    ProFeature.heatmap: 'Теплова карта загроз за останній місяць',
    ProFeature.trajectories: 'Візуалізація траєкторій ракет та дронів',
    ProFeature.customAlarmSounds: 'Обирайте унікальний звук для кожного типу загрози',
    ProFeature.advancedFilters: 'Фільтрація за типом, регіоном та часом',
    ProFeature.noAds: 'Повна відсутність реклами',
    ProFeature.priorityNotifications: 'Виділений канал для миттєвих сповіщень',
    ProFeature.offlineMode: 'Кешування даних для роботи без інтернету',
    ProFeature.extendedRadar: 'Розширена зона моніторингу загроз',
    ProFeature.chatBadge: 'Золотий бейдж PRO-користувача в чаті',
    ProFeature.widgetCustomization: 'Налаштування зовнішнього вигляду віджетів',
    ProFeature.chatMedia: 'Надсилання фото та аудіо в чаті',
    ProFeature.preciseRaionPush: 'Сповіщення з прив’язкою до району',
    ProFeature.sleepMode: 'Тихі години без зайвих сповіщень',
    ProFeature.detailedPush: 'Розширений текст у push-сповіщеннях',
    ProFeature.chatThemes: 'Додаткові теми оформлення чату',
    ProFeature.animatedAvatar: 'Анімоване відображення аватара',
  };
}

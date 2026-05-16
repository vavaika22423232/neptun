import '../di/service_locator.dart';
import '../../services/purchase_service.dart';

/// Тарифний план користувача.
enum AppTier {
  free,
  pro, // Pro-підписка (місячна або legacy-навсегда)
}

enum ProFeature {
  alarmHistory,
  personalAnalytics,
  heatmap,
  sleepMode,          // тихий режим з винятками по типу загрози
  detailedPush,       // детальні push з типом + містом загрози
  preciseRaionPush,   // підписка на конкретний район замість цілої області
  extendedRadar,
  trajectories,
  customAlarmSounds,
  advancedFilters,
  noAds,
  priorityNotifications,
  offlineMode,
  chatBadge,
  widgetCustomization,
  chatThemes,
  animatedAvatar,
}

class ProGate {
  ProGate._();

  static AppTier get tier => sl<PurchaseService>().tier;
  static bool get isPro => tier == AppTier.pro;

  /// Alias для зворотної сумісності — скрізь де перевіряли isPremium.
  static bool get isPremium => isPro;

  /// Хвилини історії позицій загроз на карті / радарі (PRO: 3 год, FREE: 1 год).
  static int get mapThreatHistoryMinutes => isPro ? 180 : 60;

  static bool isUnlocked(ProFeature feature) => isPro;

  static const Map<ProFeature, String> featureNames = {
    ProFeature.noAds: 'Без реклами',
    ProFeature.customAlarmSounds: 'Кастомні звуки тривоги',
    ProFeature.widgetCustomization: 'Віджет на екрані',
    ProFeature.alarmHistory: 'Історія тривог',
    ProFeature.personalAnalytics: 'Персональна аналітика',
    ProFeature.heatmap: 'Теплова карта',
    ProFeature.sleepMode: 'Режим сну',
    ProFeature.detailedPush: 'Детальні сповіщення',
    ProFeature.preciseRaionPush: 'Push тільки для вашого району',
    ProFeature.extendedRadar: 'Більша історія на карті',
    ProFeature.trajectories: 'Траєкторії загроз',
    ProFeature.advancedFilters: 'Розширені фільтри',
    ProFeature.priorityNotifications: 'Пріоритетні сповіщення',
    ProFeature.offlineMode: 'Офлайн режим',
    ProFeature.chatBadge: 'PRO бейдж в чаті',
    ProFeature.chatThemes: 'Теми оформлення чату',
    ProFeature.animatedAvatar: 'Анімована аватарка',
  };

  static const Map<ProFeature, String> featureDescriptions = {
    ProFeature.noAds: 'Повна відсутність реклами в додатку',
    ProFeature.customAlarmSounds: 'Звуки «Різкий» та «Сирена» для push-сповіщень',
    ProFeature.widgetCustomization: 'Додайте віджет Neptun на головний екран',
    ProFeature.alarmHistory: 'Перегляд та аналіз усіх попередніх тривог',
    ProFeature.personalAnalytics: 'Час під тривогою, статистика по регіону',
    ProFeature.heatmap: 'Теплова карта загроз за останній місяць',
    ProFeature.sleepMode: 'Вночі — тиша, але ракети та балістика все одно розбудять',
    ProFeature.detailedPush: 'Push із типом загрози та містом: «🚀 Балістика — Харків»',
    ProFeature.preciseRaionPush:
        'Обирайте конкретний район: push тільки якщо загроза у вашому місті',
    ProFeature.extendedRadar:
        'До 3 год історії позицій на карті та радарі (безкоштовно — 1 год)',
    ProFeature.trajectories: 'Візуалізація траєкторій ракет та дронів',
    ProFeature.advancedFilters: 'Фільтрація за типом, регіоном та часом',
    ProFeature.priorityNotifications: 'Виділений канал для миттєвих сповіщень',
    ProFeature.offlineMode: 'Кешування даних для роботи без інтернету',
    ProFeature.chatBadge: 'Золотий бейдж PRO-користувача в чаті',
    ProFeature.chatThemes: 'Ексклюзивні кольори та фони для чату',
    ProFeature.animatedAvatar: 'Динамічне підсвічування вашого аватара',
  };
}

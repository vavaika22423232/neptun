/** Mirrors Flutter `ProFeature` — no native / purchase imports (testable in Node). */
export enum ProFeature {
  AlarmHistory = 'alarmHistory',
  PersonalAnalytics = 'personalAnalytics',
  Heatmap = 'heatmap',
  Trajectories = 'trajectories',
  CustomAlarmSounds = 'customAlarmSounds',
  AdvancedFilters = 'advancedFilters',
  NoAds = 'noAds',
  PriorityNotifications = 'priorityNotifications',
  OfflineMode = 'offlineMode',
  ExtendedRadar = 'extendedRadar',
  ChatBadge = 'chatBadge',
  WidgetCustomization = 'widgetCustomization',
  ChatMedia = 'chatMedia',
  PreciseRaionPush = 'preciseRaionPush',
  SleepMode = 'sleepMode',
  DetailedPush = 'detailedPush',
  ChatThemes = 'chatThemes',
  AnimatedAvatar = 'animatedAvatar',
}

export const PRO_ONLY_FEATURES: ReadonlySet<ProFeature> = new Set([
  ProFeature.AlarmHistory,
  ProFeature.PersonalAnalytics,
  ProFeature.Heatmap,
  ProFeature.Trajectories,
  ProFeature.CustomAlarmSounds,
  ProFeature.AdvancedFilters,
  ProFeature.NoAds,
  ProFeature.PriorityNotifications,
  ProFeature.OfflineMode,
  ProFeature.ExtendedRadar,
  ProFeature.ChatBadge,
  ProFeature.WidgetCustomization,
  ProFeature.ChatMedia,
  ProFeature.PreciseRaionPush,
  ProFeature.SleepMode,
  ProFeature.DetailedPush,
  ProFeature.ChatThemes,
  ProFeature.AnimatedAvatar,
]);

export const proFeatureNames: Record<ProFeature, string> = {
  [ProFeature.AlarmHistory]: 'Історія тривог',
  [ProFeature.PersonalAnalytics]: 'Персональна аналітика',
  [ProFeature.Heatmap]: 'Теплова карта',
  [ProFeature.Trajectories]: 'Траєкторії загроз',
  [ProFeature.CustomAlarmSounds]: 'Кастомні звуки',
  [ProFeature.AdvancedFilters]: 'Розширені фільтри',
  [ProFeature.NoAds]: 'Без реклами',
  [ProFeature.PriorityNotifications]: 'Пріоритетні сповіщення',
  [ProFeature.OfflineMode]: 'Офлайн режим',
  [ProFeature.ExtendedRadar]: 'Розширений радар',
  [ProFeature.ChatBadge]: 'PRO бейдж в чаті',
  [ProFeature.WidgetCustomization]: 'Кастомізація віджетів',
  [ProFeature.ChatMedia]: 'Медіа в чаті',
  [ProFeature.PreciseRaionPush]: 'Точні пуші по району',
  [ProFeature.SleepMode]: 'Режим сну',
  [ProFeature.DetailedPush]: 'Детальні сповіщення',
  [ProFeature.ChatThemes]: 'Теми чату',
  [ProFeature.AnimatedAvatar]: 'Анімований аватар',
};

export function isProFeatureUnlockedSync(feature: ProFeature, isPremium: boolean): boolean {
  if (isPremium) return true;
  return !PRO_ONLY_FEATURES.has(feature);
}

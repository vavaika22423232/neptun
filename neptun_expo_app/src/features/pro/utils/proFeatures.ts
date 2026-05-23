import type { PlanId } from '../../monetization/types';

export type ProEntrySource =
  | 'map'
  | 'radar'
  | 'profile'
  | 'ads'
  | 'settings'
  | 'history'
  | 'notifications'
  | 'feature_gate';

export type LockedFeatureId =
  | 'advanced_filters'
  | 'history_extended'
  | 'ai_summary'
  | 'priority_push'
  | 'remove_ads'
  | 'my_regions'
  | 'quiet_mode'
  | 'smart_notifications';

export type LockedFeatureSpec = {
  id: LockedFeatureId;
  label: string;
  subtitle: string;
  minPlan: PlanId;
};

export const PRO_HERO_BENEFITS = [
  { icon: 'eye-off-outline' as const, text: 'Без реклами' },
  { icon: 'notifications-outline' as const, text: 'Пріоритетні сповіщення' },
  { icon: 'location-outline' as const, text: 'Обрані області' },
  { icon: 'time-outline' as const, text: 'Розширена історія' },
  { icon: 'options-outline' as const, text: 'Розумні фільтри' },
  { icon: 'moon-outline' as const, text: 'Тихий режим' },
] as const;

export const LOCKED_FEATURES: Record<LockedFeatureId, LockedFeatureSpec> = {
  advanced_filters: {
    id: 'advanced_filters',
    label: 'Розширені фільтри',
    subtitle: 'Точніший відбір загроз на радарі',
    minPlan: 'pro',
  },
  history_extended: {
    id: 'history_extended',
    label: 'Історія 24 год',
    subtitle: 'Повний журнал подій за добу',
    minPlan: 'pro_plus',
  },
  ai_summary: {
    id: 'ai_summary',
    label: 'AI-зведення',
    subtitle: 'Короткий огляд ситуації',
    minPlan: 'max',
  },
  priority_push: {
    id: 'priority_push',
    label: 'Пріоритетні push',
    subtitle: 'Швидші критичні сповіщення',
    minPlan: 'pro',
  },
  remove_ads: {
    id: 'remove_ads',
    label: 'Прибрати рекламу',
    subtitle: 'Чистий інтерфейс без банерів',
    minPlan: 'pro',
  },
  my_regions: {
    id: 'my_regions',
    label: 'Обрані області',
    subtitle: 'Сповіщення лише для ваших регіонів',
    minPlan: 'pro',
  },
  quiet_mode: {
    id: 'quiet_mode',
    label: 'Тихий режим',
    subtitle: 'Менше шуму вночі',
    minPlan: 'pro',
  },
  smart_notifications: {
    id: 'smart_notifications',
    label: 'Розумні сповіщення',
    subtitle: 'Правила та пріоритети',
    minPlan: 'pro',
  },
};

export const RADAR_PRO_CHIPS: LockedFeatureId[] = [
  'advanced_filters',
  'history_extended',
  'ai_summary',
  'priority_push',
];

export function analyticsSource(source: ProEntrySource, feature?: LockedFeatureId): string {
  if (feature) return `${source}_${feature}`;
  if (source === 'map') return 'map_pro_pill';
  if (source === 'radar') return 'radar_locked_filter';
  if (source === 'profile') return 'profile_pro_card';
  if (source === 'ads') return 'ads_remove_cta';
  return `pro_${source}`;
}

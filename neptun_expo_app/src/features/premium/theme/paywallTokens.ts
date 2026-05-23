import { getActiveTheme } from '../../../theme/activeTheme';
import { radii, spacing, typography } from '../../../theme/tokens';
import type { AppTheme } from '../../../theme/types';
import { useAppTheme } from '../../../theme/useAppTheme';

export function getPaywallTokens(theme: AppTheme) {
  const c = theme.colors;
  const isLight = theme.scheme === 'light';
  return {
    bg: c.background,
    bgAmbient: isLight
      ? (['rgba(37, 99, 235, 0.03)', 'rgba(246, 231, 200, 0.25)', c.background] as const)
      : (['rgba(74, 141, 255, 0.04)', 'rgba(200, 164, 93, 0.05)', c.background] as const),
    heroGlow: isLight
      ? (['rgba(246, 231, 200, 0.35)', 'rgba(232, 240, 255, 0.5)'] as const)
      : (['rgba(200, 164, 93, 0.12)', 'rgba(74, 141, 255, 0.06)'] as const),
    heroRing: isLight ? 'rgba(169, 121, 43, 0.2)' : 'rgba(200, 164, 93, 0.25)',
    accent: c.pro,
    accentSoft: c.pro,
    accentMuted: c.proSoft,
    accentOnCta: isLight ? '#FFFFFF' : c.textPrimary,
    text: c.textPrimary,
    textSoft: c.textSecondary,
    textMuted: c.textMuted,
    textFaint: c.textFaint,
    surface: c.surfaceHighlight,
    surfaceStrong: c.card,
    border: c.border,
    borderStrong: c.borderStrong,
    divider: c.divider,
    success: c.success,
    radiusHero: 28,
    radiusCard: radii.xl,
    radiusPill: radii.pill,
    inset: spacing.screenH,
    sectionGap: spacing.xxl,
    ...typography,
    shadows: theme.shadows,
  };
}

export type PaywallTokens = ReturnType<typeof getPaywallTokens>;

/** Reads active theme on each property access — prefer `usePaywallTheme()` in components. */
export const paywall = new Proxy({} as PaywallTokens, {
  get(_t, prop: string | symbol) {
    return getPaywallTokens(getActiveTheme())[prop as keyof PaywallTokens];
  },
});

export function usePaywallTheme() {
  return getPaywallTokens(useAppTheme().theme);
}

export const PREMIUM_BENEFITS = [
  { icon: 'location-outline' as const, title: 'Точні сповіщення', subtitle: 'По районах, не лише областях' },
  { icon: 'moon-outline' as const, title: 'Режим сну', subtitle: 'Тихі години без зайвого шуму' },
  { icon: 'time-outline' as const, title: 'Історія тривог', subtitle: 'Журнал подій у ваших регіонах' },
  { icon: 'stats-chart-outline' as const, title: 'Аналітика', subtitle: 'Час під тривогою та статистика' },
  { icon: 'flame-outline' as const, title: 'Теплова карта', subtitle: 'Активність загроз по регіонах' },
  { icon: 'color-palette-outline' as const, title: 'Теми чату', subtitle: 'Оформлення та анімована аватарка' },
  { icon: 'eye-off-outline' as const, title: 'Без реклами', subtitle: 'Чистий інтерфейс без відволікань' },
  { icon: 'radio-outline' as const, title: 'Розширений радар', subtitle: 'Детальніша картина загроз' },
] as const;

export const PAYWALL_FAQ = [
  { q: 'Це підписка чи разова оплата?', a: 'PRO — одноразова покупка назавжди. Без щомісячних списань і прихованих платежів.' },
  { q: 'Як відновити покупку?', a: 'Натисніть «Відновити» зверху екрана — використовується той самий Apple ID або Google акаунт.' },
  { q: 'Чи можна скасувати?', a: 'Покупка не скасовується автоматично — ви платите один раз і зберігаєте доступ.' },
] as const;

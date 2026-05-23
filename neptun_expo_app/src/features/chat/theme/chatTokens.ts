import { chatThemeById } from '../../../config/chatThemes';
import { getActiveTheme } from '../../../theme/activeTheme';
import { radii, spacing, typography } from '../../../theme/tokens';
import type { AppTheme, ChatThemeTokens, LegacyPalette } from '../../../theme/types';

export function getChatTokens(): ChatThemeTokens & {
  avatarSize: number;
  avatarGap: number;
  bubbleMaxWidth: '82%';
  messagePadH: number;
  messagePadV: number;
  composerMargin: number;
  listPadH: number;
  listPadV: number;
} {
  const c = getActiveTheme().chat;
  return {
    ...c,
    avatarSize: 30,
    avatarGap: 36,
    bubbleMaxWidth: '82%' as const,
    messagePadH: 12,
    messagePadV: 8,
    composerMargin: spacing.screenH,
    listPadH: spacing.screenH,
    listPadV: spacing.sm,
  };
}

type ChatTokens = ReturnType<typeof getChatTokens>;

/** Reads active theme on each property access. */
export const chat = new Proxy({} as ChatTokens, {
  get(_t, prop: keyof ChatTokens) {
    return getChatTokens()[prop as keyof ChatTokens];
  },
});

export type ChatBubblePalette = {
  mineGradient: readonly [string, string];
  mineText: string;
  mineMeta: string;
  mineReplyBorder: string;
  mineReplyBg: string;
  mineReplyText: string;
  peerBg: string;
  peerBorder: string;
  peerText: string;
  peerMeta: string;
  peerReplyBorder: string;
  peerReplyBg: string;
  peerName: string;
};

export function chatBubblePalette(
  themeId: string,
  isPremium: boolean,
  appTheme: AppTheme = getActiveTheme(),
): ChatBubblePalette {
  const c = appTheme.colors;
  const chatDecor = appTheme.chat;
  const isLight = appTheme.scheme === 'light';

  /** Premium messenger look — white outgoing, charcoal incoming. */
  if (isLight) {
    return {
      mineGradient: ['#FFFFFF', '#FFFFFF'],
      mineText: '#000000',
      mineMeta: 'rgba(0,0,0,0.42)',
      mineReplyBorder: 'rgba(0,0,0,0.18)',
      mineReplyBg: 'rgba(0,0,0,0.05)',
      mineReplyText: 'rgba(0,0,0,0.62)',
      peerBg: chatDecor.bubbleOther,
      peerBorder: 'transparent',
      peerText: c.textPrimary,
      peerMeta: c.textMuted,
      peerReplyBorder: c.primary,
      peerReplyBg: 'rgba(0,0,0,0.04)',
      peerName: c.textPrimary,
    };
  }

  return {
    mineGradient: ['#FFFFFF', '#FFFFFF'],
    mineText: '#000000',
    mineMeta: 'rgba(0,0,0,0.42)',
    mineReplyBorder: 'rgba(0,0,0,0.15)',
    mineReplyBg: 'rgba(0,0,0,0.06)',
    mineReplyText: 'rgba(0,0,0,0.62)',
    peerBg: chatDecor.bubbleOther,
    peerBorder: 'transparent',
    peerText: '#FFFFFF',
    peerMeta: 'rgba(235,235,245,0.55)',
    peerReplyBorder: 'rgba(255,255,255,0.35)',
    peerReplyBg: 'rgba(255,255,255,0.06)',
    peerName: 'rgba(235,235,245,0.88)',
  };
}

function shadeColor(hex: string, percent: number): string {
  const n = hex.replace('#', '');
  if (n.length !== 6) return hex;
  const num = parseInt(n, 16);
  const r = Math.min(255, Math.max(0, ((num >> 16) & 0xff) + percent));
  const g = Math.min(255, Math.max(0, ((num >> 8) & 0xff) + percent));
  const b = Math.min(255, Math.max(0, (num & 0xff) + percent));
  return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`;
}

export { radii, spacing, typography };

export function getChatPalette() {
  return getActiveTheme().palette;
}

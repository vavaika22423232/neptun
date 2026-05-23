import { spacing } from '../../theme/tokens';

/** Profile — grouped iOS cards (reference layout). */
export const profileTokens = {
  insetH: spacing.screenH,
  heroGap: 12,
  groupGap: 16,
  rowMinHeight: 52,
  rowPadV: 12,
  rowPadH: 16,
  iconSize: 22,
  iconColWidth: 28,
  cardRadius: 20,
  proCardRadius: 20,
  avatarSize: 52,
  headerBtn: 40,
  statusCardPad: 16,
  proCardPad: 14,
  tabBarClearance: 84,
  type: {
    headerTitle: { fontSize: 17, lineHeight: 22 },
    headerSubtitle: { fontSize: 13, lineHeight: 18 },
    sectionLabel: { fontSize: 13, lineHeight: 18 },
    rowTitle: { fontSize: 16, lineHeight: 21 },
    rowSubtitle: { fontSize: 13, lineHeight: 18 },
    accountTitle: { fontSize: 17, lineHeight: 22 },
    accountSubtitle: { fontSize: 14, lineHeight: 19 },
    proTitle: { fontSize: 16, lineHeight: 21 },
    proDesc: { fontSize: 12, lineHeight: 16 },
    proCtaPill: { fontSize: 13, lineHeight: 16 },
  },
} as const;

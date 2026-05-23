import { Ionicons } from '@expo/vector-icons';
import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import { Text } from '../../../components/Text';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { fonts } from '../../../theme/fonts';
import { useThemedStyles } from '../../../theme/useAppTheme';
import { profileTokens } from '../profileTokens';

type Props = {
  title: string;
  subtitle: string;
  onPress?: () => void;
};

function AccountStatusCardInner({ title, subtitle, onPress }: Props) {
  const styles = useCardStyles();

  const body = (
    <View style={styles.row}>
      <View style={styles.avatar}>
        <Ionicons name="person" size={24} color="#FFFFFF" />
      </View>
      <View style={styles.copy}>
        <Text style={styles.name} numberOfLines={1}>
          {title}
        </Text>
        <Text style={styles.subtitle} numberOfLines={2}>
          {subtitle}
        </Text>
      </View>
      {onPress ? (
        <Ionicons name="chevron-forward" size={18} color={styles.chevronColor.color} />
      ) : null}
    </View>
  );

  if (!onPress) {
    return <View style={styles.card}>{body}</View>;
  }

  return (
    <NeptunPressable haptic onPress={onPress} style={styles.card}>
      {body}
    </NeptunPressable>
  );
}

function useCardStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      card: {
        marginHorizontal: profileTokens.insetH,
        padding: profileTokens.statusCardPad,
        borderRadius: profileTokens.cardRadius,
        backgroundColor: t.colors.card,
        shadowColor: '#000',
        shadowOpacity: t.scheme === 'light' ? 0.04 : 0,
        shadowRadius: 8,
        shadowOffset: { width: 0, height: 2 },
        elevation: t.scheme === 'light' ? 1 : 0,
      },
      row: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 14,
      },
      avatar: {
        width: profileTokens.avatarSize,
        height: profileTokens.avatarSize,
        borderRadius: profileTokens.avatarSize / 2,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#5856D6',
      },
      copy: {
        flex: 1,
        minWidth: 0,
        gap: 3,
      },
      name: {
        fontFamily: fonts.semiBold,
        fontSize: profileTokens.type.accountTitle.fontSize,
        color: t.colors.textPrimary,
      },
      subtitle: {
        fontFamily: fonts.regular,
        fontSize: profileTokens.type.accountSubtitle.fontSize,
        color: t.colors.textMuted,
      },
      chevronColor: { color: t.colors.textFaint },
    }),
  );
}

export const AccountStatusCard = memo(AccountStatusCardInner);

/** @deprecated use AccountStatusCard */
export const AccountSummaryCard = AccountStatusCard;

export function buildAccountStatusCopy(opts: {
  nickname?: string | null;
  isPremium?: boolean;
  notificationsActive: boolean;
  regionCount: number;
}): { title: string; subtitle: string } {
  const trimmed = opts.nickname?.trim();
  const title = trimmed || 'NEPTUN Alerts';
  const status = opts.notificationsActive ? 'Сповіщення активні' : 'Сповіщення вимкнено';
  const n = opts.regionCount;
  const regionPart =
    n === 0 ? '0 регіонів' : n === 1 ? '1 регіон' : n < 5 ? `${n} регіони` : `${n} регіонів`;
  const plan = opts.isPremium ? 'PRO' : 'Free';
  return {
    title,
    subtitle: `${status} · ${regionPart} · ${plan}`,
  };
}

export function buildAccountSummaryCopy(opts: {
  nickname?: string | null;
  notificationsOn: boolean;
  pushReady: boolean;
  regionCount: number;
}): { title: string; subtitle: string } {
  return buildAccountStatusCopy({
    nickname: opts.nickname,
    notificationsActive: opts.notificationsOn && opts.pushReady,
    regionCount: opts.regionCount,
  });
}

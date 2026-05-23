import { StyleSheet, View } from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { AppText } from '../../../components/ui/AppText';
import { fonts } from '../../../theme/fonts';
import { useThemedStyles } from '../../../theme/useAppTheme';

type Props = {
  displayName: string;
  isPremium: boolean;
};

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}

export function ProfileHero({ displayName, isPremium }: Props) {
  const styles = useThemedStyles((t) => {
    const prof = t.profile;
    const S = prof.avatarSize;
    return StyleSheet.create({
      root: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 16,
        paddingVertical: 4,
      },
      avatarOuter: {
        width: S + 8,
        height: S + 8,
        alignItems: 'center',
        justifyContent: 'center',
      },
      avatarRing: {
        ...StyleSheet.absoluteFillObject,
        borderRadius: (S + 8) / 2,
        borderWidth: 1.5,
        borderColor: prof.heroRing,
        opacity: 0.85,
      },
      avatar: {
        width: S,
        height: S,
        borderRadius: prof.radiusAvatar,
        alignItems: 'center',
        justifyContent: 'center',
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: prof.cardBorder,
        backgroundColor: t.colors.primaryMuted,
      },
      avatarText: {
        fontFamily: fonts.bold,
        fontSize: 24,
        color: prof.premiumAccent,
        letterSpacing: -0.5,
      },
      copy: { flex: 1, minWidth: 0, gap: 4 },
      name: {
        fontFamily: fonts.bold,
        fontSize: 24,
        color: prof.textPrimary,
        letterSpacing: -0.5,
        lineHeight: 28,
      },
      hint: {
        fontFamily: fonts.medium,
        fontSize: 13,
        color: prof.textSecondary,
      },
      tierPremium: {
        paddingHorizontal: 14,
        paddingVertical: 7,
        borderRadius: 999,
        backgroundColor: t.colors.proSoft,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.colors.pro + '44',
      },
      tierPremiumText: {
        fontFamily: fonts.bold,
        fontSize: 11,
        color: t.colors.pro,
        letterSpacing: 0.4,
      },
      tierFree: {
        paddingHorizontal: 14,
        paddingVertical: 7,
        borderRadius: 999,
        backgroundColor: prof.freeBg,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: prof.cardBorder,
      },
      tierFreeText: {
        fontFamily: fonts.semiBold,
        fontSize: 11,
        color: prof.freeText,
        letterSpacing: 0.3,
      },
    });
  });

  return (
    <Animated.View entering={FadeInDown.duration(340).springify().damping(22)} style={styles.root}>
      <View style={styles.avatarOuter}>
        <View style={styles.avatarRing} />
        <View style={styles.avatar}>
          <AppText variant="screenTitle" style={styles.avatarText}>
            {initials(displayName)}
          </AppText>
        </View>
      </View>

      <View style={styles.copy}>
        <AppText variant="screenTitle" style={styles.name} numberOfLines={1}>
          {displayName}
        </AppText>
        <AppText variant="meta" muted>
          Neptun Alerts
        </AppText>
      </View>

      {isPremium ? (
        <View style={styles.tierPremium}>
          <AppText variant="badge" style={styles.tierPremiumText}>
            PRO
          </AppText>
        </View>
      ) : (
        <View style={styles.tierFree}>
          <AppText variant="badge" style={styles.tierFreeText}>
            Free
          </AppText>
        </View>
      )}
    </Animated.View>
  );
}

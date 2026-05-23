import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { StyleSheet, View } from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { Text } from '../../../components/Text';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { fonts } from '../../../theme/fonts';
import { useAppTheme, useThemedStyles } from '../../../theme/useAppTheme';
import { ProfileGlassCard } from './ProfileGlassCard';

type Props = {
  onPress: () => void;
  isPremium: boolean;
};

export function ProfilePremiumCard({ onPress, isPremium }: Props) {
  const { theme } = useAppTheme();
  const p = theme.profile;

  const styles = useThemedStyles((t) => {
    const prof = t.profile;
    return StyleSheet.create({
      pressWrap: { borderRadius: prof.radiusCard, ...t.shadows.sm },
      upgradeShell: {
        borderRadius: prof.radiusCard,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.colors.premiumMuted,
        padding: 18,
        overflow: 'hidden',
      },
      upgradeRow: { flexDirection: 'row', alignItems: 'center', gap: 14 },
      iconWrap: {
        width: 50,
        height: 50,
        borderRadius: 16,
        alignItems: 'center',
        justifyContent: 'center',
      },
      upgradeCopy: { flex: 1 },
      upgradeTitle: {
        fontFamily: fonts.bold,
        fontSize: 17,
        color: prof.textPrimary,
        letterSpacing: -0.2,
      },
      upgradeSub: {
        marginTop: 4,
        fontFamily: fonts.regular,
        fontSize: 13,
        color: prof.textSecondary,
        lineHeight: 18,
      },
      activeRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
      activeIcon: {
        width: 44,
        height: 44,
        borderRadius: 14,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: prof.premiumGlow,
      },
      activeCopy: { flex: 1 },
      activeTitle: {
        fontFamily: fonts.semiBold,
        fontSize: 16,
        color: prof.textPrimary,
      },
      activeSub: {
        marginTop: 2,
        fontSize: 12,
        color: prof.textSecondary,
      },
    });
  });

  const premiumIconColor = theme.scheme === 'light' ? '#92400E' : '#FFF9EB';

  if (isPremium) {
    return (
      <Animated.View entering={FadeInDown.delay(50).duration(320)}>
        <ProfileGlassCard padding={18}>
          <View style={styles.activeRow}>
            <View style={styles.activeIcon}>
              <Ionicons name="star" size={20} color={p.premiumAccent} />
            </View>
            <View style={styles.activeCopy}>
              <Text style={styles.activeTitle}>Premium активний</Text>
              <Text style={styles.activeSub}>Дякуємо, що підтримуєте NEPTUN</Text>
            </View>
            <Ionicons name="checkmark-circle" size={22} color={p.statusCalm} />
          </View>
        </ProfileGlassCard>
      </Animated.View>
    );
  }

  return (
    <Animated.View entering={FadeInDown.delay(50).duration(320)}>
      <NeptunPressable onPress={onPress} style={styles.pressWrap}>
        <LinearGradient
          colors={[...p.premiumGradientSoft]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={styles.upgradeShell}
        >
          <View style={styles.upgradeRow}>
            <LinearGradient colors={[...p.premiumGradient]} style={styles.iconWrap}>
              <Ionicons name="sparkles" size={22} color={premiumIconColor} />
            </LinearGradient>
            <View style={styles.upgradeCopy}>
              <Text style={styles.upgradeTitle}>Оновити до Premium</Text>
              <Text style={styles.upgradeSub}>Аналітика, звуки та пріоритетні сповіщення</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color={p.textTertiary} />
          </View>
        </LinearGradient>
      </NeptunPressable>
    </Animated.View>
  );
}

import { Ionicons } from '@expo/vector-icons';
import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { Text } from '../../../components/Text';
import { AppButton } from '../../../components/ui/AppButton';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { ProfileGlassCard } from '../../profile/components/ProfileGlassCard';
import { useAppTheme, useThemedStyles } from '../../../theme/useAppTheme';
import { fonts } from '../../../theme/fonts';
import { useProAccess } from '../hooks/useProAccess';
import { PRO_HERO_BENEFITS } from '../utils/proFeatures';

type Props = {
  onPress?: () => void;
};

function ProCardInner({ onPress }: Props) {
  const { isPaid, plan, entitlements, openPaywall } = useProAccess();
  const { theme } = useAppTheme();
  const styles = useProCardStyles();
  const handlePress = onPress ?? (() => openPaywall({ source: 'profile' }));

  if (isPaid) {
    const planLabel = plan === 'max' ? 'MAX' : plan === 'pro_plus' ? 'PRO+' : 'PRO';
    return (
      <Animated.View entering={FadeInDown.delay(40).duration(300)}>
        <ProfileGlassCard padding={18}>
          <View style={styles.activeRow}>
            <View style={[styles.activeIcon, { backgroundColor: theme.colors.proSoft }]}>
              <Ionicons name="star" size={20} color={theme.colors.pro} />
            </View>
            <View style={styles.activeCopy}>
              <Text style={styles.activeTitle}>PRO активний · {planLabel}</Text>
              <Text style={styles.activeSub}>
                {entitlements.expiresAt
                  ? `Діє до ${new Date(entitlements.expiresAt).toLocaleDateString('uk-UA')}`
                  : 'Дякуємо за підтримку NEPTUN'}
              </Text>
            </View>
            <NeptunPressable haptic onPress={handlePress}>
              <Text style={styles.manage}>Керувати</Text>
            </NeptunPressable>
          </View>
        </ProfileGlassCard>
      </Animated.View>
    );
  }

  return (
    <Animated.View entering={FadeInDown.delay(40).duration(300)}>
      <ProfileGlassCard padding={18} style={styles.card}>
        <Text style={styles.brand}>NEPTUN PRO</Text>
        <Text style={styles.subtitle}>
          Без реклами, пріоритетні сповіщення та більше контролю
        </Text>
        <View style={styles.benefits}>
          {PRO_HERO_BENEFITS.map((b) => (
            <View key={b.text} style={styles.benefitRow}>
              <Ionicons name={b.icon} size={16} color={theme.colors.primary} />
              <Text style={styles.benefitText}>{b.text}</Text>
            </View>
          ))}
        </View>
        <AppButton onPress={handlePress}>Отримати PRO</AppButton>
      </ProfileGlassCard>
    </Animated.View>
  );
}

function useProCardStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      card: {
        borderColor: t.colors.proSoft,
      },
      brand: {
        fontFamily: fonts.bold,
        fontSize: 20,
        letterSpacing: 0.5,
        color: t.colors.textPrimary,
      },
      subtitle: {
        marginTop: 6,
        fontFamily: fonts.medium,
        fontSize: 14,
        lineHeight: 20,
        color: t.colors.textSecondary,
      },
      benefits: {
        marginTop: 14,
        marginBottom: 16,
        gap: 8,
      },
      benefitRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 10,
      },
      benefitText: {
        fontFamily: fonts.medium,
        fontSize: 14,
        color: t.colors.textPrimary,
      },
      activeRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
      },
      activeIcon: {
        width: 44,
        height: 44,
        borderRadius: 14,
        alignItems: 'center',
        justifyContent: 'center',
      },
      activeCopy: { flex: 1 },
      activeTitle: {
        fontFamily: fonts.semiBold,
        fontSize: 16,
        color: t.colors.textPrimary,
      },
      activeSub: {
        marginTop: 2,
        fontSize: 12,
        color: t.colors.textSecondary,
      },
      manage: {
        fontFamily: fonts.semiBold,
        fontSize: 13,
        color: t.colors.primary,
      },
    }),
  );
}

export const ProCard = memo(ProCardInner);

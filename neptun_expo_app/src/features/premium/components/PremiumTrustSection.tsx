import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { Platform, StyleSheet, View } from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { Text } from '../../../components/Text';
import { paywall } from '../theme/paywallTokens';
import { fonts } from '../../../theme/fonts';

export function PremiumTrustSection() {
  return (
    <Animated.View entering={FadeInDown.delay(280).duration(300)} style={styles.wrap}>
      <View style={styles.social}>
        <View style={styles.stars}>
          {[1, 2, 3, 4, 5].map((i) => (
            <Ionicons key={i} name="star" size={14} color={paywall.accentSoft} style={{ opacity: 0.85 }} />
          ))}
        </View>
        <Text style={styles.socialText}>
          PRO допомагає тисячам користувачів тримати під контролем сповіщення та карту загроз.
        </Text>
      </View>

      <View style={styles.payment}>
        <View style={styles.payRow}>
          <Ionicons
            name={Platform.OS === 'ios' ? 'logo-apple' : 'logo-google'}
            size={20}
            color={paywall.textSoft}
          />
          <Text style={styles.payText}>
            Безпечна оплата через {Platform.OS === 'ios' ? 'App Store' : 'Google Play'}
          </Text>
        </View>
        <View style={styles.badges}>
          <TrustChip icon="lock-closed-outline" label="Шифрування" />
          <TrustChip icon="refresh-outline" label="Відновлення" />
          <TrustChip icon="card-outline" label="Без підписки" />
        </View>
      </View>
    </Animated.View>
  );
}

function TrustChip({
  icon,
  label,
}: {
  icon: ComponentProps<typeof Ionicons>['name'];
  label: string;
}) {
  return (
    <View style={styles.chip}>
      <Ionicons name={icon} size={14} color={paywall.textMuted} />
      <Text style={styles.chipText}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: 14 },
  social: {
    padding: 16,
    borderRadius: paywall.radiusCard,
    backgroundColor: paywall.surface,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: paywall.border,
    gap: 10,
  },
  stars: {
    flexDirection: 'row',
    gap: 4,
  },
  socialText: {
    fontFamily: fonts.regular,
    fontSize: 13,
    lineHeight: 20,
    color: paywall.textMuted,
  },
  payment: {
    padding: 16,
    borderRadius: paywall.radiusCard,
    backgroundColor: paywall.surface,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: paywall.border,
    gap: 12,
  },
  payRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  payText: {
    flex: 1,
    fontFamily: fonts.medium,
    fontSize: 13,
    color: paywall.textSoft,
  },
  badges: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 7,
    borderRadius: paywall.radiusPill,
    backgroundColor: 'rgba(255,255,255,0.04)',
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: paywall.border,
  },
  chipText: {
    fontFamily: fonts.medium,
    fontSize: 11,
    color: paywall.textMuted,
  },
});

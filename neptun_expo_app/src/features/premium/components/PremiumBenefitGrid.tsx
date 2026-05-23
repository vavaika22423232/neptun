import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { StyleSheet, View } from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { Text } from '../../../components/Text';
import { PREMIUM_BENEFITS, paywall } from '../theme/paywallTokens';
import { fonts } from '../../../theme/fonts';

export function PremiumBenefitGrid() {
  return (
    <View style={styles.wrap}>
      <Text style={styles.heading}>Що ви отримуєте</Text>
      <View style={styles.grid}>
        {PREMIUM_BENEFITS.map((b, i) => (
          <Animated.View
            key={b.title}
            entering={FadeInDown.delay(120 + i * 35).duration(280)}
            style={styles.cell}
          >
            <View style={styles.iconPlate}>
              <Ionicons name={b.icon as ComponentProps<typeof Ionicons>['name']} size={18} color={paywall.accentSoft} />
            </View>
            <Text style={styles.title}>{b.title}</Text>
            <Text style={styles.sub}>{b.subtitle}</Text>
          </Animated.View>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: 14 },
  heading: {
    fontFamily: fonts.semiBold,
    fontSize: 12,
    letterSpacing: 0.9,
    textTransform: 'uppercase',
    color: paywall.textFaint,
    paddingLeft: 4,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  cell: {
    width: '48.5%',
    flexGrow: 1,
    minWidth: 148,
    padding: 14,
    borderRadius: 18,
    backgroundColor: paywall.surface,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: paywall.border,
    gap: 6,
  },
  iconPlate: {
    width: 34,
    height: 34,
    borderRadius: 11,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: paywall.accentMuted,
  },
  title: {
    fontFamily: fonts.semiBold,
    fontSize: 14,
    color: paywall.text,
    letterSpacing: -0.1,
  },
  sub: {
    fontFamily: fonts.regular,
    fontSize: 12,
    lineHeight: 16,
    color: paywall.textMuted,
  },
});

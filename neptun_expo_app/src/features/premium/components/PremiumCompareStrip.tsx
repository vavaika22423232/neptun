import { StyleSheet, View } from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { Text } from '../../../components/Text';
import { paywall } from '../theme/paywallTokens';
import { fonts } from '../../../theme/fonts';

const ROWS = [
  { label: 'Сповіщення по районах', free: 'Обмежено', pro: 'Повністю' },
  { label: 'Реклама', free: 'Є', pro: 'Немає' },
  { label: 'Аналітика та історія', free: '—', pro: '✓' },
  { label: 'Режим сну', free: '—', pro: '✓' },
] as const;

export function PremiumCompareStrip() {
  return (
    <Animated.View entering={FadeInDown.delay(200).duration(300)} style={styles.card}>
      <View style={styles.header}>
        <Text style={styles.colLabel}>Free</Text>
        <Text style={[styles.colLabel, styles.colPro]}>PRO</Text>
      </View>
      {ROWS.map((row, i) => (
        <View key={row.label} style={[styles.row, i < ROWS.length - 1 && styles.rowBorder]}>
          <Text style={styles.rowLabel}>{row.label}</Text>
          <Text style={styles.freeVal}>{row.free}</Text>
          <Text style={styles.proVal}>{row.pro}</Text>
        </View>
      ))}
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: paywall.radiusCard,
    backgroundColor: paywall.surfaceStrong,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: paywall.border,
    overflow: 'hidden',
  },
  header: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: 'rgba(255,255,255,0.03)',
  },
  colLabel: {
    flex: 1,
    textAlign: 'right',
    fontFamily: fonts.bold,
    fontSize: 11,
    letterSpacing: 0.6,
    textTransform: 'uppercase',
    color: paywall.textFaint,
  },
  colPro: { color: paywall.accentSoft },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 13,
    gap: 8,
  },
  rowBorder: {
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: paywall.divider,
  },
  rowLabel: {
    flex: 1.4,
    fontFamily: fonts.medium,
    fontSize: 13,
    color: paywall.textSoft,
  },
  freeVal: {
    flex: 0.8,
    textAlign: 'right',
    fontFamily: fonts.medium,
    fontSize: 13,
    color: paywall.textFaint,
  },
  proVal: {
    flex: 0.8,
    textAlign: 'right',
    fontFamily: fonts.semiBold,
    fontSize: 13,
    color: paywall.accentSoft,
  },
});

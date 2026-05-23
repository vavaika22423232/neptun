import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, View } from 'react-native';
import { Text } from '../../../components/Text';
import { NeptunSurface } from '../../../design/components/NeptunSurface';
import { palette, radii, spacing } from '../../../design/tokens';
import { fonts } from '../../../theme/fonts';

type Props = {
  onPress: () => void;
};

export function PremiumBanner({ onPress }: Props) {
  return (
    <NeptunSurface variant="raised" padding={spacing.lg} onPress={onPress}>
      <View style={styles.row}>
        <View style={styles.iconWrap}>
          <Ionicons name="ribbon" size={24} color={palette.premium} />
        </View>
        <View style={styles.body}>
          <Text style={styles.title}>NEPTUN Premium</Text>
          <Text style={styles.sub}>Розширені можливості</Text>
          <Bullet text="Детальні карти загроз" />
          <Bullet text="Пріоритетні сповіщення" />
          <Bullet text="Статистика та аналітика" />
        </View>
        <Ionicons name="chevron-forward" size={20} color={palette.premium} />
      </View>
    </NeptunSurface>
  );
}

function Bullet({ text }: { text: string }) {
  return (
    <View style={styles.bulletRow}>
      <View style={styles.dot} />
      <Text style={styles.bulletText}>{text}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'flex-start', gap: spacing.md },
  iconWrap: {
    width: 48,
    height: 48,
    borderRadius: radii.lg,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: palette.premiumMuted,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: palette.borderStrong,
  },
  body: { flex: 1, gap: 4 },
  title: { fontFamily: fonts.bold, fontSize: 18, color: palette.text },
  sub: { fontFamily: fonts.medium, fontSize: 13, color: palette.textMuted, marginBottom: spacing.sm },
  bulletRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, marginTop: 4 },
  dot: { width: 6, height: 6, borderRadius: 3, backgroundColor: palette.premium },
  bulletText: { flex: 1, fontFamily: fonts.medium, fontSize: 13, color: palette.textSoft },
});

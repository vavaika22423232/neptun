import { StyleSheet, View } from 'react-native';
import { Text } from '../Text';
import { profile } from '../../design/tokens';
import { fonts } from '../../theme/fonts';

export function ProBadge({ label = 'PRO' }: { label?: string }) {
  return (
    <View style={styles.wrap}>
      <Text style={styles.text}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    paddingHorizontal: 9,
    paddingVertical: 4,
    borderRadius: 999,
    backgroundColor: profile.premiumGlow,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: 'rgba(201, 169, 98, 0.35)',
  },
  text: {
    fontFamily: fonts.bold,
    fontSize: 10,
    letterSpacing: 0.6,
    color: profile.premiumAccent,
  },
});

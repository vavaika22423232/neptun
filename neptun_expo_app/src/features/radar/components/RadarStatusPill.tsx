import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, View } from 'react-native';
import { Text } from '../../../components/Text';
import { palette, radii, typography } from '../../../design/tokens';
import { fonts } from '../../../theme/fonts';

type Props = {
  label: string;
};

export function RadarStatusPill({ label }: Props) {
  return (
    <View style={styles.root}>
      <Ionicons name="pulse-outline" size={14} color={palette.danger} />
      <Text style={styles.text}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: radii.pill,
    backgroundColor: palette.dangerMuted,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: palette.danger + '44',
  },
  text: {
    fontFamily: fonts.bold,
    ...typography.callout,
    color: palette.danger,
  },
});

import { StyleSheet, View } from 'react-native';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { Text } from '../../../components/Text';
import { radarTheme } from '../constants/radarTheme';
import { fonts } from '../../../theme/fonts';

type Props = {
  count: number;
  onPress: () => void;
};

export function RadarNewUpdatesPill({ count, onPress }: Props) {
  if (count <= 0) return null;
  return (
    <View style={styles.wrap} pointerEvents="box-none">
      <NeptunPressable haptic scaleTo={1} onPress={onPress} style={styles.pill}>
        <Text style={styles.label}>
          {count === 1 ? 'Нове оновлення' : `${count} нові оновлення`}
        </Text>
      </NeptunPressable>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    position: 'absolute',
    top: 8,
    alignSelf: 'center',
    zIndex: 20,
  },
  pill: {
    backgroundColor: radarTheme.accent,
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: radarTheme.chipRadius,
    shadowColor: radarTheme.accent,
    shadowOpacity: 0.35,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
  },
  label: { fontFamily: fonts.bold, fontSize: 13, color: radarTheme.bg },
});

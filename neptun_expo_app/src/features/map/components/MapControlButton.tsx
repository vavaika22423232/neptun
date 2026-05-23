import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { memo } from 'react';
import { StyleSheet } from 'react-native';
import { NeptunPressable } from '../../../design/components/NeptunPressable';

const BTN = 40;

type Props = {
  icon: ComponentProps<typeof Ionicons>['name'];
  label: string;
  color: string;
  onPress: () => void;
};

function MapControlButtonInner({ icon, label, color, onPress }: Props) {
  return (
    <NeptunPressable
      haptic
      scaleTo={0.96}
      accessibilityLabel={label}
      onPress={onPress}
      style={styles.btn}
    >
      <Ionicons name={icon} size={20} color={color} />
    </NeptunPressable>
  );
}

const styles = StyleSheet.create({
  btn: {
    width: BTN,
    height: BTN,
    borderRadius: BTN / 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
});

export const MapControlButton = memo(MapControlButtonInner);

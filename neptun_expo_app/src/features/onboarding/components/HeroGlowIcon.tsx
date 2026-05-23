import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { StyleSheet, View } from 'react-native';
import { palette, radii } from '../../../design/tokens';

type Props = {
  name: ComponentProps<typeof Ionicons>['name'];
  tint?: string;
  size?: number;
};

export function HeroGlowIcon({ name, tint = palette.accent, size = 108 }: Props) {
  const outer = size + 28;
  return (
    <View
      style={[
        styles.glow,
        {
          width: outer,
          height: outer,
          borderRadius: outer / 2,
          backgroundColor: tint + '18',
        },
      ]}
    >
      <View style={[styles.core, { width: size, height: size, borderRadius: radii.xl }]}>
        <Ionicons name={name} size={size * 0.4} color={tint} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  glow: { alignItems: 'center', justifyContent: 'center' },
  core: {
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: palette.surfaceGlassStrong,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: palette.borderStrong,
  },
});

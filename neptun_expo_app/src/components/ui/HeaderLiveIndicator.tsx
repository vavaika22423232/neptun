import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import { useAppTheme } from '../../theme/useAppTheme';

type Props = {
  active?: boolean;
  size?: 'sm' | 'md';
};

/** Static live dot — no pulse or glow. */
export const HeaderLiveIndicator = memo(function HeaderLiveIndicator({
  active = true,
  size = 'md',
}: Props) {
  const { theme } = useAppTheme();
  const core = size === 'sm' ? 6 : 8;

  return (
    <View
      style={[
        styles.core,
        {
          width: core,
          height: core,
          borderRadius: core / 2,
          backgroundColor: active ? theme.colors.live : theme.colors.textFaint,
        },
      ]}
    />
  );
});

const styles = StyleSheet.create({
  core: {},
});

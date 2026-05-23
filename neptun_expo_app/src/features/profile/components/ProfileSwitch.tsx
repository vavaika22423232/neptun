import { Platform, Switch, type SwitchProps } from 'react-native';
import { neptunPalette } from '../../../theme/neptunPalette';
import { useAppTheme } from '../../../theme/useAppTheme';

export function ProfileSwitch(props: SwitchProps) {
  const { theme } = useAppTheme();
  const c = theme.colors;
  const trackOff = theme.scheme === 'light' ? 'rgba(120,120,128,0.16)' : 'rgba(120,120,128,0.32)';

  return (
    <Switch
      trackColor={{ false: trackOff, true: neptunPalette.iosGreen }}
      thumbColor={Platform.OS === 'android' ? '#FFFFFF' : undefined}
      ios_backgroundColor={trackOff}
      {...props}
    />
  );
}

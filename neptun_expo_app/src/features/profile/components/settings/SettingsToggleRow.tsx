import { memo } from 'react';
import { SettingsRow, type SettingsRowProps } from './SettingsRow';
import { ProfileSwitch } from '../ProfileSwitch';

type Props = Omit<SettingsRowProps, 'trailing' | 'onPress' | 'detail'> & {
  enabled: boolean;
  onEnabledChange: (value: boolean) => void;
  onPress?: () => void;
};

function SettingsToggleRowInner({ enabled, onEnabledChange, onPress, ...rest }: Props) {
  return (
    <SettingsRow
      {...rest}
      onPress={onPress}
      trailing={<ProfileSwitch value={enabled} onValueChange={onEnabledChange} />}
    />
  );
}

export const SettingsToggleRow = memo(SettingsToggleRowInner);

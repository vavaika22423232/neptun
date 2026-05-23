import { memo } from 'react';
import { Alert } from 'react-native';
import type { ThemeMode } from '../../../theme/types';
import { useAppTheme } from '../../../theme/useAppTheme';
import { SettingsRow } from './settings/SettingsRow';

const MODE_LABELS: Record<ThemeMode, string> = {
  system: 'Системна',
  light: 'Світла',
  dark: 'Темна',
};

function ProfileThemeRowInner() {
  const { mode, setMode } = useAppTheme();

  const pickTheme = () => {
    Alert.alert('Тема застосунку', undefined, [
      { text: 'Системна', onPress: () => void apply('system') },
      { text: 'Світла', onPress: () => void apply('light') },
      { text: 'Темна', onPress: () => void apply('dark') },
      { text: 'Скасувати', style: 'cancel' },
    ]);
  };

  const apply = (next: ThemeMode) => {
    if (next === mode) return;
    setMode(next);
  };

  return (
    <SettingsRow
      icon="color-palette-outline"
      label="Тема застосунку"
      detail={MODE_LABELS[mode]}
      showDivider
      onPress={pickTheme}
    />
  );
}

export const ProfileThemeRow = memo(ProfileThemeRowInner);

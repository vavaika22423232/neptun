import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import { useAppTheme, useThemedStyles } from '../../../../theme/useAppTheme';
import { profileTokens } from '../../profileTokens';
import {
  getSettingsIconToneColors,
  resolveSettingsIconTone,
  type SettingsIconTone,
} from './settingsIconTones';

type Props = {
  name: ComponentProps<typeof Ionicons>['name'];
  tone?: SettingsIconTone;
  /** `plain` — line icon like reference; `tinted` — colored circle */
  variant?: 'plain' | 'tinted';
};

function SettingsIconInner({ name, tone, variant = 'plain' }: Props) {
  const { theme } = useAppTheme();
  const styles = useIconStyles();

  if (variant === 'plain') {
    return (
      <View style={styles.plainWrap}>
        <Ionicons name={name} size={profileTokens.iconSize} color={styles.plainIcon.color} />
      </View>
    );
  }

  const resolved = resolveSettingsIconTone(name, tone);
  const palette = getSettingsIconToneColors(theme.scheme, resolved);

  return (
    <View style={[styles.tintedWrap, { backgroundColor: palette.background }]}>
      <Ionicons name={name} size={18} color={palette.foreground} />
    </View>
  );
}

function useIconStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      plainWrap: {
        width: profileTokens.iconColWidth,
        alignItems: 'center',
        justifyContent: 'center',
      },
      plainIcon: { color: t.colors.textPrimary },
      tintedWrap: {
        width: 36,
        height: 36,
        borderRadius: 18,
        alignItems: 'center',
        justifyContent: 'center',
      },
    }),
  );
}

export const SettingsIcon = memo(SettingsIconInner);

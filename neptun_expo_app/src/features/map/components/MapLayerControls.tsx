import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { Text } from '../../../components/Text';
import { radii } from '../../../design/tokens';
import { fonts } from '../../../theme/fonts';
import { useAppTheme, useThemedStyles } from '../../../theme/useAppTheme';

type Props = {
  showOblastAlarms: boolean;
  showTrajectories: boolean;
  onToggleOblast: () => void;
  onToggleTrajectories: () => void;
};

/** Native map layer toggles (Flutter map legend / layer controls subset). */
export function MapLayerControls({
  showOblastAlarms,
  showTrajectories,
  onToggleOblast,
  onToggleTrajectories,
}: Props) {
  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      row: {
        position: 'absolute',
        left: 12,
        bottom: 12,
        flexDirection: 'row',
        gap: 8,
        zIndex: 12,
      },
      chip: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        paddingHorizontal: 12,
        paddingVertical: 8,
        borderRadius: radii.pill,
        backgroundColor: t.colors.surfaceGlassStrong,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.colors.border,
        ...t.shadows.sm,
      },
      chipOn: {
        borderColor: t.colors.primary,
        backgroundColor: t.colors.primaryMuted,
      },
      chipText: {
        fontFamily: fonts.semiBold,
        fontSize: 12,
        color: t.colors.textMuted,
      },
      chipTextOn: {
        color: t.colors.primary,
      },
    }),
  );

  return (
    <View style={styles.row}>
      <LayerChip
        icon="map"
        label="Області"
        active={showOblastAlarms}
        onPress={onToggleOblast}
        styles={styles}
      />
      <LayerChip
        icon="git-branch"
        label="Траєкторії"
        active={showTrajectories}
        onPress={onToggleTrajectories}
        styles={styles}
      />
    </View>
  );
}

function LayerChip({
  icon,
  label,
  active,
  onPress,
  styles,
}: {
  icon: ComponentProps<typeof Ionicons>['name'];
  label: string;
  active: boolean;
  onPress: () => void;
  styles: {
    chip: object;
    chipOn: object;
    chipText: object;
    chipTextOn: object;
  };
}) {
  const { theme } = useAppTheme();
  const iconColor = active ? theme.colors.primary : theme.colors.textMuted;

  return (
    <Pressable onPress={onPress} style={[styles.chip, active && styles.chipOn]}>
      <Ionicons name={icon} size={14} color={iconColor} />
      <Text style={[styles.chipText, active && styles.chipTextOn]}>{label}</Text>
    </Pressable>
  );
}

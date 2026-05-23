import { Ionicons } from '@expo/vector-icons';
import { memo, useMemo } from 'react';
import { StyleSheet } from 'react-native';
import { Text } from '../../../components/Text';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { fonts } from '../../../theme/fonts';
import { useAppTheme } from '../../../theme/useAppTheme';
import { mapOverlayTokens } from './mapOverlayTokens';

export type MapAlertSummaryChipProps = {
  activeAlertCount: number;
  label: string;
  onPress?: () => void;
};

function MapAlertSummaryChipInner({ label, onPress }: MapAlertSummaryChipProps) {
  const { theme } = useAppTheme();
  const tokens = useMemo(() => mapOverlayTokens(theme.scheme), [theme.scheme]);

  return (
    <NeptunPressable
      haptic
      scaleTo={0.99}
      accessibilityLabel={label}
      onPress={() => onPress?.()}
      style={[
        styles.chip,
        { backgroundColor: tokens.bg, borderColor: tokens.border },
      ]}
    >
      <Text style={[styles.text, { color: tokens.textPrimary }]} numberOfLines={1}>
        {label}
      </Text>
      <Ionicons name="chevron-forward" size={16} color={tokens.textSecondary} />
    </NeptunPressable>
  );
}

const styles = StyleSheet.create({
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    height: 46,
    paddingHorizontal: 16,
    borderRadius: 14,
    borderWidth: StyleSheet.hairlineWidth,
    gap: 8,
  },
  text: {
    flex: 1,
    fontFamily: fonts.semiBold,
    fontSize: 13,
  },
});

export const MapAlertSummaryChip = memo(MapAlertSummaryChipInner);

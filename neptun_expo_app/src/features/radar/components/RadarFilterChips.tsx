import { ScrollView, StyleSheet } from 'react-native';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { Text } from '../../../components/Text';
import { fonts } from '../../../theme/fonts';
import { useThemedStyles } from '../../../theme/useAppTheme';
import { RADAR_FILTER_LABELS, RADAR_FILTER_ORDER, type RadarQuickFilter } from '../domain/radarQuickFilter';

type Props = {
  selected: RadarQuickFilter;
  onChange: (f: RadarQuickFilter) => void;
  showMyRegions?: boolean;
};

export function RadarFilterChips({ selected, onChange, showMyRegions = true }: Props) {
  const styles = useChipStyles();
  const filters = showMyRegions
    ? RADAR_FILTER_ORDER
    : RADAR_FILTER_ORDER.filter((f) => f !== 'myRegions');

  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.row}
      keyboardShouldPersistTaps="handled"
      nestedScrollEnabled
      directionalLockEnabled
    >
      {filters.map((f) => {
        const active = selected === f;
        return (
          <NeptunPressable
            key={f}
            haptic={false}
            onPress={() => onChange(f)}
            style={[styles.chip, active && styles.chipActive]}
          >
            <Text style={[styles.label, active && styles.labelActive]}>{RADAR_FILTER_LABELS[f]}</Text>
          </NeptunPressable>
        );
      })}
    </ScrollView>
  );
}

function useChipStyles() {
  return useThemedStyles((t) => {
    const isDark = t.scheme === 'dark';
    return StyleSheet.create({
      row: { gap: 8, paddingVertical: 2 },
      chip: {
        paddingHorizontal: 14,
        paddingVertical: 8,
        borderRadius: t.radar.chipRadius,
        backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)',
      },
      chipActive: {
        backgroundColor: isDark ? '#FFFFFF' : '#000000',
      },
      label: {
        fontFamily: fonts.medium,
        fontSize: 13,
        color: t.colors.textMuted,
      },
      labelActive: {
        fontFamily: fonts.semiBold,
        color: isDark ? '#000000' : '#FFFFFF',
      },
    });
  });
}

import { Pressable, ScrollView, StyleSheet } from 'react-native';
import { Text } from '../../../components/Text';
import { fonts } from '../../../theme/fonts';
import { useThemedStyles } from '../../../theme/useAppTheme';
import {
  RADAR_FILTER_LABELS,
  type RadarQuickFilter,
} from '../domain/radarQuickFilter';

const FILTERS: RadarQuickFilter[] = [
  'all',
  'shahedLayer',
  'missiles',
  'aviation',
  'airRaid',
  'blasts',
];

type Props = {
  value: RadarQuickFilter;
  onChange: (f: RadarQuickFilter) => void;
};

export function RadarQuickFilters({ value, onChange }: Props) {
  const styles = useStyles();
  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.row}
    >
      {FILTERS.map((f) => {
        const active = f === value;
        return (
          <Pressable
            key={f}
            onPress={() => onChange(f)}
            style={[styles.chip, active && styles.chipOn]}
          >
            <Text style={[styles.chipText, active && styles.chipTextOn]}>
              {RADAR_FILTER_LABELS[f]}
            </Text>
          </Pressable>
        );
      })}
    </ScrollView>
  );
}

function useStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      row: { paddingHorizontal: 14, gap: 8, paddingBottom: 8 },
      chip: {
        paddingHorizontal: 12,
        paddingVertical: 7,
        borderRadius: 999,
        backgroundColor: t.colors.surface,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.colors.border,
      },
      chipOn: {
        borderColor: t.colors.primary,
        backgroundColor: t.colors.primarySoft,
      },
      chipText: { fontFamily: fonts.medium, fontSize: 12, color: t.colors.textMuted },
      chipTextOn: { color: t.colors.textPrimary },
    }),
  );
}

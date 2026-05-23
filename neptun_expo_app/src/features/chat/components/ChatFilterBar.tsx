import { StyleSheet, View } from 'react-native';
import { Text } from '../../../components/Text';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { fonts } from '../../../theme/fonts';
import { useThemedStyles } from '../../../theme/useAppTheme';

export type ChatMessageFilter = 'all' | 'media' | 'voice';

const FILTERS: { id: ChatMessageFilter; label: string }[] = [
  { id: 'all', label: 'Усі' },
  { id: 'media', label: 'Медіа' },
  { id: 'voice', label: 'Голос' },
];

type Props = {
  active: ChatMessageFilter;
  counts: Record<ChatMessageFilter, number>;
  onChange: (filter: ChatMessageFilter) => void;
};

/** Compact dark pills — unobtrusive on messenger canvas. */
export function ChatFilterBar({ active, counts, onChange }: Props) {
  const styles = useFilterStyles();

  return (
    <View style={styles.wrap}>
      <View style={styles.row}>
        {FILTERS.map((f) => {
          const selected = active === f.id;
          const count = counts[f.id];
          const label = count > 0 ? `${f.label} · ${count > 99 ? '99+' : count}` : f.label;
          return (
            <NeptunPressable
              key={f.id}
              haptic={false}
              onPress={() => onChange(f.id)}
              style={[styles.chip, selected && styles.chipActive]}
            >
              <Text style={[styles.label, selected && styles.labelActive]} numberOfLines={1}>
                {label}
              </Text>
            </NeptunPressable>
          );
        })}
      </View>
    </View>
  );
}

function useFilterStyles() {
  return useThemedStyles((t) => {
    const isDark = t.scheme === 'dark';
    return StyleSheet.create({
      wrap: {
        paddingHorizontal: 14,
        paddingBottom: 4,
      },
      row: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
      },
      chip: {
        paddingHorizontal: 12,
        paddingVertical: 6,
        borderRadius: 14,
        backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)',
      },
      chipActive: {
        backgroundColor: isDark ? 'rgba(255,255,255,0.14)' : t.colors.surface,
      },
      label: {
        fontFamily: fonts.medium,
        fontSize: 12,
        color: t.colors.textMuted,
      },
      labelActive: {
        fontFamily: fonts.semiBold,
        color: t.colors.textPrimary,
      },
    });
  });
}

import { Ionicons } from '@expo/vector-icons';
import { ScrollView, StyleSheet, TextInput, View } from 'react-native';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { Text } from '../../../components/Text';
import { fonts } from '../../../theme/fonts';
import { useThemedStyles } from '../../../theme/useAppTheme';

type Props = {
  expanded: boolean;
  query: string;
  recentSearches: string[];
  onToggle: () => void;
  onChange: (q: string) => void;
  onSubmit: () => void;
};

export function RadarSearchBar({
  expanded,
  query,
  recentSearches,
  onToggle,
  onChange,
  onSubmit,
}: Props) {
  const styles = useSearchStyles();

  if (!expanded) {
    return (
      <NeptunPressable haptic onPress={onToggle}>
        <View style={styles.collapsed}>
          <Ionicons name="search" size={17} color={styles.mutedColor.color} />
          <Text style={styles.collapsedLabel}>Пошук подій</Text>
        </View>
      </NeptunPressable>
    );
  }

  return (
    <View style={styles.expanded}>
      <View style={styles.inputWrap}>
        <Ionicons name="search" size={17} color={styles.mutedColor.color} />
        <TextInput
          value={query}
          onChangeText={onChange}
          onSubmitEditing={onSubmit}
          placeholder="Місто, область або подія"
          placeholderTextColor={styles.faintColor.color}
          style={styles.input}
          returnKeyType="search"
          autoFocus
        />
        <NeptunPressable haptic={false} onPress={onToggle}>
          <Ionicons name="close-circle" size={18} color={styles.mutedColor.color} />
        </NeptunPressable>
      </View>
      {recentSearches.length > 0 ? (
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.recentRow}
          keyboardShouldPersistTaps="handled"
        >
          {recentSearches.map((s) => (
            <NeptunPressable key={s} haptic onPress={() => onChange(s)} style={styles.recentChip}>
              <Text style={styles.recentText}>{s}</Text>
            </NeptunPressable>
          ))}
        </ScrollView>
      ) : null}
    </View>
  );
}

function useSearchStyles() {
  return useThemedStyles((t) => {
    const isDark = t.scheme === 'dark';
    const fieldBg = isDark ? 'rgba(255,255,255,0.10)' : '#FFFFFF';
    return StyleSheet.create({
      collapsed: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        minHeight: 44,
        paddingHorizontal: 14,
        borderRadius: 14,
        backgroundColor: fieldBg,
        shadowColor: '#000000',
        shadowOpacity: isDark ? 0 : 0.04,
        shadowRadius: 8,
        shadowOffset: { width: 0, height: 2 },
        elevation: isDark ? 0 : 1,
      },
      collapsedLabel: {
        fontFamily: fonts.regular,
        fontSize: 15,
        color: t.colors.textMuted,
      },
      expanded: { gap: 8 },
      inputWrap: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        minHeight: 44,
        paddingHorizontal: 14,
        borderRadius: 14,
        backgroundColor: fieldBg,
      },
      input: {
        flex: 1,
        fontFamily: fonts.regular,
        fontSize: 16,
        color: t.colors.textPrimary,
        paddingVertical: 8,
      },
      recentRow: { gap: 8 },
      recentChip: {
        paddingHorizontal: 12,
        paddingVertical: 6,
        borderRadius: 12,
        backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)',
      },
      recentText: {
        fontFamily: fonts.medium,
        fontSize: 13,
        color: t.colors.textSecondary,
      },
      mutedColor: { color: t.colors.textMuted },
      faintColor: { color: t.colors.textFaint },
    });
  });
}

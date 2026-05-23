import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { Text } from '../../../components/Text';
import { useAppTheme } from '../../../theme/useAppTheme';
import type { ThemeMode } from '../../../theme/types';
import { fonts } from '../../../theme/fonts';

type Option = {
  mode: ThemeMode;
  icon: ComponentProps<typeof Ionicons>['name'];
  label: string;
  description: string;
};

const OPTIONS: Option[] = [
  { mode: 'system', icon: 'phone-portrait-outline', label: 'Системна', description: 'Як у налаштуваннях телефону' },
  { mode: 'light', icon: 'sunny-outline', label: 'Світла', description: 'Чистий денний інтерфейс' },
  { mode: 'dark', icon: 'moon-outline', label: 'Темна', description: 'Комфортно вночі' },
];

export function ThemeSelector() {
  const { theme, mode, setMode } = useAppTheme();
  const c = theme.colors;

  return (
    <View style={styles.wrap}>
      <Text style={[styles.title, { color: c.textPrimary }]}>Тема застосунку</Text>
      {OPTIONS.map((opt) => {
        const selected = mode === opt.mode;
        return (
          <Pressable
            key={opt.mode}
            onPress={() => setMode(opt.mode)}
            style={[
              styles.row,
              {
                backgroundColor: selected ? c.primaryMuted : c.card,
                borderColor: selected ? c.primary : c.border,
              },
            ]}
          >
            <View style={[styles.iconBox, { backgroundColor: c.surfaceHighlight }]}>
              <Ionicons name={opt.icon} size={20} color={selected ? c.primary : c.textMuted} />
            </View>
            <View style={styles.copy}>
              <Text style={[styles.label, { color: c.textPrimary }]}>{opt.label}</Text>
              <Text style={[styles.desc, { color: c.textMuted }]}>{opt.description}</Text>
            </View>
            {selected ? (
              <Ionicons name="checkmark-circle" size={22} color={c.primary} />
            ) : (
              <View style={[styles.radio, { borderColor: c.borderStrong }]} />
            )}
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: 10 },
  title: { fontFamily: fonts.bold, fontSize: 15, marginBottom: 4 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 14,
    borderRadius: 16,
    borderWidth: StyleSheet.hairlineWidth,
  },
  iconBox: {
    width: 40,
    height: 40,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  copy: { flex: 1, gap: 2 },
  label: { fontFamily: fonts.semiBold, fontSize: 15 },
  desc: { fontFamily: fonts.medium, fontSize: 12 },
  radio: {
    width: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 2,
  },
});

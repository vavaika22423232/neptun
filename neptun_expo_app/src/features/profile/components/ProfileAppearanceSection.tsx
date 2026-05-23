import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import { AppText } from '../../../components/ui/AppText';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import type { ThemeMode } from '../../../theme/types';
import { useAppTheme } from '../../../theme/useAppTheme';
import { ProfileGlassCard } from './ProfileGlassCard';

const OPTIONS: { mode: ThemeMode; label: string; icon: ComponentProps<typeof Ionicons>['name'] }[] = [
  { mode: 'system', label: 'Системна', icon: 'phone-portrait-outline' },
  { mode: 'light', label: 'Світла', icon: 'sunny-outline' },
  { mode: 'dark', label: 'Темна', icon: 'moon-outline' },
];

function ProfileAppearanceSectionInner() {
  const { theme, mode, setMode } = useAppTheme();

  return (
    <ProfileGlassCard padding={16}>
      <AppText variant="sectionTitle">Тема застосунку</AppText>
      <AppText variant="meta" muted style={styles.sub}>
        Світла, темна або як у системі
      </AppText>
      <View style={styles.row}>
        {OPTIONS.map((opt) => {
          const active = mode === opt.mode;
          return (
            <NeptunPressable
              key={opt.mode}
              haptic
              scaleTo={0.97}
              onPress={() => setMode(opt.mode)}
              style={[
                styles.chip,
                {
                  backgroundColor: active ? theme.colors.primaryMuted : theme.colors.surfaceHighlight,
                  borderColor: active ? theme.colors.primary : theme.colors.border,
                },
              ]}
            >
              <Ionicons
                name={opt.icon}
                size={18}
                color={active ? theme.colors.primary : theme.colors.textMuted}
              />
              <AppText variant="meta" accent={active}>
                {opt.label}
              </AppText>
            </NeptunPressable>
          );
        })}
      </View>
    </ProfileGlassCard>
  );
}

const styles = StyleSheet.create({
  sub: { marginTop: 4, marginBottom: 14 },
  row: { flexDirection: 'row', gap: 8 },
  chip: {
    flex: 1,
    alignItems: 'center',
    gap: 6,
    paddingVertical: 12,
    borderRadius: 16,
    borderWidth: StyleSheet.hairlineWidth,
  },
});

export const ProfileAppearanceSection = memo(ProfileAppearanceSectionInner);

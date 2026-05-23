import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import { AppText } from '../../../components/ui/AppText';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import type { ThemeMode } from '../../../theme/types';
import { useAppTheme, useThemedStyles } from '../../../theme/useAppTheme';
import { ProfileGlassCard } from './ProfileGlassCard';

type Option = {
  mode: ThemeMode;
  label: string;
  description: string;
  icon: ComponentProps<typeof Ionicons>['name'];
};

const OPTIONS: Option[] = [
  {
    mode: 'system',
    label: 'Системна',
    description: 'Як у налаштуваннях телефону',
    icon: 'phone-portrait-outline',
  },
  {
    mode: 'light',
    label: 'Світла',
    description: 'Чистий денний інтерфейс',
    icon: 'sunny-outline',
  },
  {
    mode: 'dark',
    label: 'Темна',
    description: 'Комфортно вночі',
    icon: 'moon-outline',
  },
];

function ProfileThemeSelectorInner() {
  const { theme, mode, setMode } = useAppTheme();
  const styles = useThemeSelectorStyles();

  return (
    <ProfileGlassCard padding={0}>
      <View style={styles.header}>
        <AppText variant="sectionTitle">Тема застосунку</AppText>
      </View>
      {OPTIONS.map((opt, index) => {
        const active = mode === opt.mode;
        return (
          <NeptunPressable
            key={opt.mode}
            haptic
            onPress={() => setMode(opt.mode)}
            style={[styles.row, index < OPTIONS.length - 1 && styles.rowBorder]}
          >
            <View
              style={[
                styles.iconWrap,
                { backgroundColor: active ? theme.colors.primaryMuted : theme.colors.surfaceHighlight },
              ]}
            >
              <Ionicons
                name={opt.icon}
                size={20}
                color={active ? theme.colors.primary : theme.colors.textMuted}
              />
            </View>
            <View style={styles.copy}>
              <AppText variant="cardTitle">{opt.label}</AppText>
              <AppText variant="meta" muted>
                {opt.description}
              </AppText>
            </View>
            <View
              style={[
                styles.radio,
                {
                  borderColor: active ? theme.colors.primary : theme.colors.borderStrong,
                  backgroundColor: active ? theme.colors.primary : 'transparent',
                },
              ]}
            >
              {active ? <View style={styles.radioDot} /> : null}
            </View>
          </NeptunPressable>
        );
      })}
    </ProfileGlassCard>
  );
}

function useThemeSelectorStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      header: {
        paddingHorizontal: t.spacing.lg,
        paddingTop: t.spacing.lg,
        paddingBottom: t.spacing.sm,
      },
      row: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
        paddingHorizontal: t.spacing.lg,
        paddingVertical: 14,
        minHeight: 64,
      },
      rowBorder: {
        borderBottomWidth: StyleSheet.hairlineWidth,
        borderBottomColor: t.colors.divider,
      },
      iconWrap: {
        width: 40,
        height: 40,
        borderRadius: 12,
        alignItems: 'center',
        justifyContent: 'center',
      },
      copy: { flex: 1, gap: 2 },
      radio: {
        width: 22,
        height: 22,
        borderRadius: 11,
        borderWidth: 2,
        alignItems: 'center',
        justifyContent: 'center',
      },
      radioDot: {
        width: 8,
        height: 8,
        borderRadius: 4,
        backgroundColor: t.colors.onAccent,
      },
    }),
  );
}

export const ProfileThemeSelector = memo(ProfileThemeSelectorInner);

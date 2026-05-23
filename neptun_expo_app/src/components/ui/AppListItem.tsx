import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps, ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';
import { NeptunPressable } from '../../design/components/NeptunPressable';
import { useAppTheme, useThemedStyles } from '../../theme/useAppTheme';
import { AppText } from './AppText';

type Props = {
  icon: ComponentProps<typeof Ionicons>['name'];
  label: string;
  subtitle?: string;
  badge?: string;
  trailing?: ReactNode;
  showDivider?: boolean;
  /** When false, row aligns with parent horizontal padding (default true). */
  inset?: boolean;
  onPress?: () => void;
};

export function AppListItem({
  icon,
  label,
  subtitle,
  badge,
  trailing,
  showDivider,
  inset = true,
  onPress,
}: Props) {
  const { theme } = useAppTheme();
  const styles = useListItemStyles(inset);

  const row = (
    <View style={[styles.row, showDivider && styles.divider]}>
      <View style={styles.iconWrap}>
        <Ionicons name={icon} size={20} color={theme.colors.primary} />
      </View>
      <View style={styles.copy}>
        <AppText variant="cardTitle">{label}</AppText>
        {subtitle ? (
          <AppText variant="meta" muted numberOfLines={2}>
            {subtitle}
          </AppText>
        ) : null}
      </View>
      {badge ? (
        <View style={styles.badge}>
          <AppText variant="meta" accent>
            {badge}
          </AppText>
        </View>
      ) : null}
      {trailing ?? (onPress ? <Ionicons name="chevron-forward" size={18} color={theme.colors.textMuted} /> : null)}
    </View>
  );

  if (!onPress) return row;

  return (
    <NeptunPressable haptic onPress={onPress}>
      {row}
    </NeptunPressable>
  );
}

function useListItemStyles(inset: boolean) {
  return useThemedStyles((t) =>
    StyleSheet.create({
      row: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 10,
        paddingHorizontal: inset ? t.spacing.screenH : 0,
        paddingVertical: 11,
        minHeight: 44,
      },
      divider: {
        borderBottomWidth: StyleSheet.hairlineWidth,
        borderBottomColor: t.colors.divider,
      },
      iconWrap: {
        width: 32,
        height: 32,
        borderRadius: 8,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: t.colors.surfaceSoft,
      },
      copy: { flex: 1, minWidth: 0, gap: 2 },
      badge: {
        paddingHorizontal: 8,
        paddingVertical: 4,
        borderRadius: 8,
        backgroundColor: t.colors.surfaceHighlight,
      },
    }),
  );
}

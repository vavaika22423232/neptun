import type { ComponentProps, ReactNode } from 'react';
import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Text } from '../../../../components/Text';
import { NeptunPressable } from '../../../../design/components/NeptunPressable';
import { fonts } from '../../../../theme/fonts';
import { useThemedStyles } from '../../../../theme/useAppTheme';
import { profileTokens } from '../../profileTokens';
import { ProBadge } from './ProBadge';
import { SettingsIcon } from './SettingsIcon';
import type { SettingsIconTone } from './settingsIconTones';

export type SettingsRowProps = {
  icon?: ComponentProps<typeof Ionicons>['name'];
  iconTone?: SettingsIconTone;
  label: string;
  subtitle?: string;
  detail?: string;
  badge?: string;
  trailing?: ReactNode;
  showDivider?: boolean;
  destructive?: boolean;
  onPress?: () => void;
};

function SettingsRowInner({
  icon,
  iconTone,
  label,
  subtitle,
  detail,
  badge,
  trailing,
  showDivider,
  destructive,
  onPress,
}: SettingsRowProps) {
  const styles = useRowStyles();
  const hasIcon = Boolean(icon);

  const content = (
    <>
      <View style={styles.row}>
        {icon ? <SettingsIcon name={icon} tone={iconTone} /> : null}
        <View style={styles.copy}>
          <Text style={[styles.label, destructive && styles.destructiveLabel]}>{label}</Text>
          {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
        </View>
        {badge ? <ProBadge label={badge} /> : null}
        {detail ? <Text style={styles.detail}>{detail}</Text> : null}
        {trailing ??
          (onPress ? (
            <Ionicons name="chevron-forward" size={18} color={styles.chevronColor.color} />
          ) : null)}
      </View>
      {showDivider ? <View style={[styles.divider, hasIcon && styles.dividerInset]} /> : null}
    </>
  );

  if (!onPress) return <View>{content}</View>;
  return (
    <NeptunPressable haptic onPress={onPress}>
      {content}
    </NeptunPressable>
  );
}

function useRowStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      row: {
        flexDirection: 'row',
        alignItems: 'center',
        minHeight: profileTokens.rowMinHeight,
        paddingHorizontal: profileTokens.rowPadH,
        paddingVertical: profileTokens.rowPadV,
        gap: 12,
      },
      copy: { flex: 1, minWidth: 0, gap: 2 },
      label: {
        fontFamily: fonts.medium,
        fontSize: profileTokens.type.rowTitle.fontSize,
        lineHeight: profileTokens.type.rowTitle.lineHeight,
        color: t.colors.textPrimary,
      },
      destructiveLabel: {
        color: t.colors.danger,
      },
      subtitle: {
        fontFamily: fonts.regular,
        fontSize: profileTokens.type.rowSubtitle.fontSize,
        lineHeight: profileTokens.type.rowSubtitle.lineHeight,
        color: t.colors.textMuted,
      },
      detail: {
        fontFamily: fonts.regular,
        fontSize: 14,
        color: t.colors.textMuted,
        marginRight: 2,
      },
      chevronColor: { color: t.colors.textFaint },
      divider: {
        height: StyleSheet.hairlineWidth,
        backgroundColor: t.colors.divider,
        marginLeft: profileTokens.rowPadH,
      },
      dividerInset: {
        marginLeft: profileTokens.rowPadH + profileTokens.iconColWidth + 12,
      },
    }),
  );
}

export const SettingsRow = memo(SettingsRowInner);

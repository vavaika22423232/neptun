import { Ionicons } from '@expo/vector-icons';
import type { ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';
import { Text } from '../Text';
import { NeptunPressable } from '../../design/components/NeptunPressable';
import { fonts } from '../../theme/fonts';
import { useProfileTheme, useThemedStyles } from '../../theme/useAppTheme';
import { ProBadge } from './ProBadge';

type Props = {
  icon: React.ComponentProps<typeof Ionicons>['name'];
  label: string;
  subtitle?: string;
  badge?: string;
  trailing?: ReactNode;
  iconAccent?: string;
  showDividerBelow?: boolean;
  onPress?: () => void;
};

export function ProfileNavTile({
  icon,
  label,
  subtitle,
  badge,
  trailing,
  iconAccent,
  showDividerBelow,
  onPress,
}: Props) {
  const profile = useProfileTheme();
  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      row: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 16,
        paddingVertical: t.profile.rowPadV,
        gap: 12,
      },
      plate: {
        width: 38,
        height: 38,
        borderRadius: 12,
        alignItems: 'center',
        justifyContent: 'center',
      },
      body: { flex: 1, minWidth: 0 },
      label: {
        fontFamily: fonts.medium,
        fontSize: 16,
        color: t.profile.textPrimary,
        letterSpacing: -0.15,
      },
      subtitle: {
        marginTop: 2,
        fontSize: 12,
        lineHeight: 16,
        color: t.profile.textSecondary,
      },
      trailSpacer: { width: 4 },
      divider: {
        height: StyleSheet.hairlineWidth,
        backgroundColor: t.profile.divider,
        marginLeft: 66,
        marginRight: 16,
      },
    }),
  );

  const accent = iconAccent ?? profile.premiumAccent;
  const row = (
    <NeptunPressable
      haptic={!!onPress}
      disabled={!onPress}
      onPress={onPress}
      style={styles.row}
    >
      <View style={[styles.plate, { backgroundColor: accent + '18' }]}>
        <Ionicons name={icon} size={19} color={accent} />
      </View>
      <View style={styles.body}>
        <Text style={styles.label}>{label}</Text>
        {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
      </View>
      {badge ? <ProBadge label={badge} /> : null}
      {trailing ?? (onPress ? <Ionicons name="chevron-forward" size={17} color={profile.textTertiary} /> : <View style={styles.trailSpacer} />)}
    </NeptunPressable>
  );

  if (!showDividerBelow) return row;
  return (
    <View>
      {row}
      <View style={styles.divider} />
    </View>
  );
}

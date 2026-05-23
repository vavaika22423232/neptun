import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { StyleSheet, View } from 'react-native';
import { ProfileNavTile } from '../../../components/profile/ProfileNavTile';
import { Text } from '../../../components/Text';
import { fonts } from '../../../theme/fonts';
import { useAppTheme, useThemedStyles } from '../../../theme/useAppTheme';

type Props = {
  deviceId: string | null;
  regionCount: number;
  notificationsOn: boolean;
  onRegionsPress: () => void;
};

function shortDeviceId(id: string | null): string {
  if (!id) return '—';
  return '••••••';
}

export function ProfileAccountCard({ deviceId, regionCount, notificationsOn, onRegionsPress }: Props) {
  const { theme } = useAppTheme();
  const p = theme.profile;
  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      summary: {
        flexDirection: 'row',
        marginHorizontal: 12,
        marginTop: 12,
        marginBottom: 4,
        paddingVertical: 14,
        paddingHorizontal: 8,
        borderRadius: t.profile.radiusRow,
        backgroundColor: t.profile.iconBg,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.profile.divider,
      },
      summaryDivider: {
        width: StyleSheet.hairlineWidth,
        backgroundColor: t.profile.divider,
        marginVertical: 6,
      },
      cell: {
        flex: 1,
        alignItems: 'center',
        gap: 5,
        paddingHorizontal: 4,
      },
      cellIcon: {
        width: 28,
        height: 28,
        borderRadius: 10,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: t.colors.surfaceHighlight,
      },
      cellLabel: {
        fontFamily: fonts.regular,
        fontSize: 11,
        color: t.profile.textTertiary,
      },
      cellValue: {
        fontFamily: fonts.semiBold,
        fontSize: 13,
        color: t.profile.textPrimary,
        maxWidth: '100%',
      },
    }),
  );

  return (
    <View>
      <View style={styles.summary}>
        <SummaryCell styles={styles} icon="phone-portrait-outline" label="Пристрій" value={shortDeviceId(deviceId)} muted={p.textTertiary} />
        <View style={styles.summaryDivider} />
        <SummaryCell
          styles={styles}
          icon="notifications-outline"
          label="Push"
          value={notificationsOn ? 'Увімк.' : 'Вимкн.'}
          valueColor={notificationsOn ? p.statusCalm : p.textSecondary}
          muted={p.textTertiary}
        />
        <View style={styles.summaryDivider} />
        <SummaryCell styles={styles} icon="map-outline" label="Регіони" value={regionCount > 0 ? String(regionCount) : '0'} muted={p.textTertiary} />
      </View>
      <ProfileNavTile
        icon="options-outline"
        label="Керувати регіонами"
        subtitle={regionCount > 0 ? `Обрано ${regionCount}` : 'Додайте зони сповіщень'}
        iconAccent={p.premiumAccent}
        onPress={onRegionsPress}
      />
    </View>
  );
}

function SummaryCell({
  icon,
  label,
  value,
  valueColor,
  muted,
  styles,
}: {
  icon: ComponentProps<typeof Ionicons>['name'];
  label: string;
  value: string;
  valueColor?: string;
  muted: string;
  styles: {
    cell: object;
    cellIcon: object;
    cellLabel: object;
    cellValue: object;
  };
}) {
  return (
    <View style={styles.cell}>
      <View style={styles.cellIcon}>
        <Ionicons name={icon} size={15} color={muted} />
      </View>
      <Text style={styles.cellLabel}>{label}</Text>
      <Text style={[styles.cellValue, valueColor ? { color: valueColor } : null]} numberOfLines={1}>
        {value}
      </Text>
    </View>
  );
}

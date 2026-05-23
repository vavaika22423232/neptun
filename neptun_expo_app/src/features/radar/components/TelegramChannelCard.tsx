import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, View } from 'react-native';
import { AppCard } from '../../../components/ui/AppCard';
import { Text } from '../../../components/Text';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { openNeptunTelegramChannel } from '../../../core/utils/openNeptunTelegram';
import { useAppTheme, useThemedStyles } from '../../../theme/useAppTheme';
import { fonts } from '../../../theme/fonts';

type Props = {
  compact: boolean;
  onDismiss: () => void;
};

export function TelegramChannelCard({ compact, onDismiss }: Props) {
  const { theme } = useAppTheme();
  const styles = useTelegramCardStyles();

  if (compact) {
    return (
      <NeptunPressable haptic onPress={() => void openNeptunTelegramChannel('radar_compact')}>
        <View style={styles.compactRow}>
          <Ionicons name="paper-plane" size={18} color={theme.colors.primary} />
          <Text style={styles.compactText}>Telegram — швидкі оновлення</Text>
          <Ionicons name="chevron-forward" size={18} color={theme.colors.textMuted} />
        </View>
      </NeptunPressable>
    );
  }

  return (
    <AppCard style={styles.card}>
      <NeptunPressable
        haptic
        containerStyle={{ flex: 1 }}
        onPress={() => void openNeptunTelegramChannel('radar_card')}
      >
        <View style={styles.row}>
          <View style={[styles.iconBox, { backgroundColor: theme.colors.primaryMuted }]}>
            <Ionicons name="paper-plane" size={22} color={theme.colors.primary} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.title}>Офіційний Telegram канал</Text>
            <Text style={styles.sub}>Швидкі оновлення та важливі повідомлення</Text>
          </View>
          <Ionicons name="arrow-forward" size={20} color={theme.colors.textSecondary} />
        </View>
      </NeptunPressable>
      <NeptunPressable haptic={false} onPress={onDismiss} style={styles.close}>
        <Ionicons name="close" size={20} color={theme.colors.textMuted} />
      </NeptunPressable>
    </AppCard>
  );
}

function useTelegramCardStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      card: {
        flexDirection: 'row',
        alignItems: 'center',
        padding: t.spacing.md,
      },
      row: { flexDirection: 'row', alignItems: 'center', gap: 14, flex: 1 },
      iconBox: {
        width: 44,
        height: 44,
        borderRadius: 14,
        alignItems: 'center',
        justifyContent: 'center',
      },
      title: { fontFamily: fonts.bold, fontSize: 16, color: t.colors.textPrimary },
      sub: {
        fontFamily: fonts.medium,
        fontSize: 13,
        color: t.colors.textSecondary,
        marginTop: 4,
      },
      close: { padding: 4, marginLeft: 4 },
      compactRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        paddingVertical: 8,
      },
      compactText: {
        flex: 1,
        fontFamily: fonts.semiBold,
        fontSize: 13,
        color: t.colors.textSecondary,
      },
    }),
  );
}

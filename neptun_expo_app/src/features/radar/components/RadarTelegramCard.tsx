import { Ionicons } from '@expo/vector-icons';
import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import { Text } from '../../../components/Text';
import { openNeptunTelegramChannel } from '../../../core/utils/openNeptunTelegram';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { fonts } from '../../../theme/fonts';
import { useThemedStyles } from '../../../theme/useAppTheme';
import { RadarFeedCard } from './RadarFeedCard';

function RadarTelegramCardInner() {
  const styles = useTelegramCardStyles();

  return (
    <RadarFeedCard>
      <NeptunPressable
        haptic
        style={styles.row}
        onPress={() => void openNeptunTelegramChannel('radar_feed')}
        accessibilityRole="link"
        accessibilityLabel="Офіційний Telegram NEPTUN"
      >
        <View style={styles.icon}>
          <Ionicons name="paper-plane-outline" size={20} color={styles.iconColor.color} />
        </View>
        <View style={styles.copy}>
          <Text style={styles.title}>Telegram канал</Text>
          <Text style={styles.sub}>Офіційні оновлення NEPTUN</Text>
        </View>
        <Ionicons name="chevron-forward" size={16} color={styles.mutedColor.color} />
      </NeptunPressable>
    </RadarFeedCard>
  );
}

function useTelegramCardStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      row: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
        paddingHorizontal: t.radar.cardPad,
        paddingVertical: 14,
      },
      icon: {
        width: 40,
        height: 40,
        borderRadius: 12,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: t.scheme === 'light' ? '#F2F2F7' : 'rgba(255,255,255,0.08)',
      },
      iconColor: { color: t.colors.textPrimary },
      copy: { flex: 1, gap: 2 },
      title: {
        fontFamily: fonts.semiBold,
        fontSize: 15,
        color: t.colors.textPrimary,
      },
      sub: {
        fontFamily: fonts.regular,
        fontSize: 13,
        color: t.colors.textMuted,
      },
      mutedColor: { color: t.colors.textMuted },
    }),
  );
}

export const RadarTelegramCard = memo(RadarTelegramCardInner);

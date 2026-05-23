import { Ionicons } from '@expo/vector-icons';
import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import { Text } from './Text';
import { openNeptunTelegramChannel } from '../core/utils/openNeptunTelegram';
import { NeptunPressable } from '../design/components/NeptunPressable';
import { useAppTheme, useThemedStyles } from '../theme/useAppTheme';
import { fonts } from '../theme/fonts';

/** Компактний рядок над tab bar — «Хлопці пишуть у Telegram». */
function TelegramBottomStripInner() {
  const { theme } = useAppTheme();
  const styles = useStripStyles();

  return (
    <NeptunPressable
      haptic
      scaleTo={0.99}
      style={styles.root}
      onPress={() => void openNeptunTelegramChannel('tab_bar_strip')}
      accessibilityRole="link"
      accessibilityLabel="Хлопці пишуть у Telegram — підписатись"
    >
      <View style={styles.iconWrap}>
        <Ionicons name="paper-plane" size={16} color={theme.colors.primary} />
      </View>
      <View style={styles.textCol}>
        <Text style={styles.hint}>Щоб не перевіряти застосунок</Text>
        <Text style={styles.title} numberOfLines={1}>
          Хлопці пишуть у Telegram
        </Text>
      </View>
      <View style={styles.cta}>
        <Text style={styles.ctaText}>Підписатись</Text>
      </View>
    </NeptunPressable>
  );
}

function useStripStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      root: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 10,
        marginHorizontal: 16,
        marginBottom: 6,
        paddingHorizontal: 12,
        paddingVertical: 10,
        borderRadius: 18,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.colors.border,
        backgroundColor: t.colors.card,
        ...t.shadows.sm,
      },
      iconWrap: {
        width: 32,
        height: 32,
        borderRadius: 10,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: t.colors.primaryMuted,
      },
      textCol: { flex: 1, minWidth: 0, gap: 1 },
      hint: {
        fontFamily: fonts.medium,
        fontSize: 10,
        color: t.colors.textMuted,
      },
      title: {
        fontFamily: fonts.bold,
        fontSize: 13,
        color: t.colors.textPrimary,
      },
      cta: {
        paddingHorizontal: 10,
        paddingVertical: 6,
        borderRadius: 12,
        backgroundColor: t.colors.primaryMuted,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.colors.border,
      },
      ctaText: {
        fontFamily: fonts.bold,
        fontSize: 11,
        color: t.colors.primary,
      },
    }),
  );
}

export const TelegramBottomStrip = memo(TelegramBottomStripInner);

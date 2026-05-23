import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import { Text } from '../../../components/Text';
import { openNeptunTelegramChannel } from '../../../core/utils/openNeptunTelegram';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { fonts } from '../../../theme/fonts';
import { useThemedStyles } from '../../../theme/useAppTheme';

type Props = {
  onPress?: () => void;
  /** Inline segment inside the map search bar row. */
  compact?: boolean;
};

function MapTelegramBannerInner({ onPress, compact = false }: Props) {
  const styles = useBannerStyles(compact);
  const handlePress = onPress ?? (() => void openNeptunTelegramChannel('map_header'));

  return (
    <NeptunPressable
      haptic
      scaleTo={0.99}
      onPress={handlePress}
      accessibilityRole="link"
      accessibilityLabel="ХЛОПЦі в Telegram"
      style={styles.pressWrap}
    >
      <LinearGradient
        colors={['#35B5F0', '#229ED9']}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={styles.banner}
      >
        <View style={styles.iconWrap}>
          <Ionicons name="paper-plane" size={compact ? 14 : 20} color="#229ED9" />
        </View>
        <View style={styles.copy}>
          <Text style={styles.title} numberOfLines={compact ? 2 : 1}>
            {compact ? 'ХЛОПЦі\nв Telegram' : 'ХЛОПЦі в Telegram'}
          </Text>
          {!compact ? (
            <Text style={styles.subtitle}>Офіційний канал · швидкі оновлення</Text>
          ) : null}
        </View>
        {!compact ? (
          <View style={styles.cta}>
            <Ionicons name="chevron-forward" size={18} color="#111111" />
          </View>
        ) : null}
      </LinearGradient>
    </NeptunPressable>
  );
}

function useBannerStyles(compact: boolean) {
  return useThemedStyles(() =>
    StyleSheet.create({
      pressWrap: compact
        ? {
            flexShrink: 0,
            width: 118,
            height: 40,
          }
        : {
            alignSelf: 'stretch',
            borderRadius: 16,
            overflow: 'hidden',
            shadowColor: '#229ED9',
            shadowOpacity: 0.32,
            shadowRadius: 12,
            shadowOffset: { width: 0, height: 6 },
            elevation: 6,
          },
      banner: compact
        ? {
            flex: 1,
            paddingHorizontal: 10,
            flexDirection: 'row',
            alignItems: 'center',
            gap: 7,
          }
        : {
            minHeight: 48,
            paddingHorizontal: 14,
            paddingVertical: 12,
            flexDirection: 'row',
            alignItems: 'center',
            gap: 12,
            borderRadius: 16,
            borderWidth: StyleSheet.hairlineWidth,
            borderColor: 'rgba(255,255,255,0.18)',
            overflow: 'hidden',
          },
      iconWrap: {
        width: compact ? 24 : 36,
        height: compact ? 24 : 36,
        borderRadius: compact ? 12 : 18,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#FFFFFF',
      },
      copy: {
        flex: 1,
        minWidth: 0,
        gap: compact ? 0 : 2,
      },
      title: {
        fontFamily: fonts.bold,
        fontSize: compact ? 10 : 15,
        lineHeight: compact ? 12 : 18,
        color: '#FFFFFF',
        letterSpacing: compact ? 0 : -0.1,
      },
      subtitle: {
        fontFamily: fonts.medium,
        fontSize: 12,
        lineHeight: 15,
        color: 'rgba(255,255,255,0.78)',
      },
      cta: {
        width: 34,
        height: 34,
        borderRadius: 17,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#FFFFFF',
      },
    }),
  );
}

export const MapTelegramBanner = memo(MapTelegramBannerInner);

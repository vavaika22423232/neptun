import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Text } from '../../../components/Text';
import { RoutePaths } from '../../../core/navigation/routePaths';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { fonts } from '../../../theme/fonts';
import { useThemedStyles } from '../../../theme/useAppTheme';
import { RadarFeedCard } from './RadarFeedCard';

function RadarHistoryLinkInner() {
  const router = useRouter();
  const styles = useHistoryLinkStyles();

  return (
    <RadarFeedCard>
      <NeptunPressable
        haptic
        style={styles.row}
        onPress={() => router.push(RoutePaths.history)}
      >
        <View style={styles.icon}>
          <Ionicons name="time-outline" size={20} color={styles.iconColor.color} />
        </View>
        <Text style={styles.label}>Історія тривог</Text>
        <Ionicons name="chevron-forward" size={16} color={styles.mutedColor.color} />
      </NeptunPressable>
    </RadarFeedCard>
  );
}

function useHistoryLinkStyles() {
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
      label: {
        flex: 1,
        fontFamily: fonts.semiBold,
        fontSize: 15,
        color: t.colors.textPrimary,
      },
      mutedColor: { color: t.colors.textMuted },
    }),
  );
}

export const RadarHistoryLink = memo(RadarHistoryLinkInner);

import { Ionicons } from '@expo/vector-icons';
import { memo, useMemo } from 'react';
import { StyleSheet, View } from 'react-native';
import { Text } from '../../../components/Text';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { fonts } from '../../../theme/fonts';
import { useAppTheme } from '../../../theme/useAppTheme';
import { useMapStore } from '../state/mapStore';
import { relativeTimeUk } from '../utils/relativeTimeUk';

type Props = {
  onOpenRadar: () => void;
  onConfigure: () => void;
};

function statusText(phase: string, lastRefresh?: number): string {
  if (phase === 'live') {
    return lastRefresh ? `Оновлено ${relativeTimeUk(new Date(lastRefresh))}` : 'Live канал активний';
  }
  if (phase === 'connecting') return 'Підключення до live каналу';
  if (phase === 'reconnecting' || phase === 'offline') return 'Працюємо з кешем, відновлюємо канал';
  return 'Готуємо live стан';
}

function pluralRegions(count: number): string {
  if (count === 1) return '1 область';
  if (count > 1 && count < 5) return `${count} області`;
  return `${count} областей`;
}

function LiveSituationCardInner({ onOpenRadar, onConfigure }: Props) {
  const { theme } = useAppTheme();
  const alarms = useMapStore((s) => s.alarms);
  const markers = useMapStore((s) => s.markers);
  const linkPhase = useMapStore((s) => s.linkPhase);
  const lastRefresh = useMapStore((s) => s.lastSignificantRefreshAt);

  const model = useMemo(() => {
    const regions = alarms.stateCount ?? 0;
    const events = markers.length;
    const hasActivity = regions > 0 || events > 0;
    return {
      hasActivity,
      title: hasActivity ? 'Є активна ситуація' : 'Зараз спокійно',
      body:
        regions > 0
          ? `Тривоги активні у ${pluralRegions(regions)}. Radar покаже розвиток подій.`
          : events > 0
            ? `${events} live ${events === 1 ? 'подія' : 'подій'} на мапі.`
            : 'Ваш Live екран готовий. Додайте регіони, щоб бачити персональний стан.',
      tone: hasActivity ? theme.colors.warning : theme.colors.success,
    };
  }, [alarms.stateCount, markers.length, theme.colors.success, theme.colors.warning]);

  const styles = useMemo(
    () =>
      StyleSheet.create({
        card: {
          borderRadius: theme.radii.lg,
          backgroundColor: theme.colors.card,
          borderWidth: StyleSheet.hairlineWidth,
          borderColor: theme.colors.border,
          padding: 14,
          gap: 12,
        },
        header: {
          flexDirection: 'row',
          alignItems: 'center',
          gap: 10,
        },
        icon: {
          width: 38,
          height: 38,
          borderRadius: 19,
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: model.tone + '22',
        },
        titleWrap: { flex: 1, minWidth: 0 },
        label: {
          fontFamily: fonts.semiBold,
          fontSize: 11,
          lineHeight: 14,
          color: theme.colors.textMuted,
          textTransform: 'uppercase',
        },
        title: {
          marginTop: 2,
          fontFamily: fonts.bold,
          fontSize: 16,
          lineHeight: 21,
          color: theme.colors.textPrimary,
        },
        body: {
          fontFamily: fonts.medium,
          fontSize: 13,
          lineHeight: 19,
          color: theme.colors.textSecondary,
        },
        actions: {
          flexDirection: 'row',
          gap: 8,
        },
        actionPrimary: {
          flex: 1,
          minHeight: 42,
          borderRadius: theme.radii.pill,
          alignItems: 'center',
          justifyContent: 'center',
          flexDirection: 'row',
          gap: 7,
          backgroundColor: theme.colors.primary,
        },
        actionSecondary: {
          width: 46,
          minHeight: 42,
          borderRadius: theme.radii.pill,
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: theme.colors.surfaceHighlight,
          borderWidth: StyleSheet.hairlineWidth,
          borderColor: theme.colors.border,
        },
        actionText: {
          color: theme.colors.onAccent,
          fontFamily: fonts.bold,
          fontSize: 13,
        },
      }),
    [model.tone, theme],
  );

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <View style={styles.icon}>
          <Ionicons name={model.hasActivity ? 'pulse' : 'checkmark-circle'} size={20} color={model.tone} />
        </View>
        <View style={styles.titleWrap}>
          <Text style={styles.label}>{statusText(linkPhase, lastRefresh)}</Text>
          <Text style={styles.title} numberOfLines={1}>
            {model.title}
          </Text>
        </View>
      </View>

      <Text style={styles.body} numberOfLines={2}>
        {model.body}
      </Text>

      <View style={styles.actions}>
        <NeptunPressable haptic style={styles.actionPrimary} onPress={onOpenRadar}>
          <Ionicons name="radio-outline" size={17} color={theme.colors.onAccent} />
          <Text style={styles.actionText}>Open Radar</Text>
        </NeptunPressable>
        <NeptunPressable haptic accessibilityLabel="Налаштувати регіони" style={styles.actionSecondary} onPress={onConfigure}>
          <Ionicons name="options-outline" size={18} color={theme.colors.textSecondary} />
        </NeptunPressable>
      </View>
    </View>
  );
}

export const LiveSituationCard = memo(LiveSituationCardInner);

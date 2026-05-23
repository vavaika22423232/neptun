import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { Pressable, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Text } from '../../../components/Text';
import { radii, typography } from '../../../design/tokens';
import { fonts } from '../../../theme/fonts';
import type { ThemeColors } from '../../../theme/types';
import { useAppTheme, useThemedStyles } from '../../../theme/useAppTheme';
import { relativeTimeUk } from '../utils/relativeTimeUk';
import { useMapStore } from '../state/mapStore';

type Props = {
  /** Extra top offset when ballistic banner is visible (Flutter native_map spacing). */
  offsetTop?: number;
};

function dotColorForPhase(phase: string, c: ThemeColors): string {
  switch (phase) {
    case 'live':
      return c.success;
    case 'reconnecting':
    case 'offline':
      return c.warning;
    default:
      return c.primarySoft;
  }
}

function buildSubtitle(phase: string, lastRefresh?: number): string {
  switch (phase) {
    case 'idle':
      return 'Готуємо зʼєднання з живими даними';
    case 'connecting':
      return 'Підключення до каналу оновлень…';
    case 'reconnecting':
    case 'offline':
      return 'Відновлюємо канал даних…';
    case 'live':
      if (!lastRefresh) return 'Канал активний — чекаємо на зміни з сервера';
      return `Дані сервіса оновлено · ${relativeTimeUk(new Date(lastRefresh))}`;
    default:
      return 'Канал даних';
  }
}

/** @deprecated Use `MapSituationCard`. */
export function MapSituationStatusStrip({ offsetTop = 0 }: Props) {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { theme } = useAppTheme();
  const c = theme.colors;
  const linkPhase = useMapStore((s) => s.linkPhase);
  const lastRefresh = useMapStore((s) => s.lastSignificantRefreshAt);

  const subtitle = buildSubtitle(linkPhase, lastRefresh);
  const dotColor = dotColorForPhase(linkPhase, c);
  const top = insets.top + 108 + offsetTop;

  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      wrap: {
        position: 'absolute',
        left: 14,
        right: 14,
        zIndex: 20,
        elevation: 20,
      },
      panel: {
        borderRadius: radii.xl,
        backgroundColor: t.colors.surfaceGlassStrong,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.colors.borderStrong,
        ...t.shadows.md,
      },
      body: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 12,
        paddingVertical: 10,
        gap: 8,
      },
      kicker: {
        fontFamily: fonts.semiBold,
        ...typography.micro,
        color: t.colors.textFaint,
        letterSpacing: 0.5,
        textTransform: 'uppercase',
      },
      subtitleRow: {
        flexDirection: 'row',
        alignItems: 'flex-start',
        gap: 8,
        marginTop: 4,
      },
      dot: {
        width: 10,
        height: 10,
        borderRadius: 5,
        marginTop: 4,
      },
      subtitle: {
        flex: 1,
        fontFamily: fonts.semiBold,
        fontSize: 13,
        lineHeight: 18,
        color: t.colors.textSecondary,
      },
      tuneBtn: {
        width: 38,
        height: 38,
        borderRadius: radii.pill,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: t.colors.surfaceHighlight,
      },
    }),
  );

  return (
    <View style={[styles.wrap, { top }]} pointerEvents="box-none" collapsable={false}>
      <View style={styles.panel}>
        <View style={styles.body}>
          <View style={{ flex: 1 }}>
            <Text style={styles.kicker}>Ситуація зараз</Text>
            <View style={styles.subtitleRow}>
              <View style={[styles.dot, { backgroundColor: dotColor }]} />
              <Text style={styles.subtitle} numberOfLines={2}>
                {subtitle}
              </Text>
            </View>
          </View>
          <Pressable
            accessibilityLabel="Радар та фільтри"
            onPress={() => router.push('/radar-full')}
            style={styles.tuneBtn}
          >
            <Ionicons name="options-outline" size={20} color={c.textSecondary} />
          </Pressable>
        </View>
      </View>
    </View>
  );
}

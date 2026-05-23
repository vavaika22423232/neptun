import { Ionicons } from '@expo/vector-icons';
import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Dimensions,
  RefreshControl,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';
import { Card } from '../components/Card';
import { ProFeatureGate } from '../components/ProFeatureGate';
import { Text } from '../components/Text';
import { AlarmHeatmapMap } from '../features/heatmap/components/AlarmHeatmapMap';
import { ProFeature } from '../core/pro/proGate';
import { loadHeatmapSnapshot, type HeatmapSnapshot } from '../services/alarmStatsService';
import { colors, radii, spacing } from '../theme/colors';
import { fonts } from '../theme/fonts';
import { useLegacyScreenStyles } from '../theme/useLegacyScreenStyles';

export function HeatmapScreen() {
  const styles = useScreenStyles();
  const [snap, setSnap] = useState<HeatmapSnapshot | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setSnap(await loadHeatmapSnapshot());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const mapHeight = Math.round(Dimensions.get('window').height * 0.42);

  return (
    <ProFeatureGate feature={ProFeature.Heatmap}>
      <ScrollView
        style={styles.root}
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl refreshing={loading} onRefresh={() => void load()} tintColor={colors.accent} />
        }
      >
        {loading && !snap ? (
          <View style={styles.loadingBox}>
            <ActivityIndicator color={colors.accent} />
          </View>
        ) : null}

        {!loading && snap && !snap.hasAnyMergedRow ? (
          <Card style={styles.emptyCard}>
            <Ionicons name="flame" size={48} color={colors.accent} style={{ opacity: 0.5 }} />
            <Text style={styles.emptyTitle}>Поки немає даних</Text>
            <Text muted style={styles.emptySub}>
              {snap.hasRegions
                ? 'Лічильник оновлюється, коли додаток отримує відбій тривоги по регіону. Потягніть вниз, щоб оновити.'
                : 'Додайте регіони у налаштуваннях, щоб отримувати тривоги.'}
            </Text>
          </Card>
        ) : null}

        {snap && snap.hasAnyMergedRow ? (
          <>
            <Text style={styles.sectionLabel}>Теплова інтенсивність по областях</Text>
            <View style={[styles.mapFrame, { height: mapHeight }]}>
              <AlarmHeatmapMap countsByStateId={snap.countsByStateId} />
            </View>

            <View style={styles.legendRow}>
              <View style={styles.legendBar} />
              <Text muted style={styles.legendHint}>
                менше
              </Text>
              <Text muted style={styles.legendHint}>
                більше
              </Text>
            </View>

            <Text style={[styles.sectionLabel, { marginTop: spacing.md }]}>Рейтинг областей</Text>
            {snap.oblastRanking.length === 0 ? (
              <Text muted>Немає накопичених тривог по областях.</Text>
            ) : (
              snap.oblastRanking.map((row) => (
                <Card key={row.name} style={styles.rankRow}>
                  <Text style={styles.rankName}>{row.name}</Text>
                  <Text style={styles.rankCount}>{row.count}</Text>
                </Card>
              ))
            )}
          </>
        ) : null}
      </ScrollView>
    </ProFeatureGate>
  );
}


function useScreenStyles() {
  return useLegacyScreenStyles((c) => ({
  root: { flex: 1, backgroundColor: c.bg },
  content: { padding: spacing.lg, paddingBottom: spacing.xxl },
  loadingBox: { paddingVertical: 48, alignItems: 'center' },
  emptyCard: { alignItems: 'center', gap: spacing.sm, padding: spacing.xl },
  emptyTitle: { fontFamily: fonts.semiBold, fontSize: 16, color: c.text },
  emptySub: { textAlign: 'center', fontSize: 14, lineHeight: 20 },
  sectionLabel: {
    fontFamily: fonts.semiBold,
    fontSize: 13,
    color: c.muted,
    marginBottom: spacing.sm,
  },
  mapFrame: {
    borderRadius: radii.md,
    overflow: 'hidden',
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: c.border,
  },
  legendRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginTop: spacing.sm,
  },
  legendBar: {
    flex: 1,
    height: 8,
    borderRadius: 4,
    backgroundColor: c.accent,
    opacity: 0.85,
  },
  legendHint: { fontSize: 11 },
  rankRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: spacing.sm,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.md,
  },
  rankName: { fontFamily: fonts.semiBold, fontSize: 15 },
  rankCount: { fontFamily: fonts.bold, fontSize: 16, color: c.warning },
}));
}

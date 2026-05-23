import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { useCallback } from 'react';
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';
import { Card } from '../components/Card';
import { PrimaryButton } from '../components/PrimaryButton';
import { Text } from '../components/Text';
import { radarRepository } from '../features/radar/data/radarRepository';
import { radarThreatTypeLabel } from '../features/radar/domain/radarThreatLabel';
import { colors, radii } from '../theme/colors';
import { fonts } from '../theme/fonts';
import { useLegacyScreenStyles } from '../theme/useLegacyScreenStyles';

/** Flutter `ThreatDashboardPage` — `/radar-full`. */
export function ThreatDashboardScreen() {
  const styles = useScreenStyles();
  const router = useRouter();
  const { data, isLoading, isError, refetch, isRefetching } = useQuery({
    queryKey: ['threat-dashboard'],
    queryFn: () => radarRepository.fetchSnapshot(180),
    refetchInterval: 30_000,
    staleTime: 15_000,
  });

  const onRefresh = useCallback(() => {
    void refetch();
  }, [refetch]);

  if (isLoading && !data) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator color={colors.accent} size="large" />
      </View>
    );
  }

  if (isError && !data) {
    return (
      <View style={styles.centered}>
        <Text title>Не вдалося завантажити дані</Text>
        <PrimaryButton onPress={onRefresh}>Повторити</PrimaryButton>
      </View>
    );
  }

  const markers = data?.markers ?? [];
  const activeAlarms = data?.activeOblastsUnderAlarm ?? 0;
  const grouped = groupByThreatType(markers);

  return (
    <ScrollView
      contentContainerStyle={styles.scroll}
      refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={onRefresh} tintColor={colors.accent} />}
    >
      <Card style={styles.summaryCard}>
        <View style={styles.summaryRow}>
          <View
            style={[
              styles.summaryIcon,
              { backgroundColor: activeAlarms > 0 ? colors.danger + '26' : colors.success + '26' },
            ]}
          >
            <Ionicons
              name={activeAlarms > 0 ? 'warning' : 'shield-checkmark'}
              size={24}
              color={activeAlarms > 0 ? colors.danger : colors.success}
            />
          </View>
          <View style={styles.summaryCopy}>
            <Text style={styles.summaryTitle}>
              {activeAlarms > 0 ? `Активні тривоги: ${activeAlarms}` : 'Тривог немає'}
            </Text>
            <Text muted style={styles.summarySub}>
              Загрози на карті: {markers.length}
            </Text>
          </View>
          <View style={[styles.badge, activeAlarms > 0 ? styles.badgeDanger : styles.badgeOk]}>
            <Text style={styles.badgeText}>{activeAlarms > 0 ? 'ТРИВОГА' : 'БЕЗПЕЧНО'}</Text>
          </View>
        </View>
      </Card>

      {markers.length === 0 ? (
        <View style={styles.empty}>
          <Ionicons name="shield-checkmark-outline" size={48} color={colors.muted} />
          <Text style={styles.emptyTitle}>Активних загроз немає</Text>
          <Text muted>Наразі ситуація спокійна</Text>
        </View>
      ) : (
        <>
          <Text style={styles.sectionTitle}>Активні загрози</Text>
          {grouped.map(([type, items]) => (
            <Pressable
              key={type}
              onPress={() => router.replace('/(tabs)')}
              style={({ pressed }) => [pressed && { opacity: 0.92 }]}
            >
              <Card style={styles.threatCard}>
                <View style={styles.threatRow}>
                  <Ionicons name={threatIconName(type)} size={20} color={colors.danger} />
                  <View style={styles.threatCopy}>
                    <Text style={styles.threatTitle}>{radarThreatTypeLabel(type)}</Text>
                    <Text muted numberOfLines={1} style={styles.threatPlaces}>
                      {items
                        .map((m) => String(m.place ?? m.location ?? ''))
                        .filter((s) => s.length > 0)
                        .slice(0, 3)
                        .join(', ')}
                    </Text>
                  </View>
                  <View style={styles.countBadge}>
                    <Text style={styles.countText}>{items.length}</Text>
                  </View>
                </View>
              </Card>
            </Pressable>
          ))}
        </>
      )}
    </ScrollView>
  );
}

function groupByThreatType(
  markers: Record<string, unknown>[],
): [string, Record<string, unknown>[]][] {
  const map = new Map<string, Record<string, unknown>[]>();
  for (const m of markers) {
    const type = String(m.threatType ?? m.type ?? 'unknown');
    const list = map.get(type) ?? [];
    list.push(m);
    map.set(type, list);
  }
  return [...map.entries()].sort((a, b) => b[1].length - a[1].length);
}

function threatIconName(type: string): ComponentProps<typeof Ionicons>['name'] {
  switch (type.toLowerCase()) {
    case 'shahed':
    case 'drone':
      return 'airplane';
    case 'raketa':
    case 'missile':
      return 'rocket';
    case 'ballistic':
      return 'warning';
    case 'avia':
      return 'navigate';
    case 'kab':
      return 'locate';
    default:
      return 'alert-circle';
  }
}


function useScreenStyles() {
  return useLegacyScreenStyles((c) => ({
  scroll: { padding: 16, paddingBottom: 32, gap: 8 },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 14, padding: 24 },
  summaryCard: { marginBottom: 8 },
  summaryRow: { flexDirection: 'row', alignItems: 'center', gap: 14 },
  summaryIcon: {
    width: 48,
    height: 48,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  summaryCopy: { flex: 1, gap: 2 },
  summaryTitle: { fontFamily: fonts.bold, fontSize: 16 },
  summarySub: { fontSize: 13 },
  badge: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: radii.pill,
  },
  badgeDanger: { backgroundColor: c.danger + '33' },
  badgeOk: { backgroundColor: c.success + '33' },
  badgeText: { fontFamily: fonts.bold, fontSize: 10, letterSpacing: 0.6 },
  sectionTitle: {
    fontFamily: fonts.bold,
    fontSize: 15,
    marginTop: 8,
    marginBottom: 4,
  },
  threatCard: { marginBottom: 8 },
  threatRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  threatCopy: { flex: 1, gap: 2 },
  threatTitle: { fontFamily: fonts.semiBold, fontSize: 14 },
  threatPlaces: { fontSize: 12 },
  countBadge: {
    minWidth: 28,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: radii.pill,
    backgroundColor: c.danger + '40',
    alignItems: 'center',
  },
  countText: { fontFamily: fonts.bold, fontSize: 12, color: c.danger },
  empty: { alignItems: 'center', gap: 8, marginTop: 48 },
  emptyTitle: { fontFamily: fonts.bold, fontSize: 16, marginTop: 8 },
}));
}

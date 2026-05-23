import { useCallback, useEffect, useMemo, useState } from 'react';
import { FlatList, StyleSheet, TextInput, View } from 'react-native';
import { Card } from '../components/Card';
import { PrimaryButton } from '../components/PrimaryButton';
import { Text } from '../components/Text';
import { NeptunEmptyState } from '../design/components/NeptunEmptyState';
import { NeptunLoading } from '../design/components/NeptunLoading';
import { NeptunViewScreen } from '../design/components/NeptunScrollScreen';
import { RewardedAdOffers } from '../features/monetization/components/RewardedAdOffers';
import { useEntitlements } from '../features/monetization/hooks/useEntitlements';
import { useProAccess } from '../features/pro/hooks/useProAccess';
import {
  monetizationApi,
  type AlertEvent,
} from '../features/monetization/services/monetizationApi';
import { monetizationAnalytics } from '../features/monetization/services/monetizationAnalytics';
import { adService } from '../services/adService';
import { palette, spacing } from '../design/tokens';

export function AlarmHistoryScreen() {
  const { features, plan, hasPlan } = useEntitlements();
  const { openPaywall } = useProAccess();
  const [loading, setLoading] = useState(true);
  const [events, setEvents] = useState<AlertEvent[]>([]);
  const [maxDays, setMaxDays] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [regionFilter, setRegionFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');

  const effectiveDays =
    adService.isHistoryUnlockedByReward() && plan === 'free' ? 1 : features.historyDays;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const from = new Date(Date.now() - effectiveDays * 24 * 3600 * 1000).toISOString();
      const data = await monetizationApi.fetchAlertHistory({
        region: regionFilter || undefined,
        from,
        type: typeFilter || undefined,
      });
      setEvents(data.events);
      setMaxDays(data.maxDays);
      monetizationAnalytics.historyOpened(plan, data.maxDays);
    } catch {
      setError('Не вдалося завантажити історію');
    } finally {
      setLoading(false);
    }
  }, [effectiveDays, plan, regionFilter, typeFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  const chartData = useMemo(() => {
    const byDay = new Map<string, number>();
    for (const ev of events) {
      const d = ev.startedAt.slice(0, 10);
      byDay.set(d, (byDay.get(d) ?? 0) + 1);
    }
    return [...byDay.entries()].sort((a, b) => a[0].localeCompare(b[0])).slice(-14);
  }, [events]);

  const maxBar = Math.max(1, ...chartData.map(([, n]) => n));

  if (loading) {
    return (
      <NeptunViewScreen padded={false} style={styles.root}>
        <NeptunLoading label="Завантаження історії…" />
      </NeptunViewScreen>
    );
  }

  return (
    <NeptunViewScreen padded={false} style={styles.root}>
      <View style={styles.header}>
        <Text subtitle>Історія та аналітика</Text>
        <Text muted>
          {plan.toUpperCase()} · до {maxDays} дн.
          {adService.isHistoryUnlockedByReward() && plan === 'free' ? ' (+24 год)' : ''}
        </Text>

        <TextInput
          style={styles.input}
          placeholder="Фільтр регіону (ID)"
          placeholderTextColor="#888"
          value={regionFilter}
          onChangeText={setRegionFilter}
          onSubmitEditing={() => {
            monetizationAnalytics.historyFilterUsed('region');
            void load();
          }}
        />
        <TextInput
          style={styles.input}
          placeholder="Тип (air_alarm, shahed…)"
          placeholderTextColor="#888"
          value={typeFilter}
          onChangeText={setTypeFilter}
          onSubmitEditing={() => {
            monetizationAnalytics.historyFilterUsed('type');
            void load();
          }}
        />
        <PrimaryButton variant="secondary" onPress={() => void load()}>
          Застосувати фільтр
        </PrimaryButton>

        {!hasPlan('pro') ? (
          <PrimaryButton
            variant="secondary"
            onPress={() => openPaywall({ source: 'history', lockedFeature: 'history_extended' })}
          >
            Розширена історія
          </PrimaryButton>
        ) : null}
      </View>

      {hasPlan('pro_plus') && chartData.length > 0 ? (
        <View style={styles.chart}>
          <Text muted>Графік подій по днях</Text>
          <View style={styles.chartRow}>
            {chartData.map(([day, count]) => (
              <View key={day} style={styles.barWrap}>
                <View style={[styles.bar, { height: 8 + (count / maxBar) * 72 }]} />
                <Text style={styles.barLabel}>{day.slice(5)}</Text>
              </View>
            ))}
          </View>
        </View>
      ) : null}

      <RewardedAdOffers />

      {error ? (
        <View style={styles.header}>
          <Text muted>{error}</Text>
        </View>
      ) : null}

      <FlatList
        data={events}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          <NeptunEmptyState
            icon="time-outline"
            title="Подій поки немає"
            subtitle="Історія наповнюється з моніторингу тривог NEPTUN"
          />
        }
        renderItem={({ item }) => (
          <Card>
            <Text subtitle>{item.title}</Text>
            <Text muted>
              {item.type} · регіон {item.regionId} · {new Date(item.startedAt).toLocaleString('uk-UA')}
            </Text>
            <Text>{item.description}</Text>
          </Card>
        )}
      />
    </NeptunViewScreen>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: palette.bg },
  list: { padding: spacing.screenH, gap: spacing.md, flexGrow: 1 },
  header: { padding: spacing.screenH, gap: 8 },
  input: {
    borderWidth: 1,
    borderColor: palette.border,
    borderRadius: 10,
    padding: 10,
    fontSize: 15,
    color: palette.text,
  },
  chart: { paddingHorizontal: spacing.screenH, gap: 8, marginBottom: 8 },
  chartRow: { flexDirection: 'row', alignItems: 'flex-end', gap: 6, height: 100 },
  barWrap: { flex: 1, alignItems: 'center', gap: 4 },
  bar: { width: '80%', backgroundColor: palette.accent, borderRadius: 4, minHeight: 8 },
  barLabel: { fontSize: 9, color: palette.textMuted },
});

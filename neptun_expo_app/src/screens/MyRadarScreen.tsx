import { useRouter } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { Alert, FlatList, StyleSheet, View } from 'react-native';
import { Card } from '../components/Card';
import { PrimaryButton } from '../components/PrimaryButton';
import { Text } from '../components/Text';
import { NeptunEmptyState } from '../design/components/NeptunEmptyState';
import { NeptunLoading } from '../design/components/NeptunLoading';
import { NeptunViewScreen } from '../design/components/NeptunScrollScreen';
import { FeatureGate } from '../features/monetization/components/FeatureGate';
import { useEntitlements } from '../features/monetization/hooks/useEntitlements';
import { monetizationApi } from '../features/monetization/services/monetizationApi';
import { monetizationAnalytics } from '../features/monetization/services/monetizationAnalytics';
import { useThemedStyles } from '../theme/useAppTheme';

export function MyRadarScreen() {
  const { features, plan, hasPlan } = useEntitlements();
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [summaryText, setSummaryText] = useState('');
  const [cards, setCards] = useState<
    Array<{
      location: { id: string; label: string; regionId: string };
      status: string;
      activeThreats: string[];
      lastUpdate: string | null;
    }>
  >([]);
  const [limit, setLimit] = useState(0);

  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      root: { flex: 1, backgroundColor: t.colors.background },
      list: { padding: 16, gap: 12, flexGrow: 1 },
      summary: { padding: 16, gap: 8 },
    }),
  );

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const radar = await monetizationApi.fetchMyRadar();
      setLimit(radar.limit);
      const sum = await monetizationApi.fetchMyRadarSummary();
      setSummaryText(sum.summaryText);
      setCards(sum.locations);
    } catch {
      Alert.alert('Помилка', 'Не вдалося завантажити Мій радар');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    monetizationAnalytics.myRadarOpened(plan);
    if (hasPlan('pro')) void load();
    else setLoading(false);
  }, [hasPlan, load, plan]);

  const addLocation = async () => {
    if (cards.length >= limit) {
      monetizationAnalytics.myRadarLimitReached(plan);
      router.push('/premium');
      return;
    }
    try {
      await monetizationApi.addMyRadarLocation({
        label: 'Дім',
        regionId: '16',
        type: 'home',
      });
      monetizationAnalytics.myRadarLocationAdded(plan);
      await load();
    } catch (e: unknown) {
      const msg = e && typeof e === 'object' && 'message' in e ? String((e as { message: string }).message) : '';
      if (msg.includes('limit')) {
        monetizationAnalytics.myRadarLimitReached(plan);
        router.push('/premium');
      } else {
        Alert.alert('Помилка', 'Додайте регіон у налаштуваннях або спробуйте пізніше');
      }
    }
  };

  if (!hasPlan('pro')) {
    return (
      <FeatureGate minPlan="pro" featureName="Мій радар">
        <View />
      </FeatureGate>
    );
  }

  if (loading) return <NeptunLoading label="Завантаження…" />;

  return (
    <NeptunViewScreen style={styles.root}>
      <View style={styles.summary}>
        <Text title>Мій радар</Text>
        <Text muted>{summaryText}</Text>
        <Text muted>
          Локацій: {cards.length} / {limit}
        </Text>
      </View>
      <FlatList
        data={cards}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          <NeptunEmptyState
            icon="location-outline"
            title="Немає локацій"
            subtitle="Додайте область або місто — без точної геолокації"
          />
        }
        renderItem={({ item }) => (
          <Card>
            <Text subtitle>{item.location.label}</Text>
            <Text muted>Регіон {item.location.regionId}</Text>
            <Text>{item.status === 'alert' ? '⚠️ Тривога' : '✓ Спокійно'}</Text>
            {item.activeThreats.length > 0 ? (
              <Text muted>Типи: {item.activeThreats.join(', ')}</Text>
            ) : null}
          </Card>
        )}
      />
      <View style={{ padding: 16 }}>
        <PrimaryButton onPress={() => void addLocation()}>Додати локацію</PrimaryButton>
      </View>
    </NeptunViewScreen>
  );
}

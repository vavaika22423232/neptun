import { useRouter } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { Alert, ScrollView, StyleSheet, Switch, TextInput, View } from 'react-native';
import { PrimaryButton } from '../components/PrimaryButton';
import { Text } from '../components/Text';
import { NeptunLoading } from '../design/components/NeptunLoading';
import { NeptunViewScreen } from '../design/components/NeptunScrollScreen';
import { FeatureGate } from '../features/monetization/components/FeatureGate';
import { useEntitlements } from '../features/monetization/hooks/useEntitlements';
import {
  monetizationApi,
  type NotificationRule,
} from '../features/monetization/services/monetizationApi';
import { monetizationAnalytics } from '../features/monetization/services/monetizationAnalytics';
import { useThemedStyles } from '../theme/useAppTheme';

const THREAT_TYPES = [
  { id: 'air_alarm', label: 'Повітряна тривога' },
  { id: 'shahed', label: 'Шахед / БПЛА' },
  { id: 'missile', label: 'Ракета' },
  { id: 'ballistic', label: 'Балістика' },
  { id: 'aviation', label: 'Авіація' },
  { id: 'explosion', label: 'Обстріл' },
  { id: 'all_clear', label: 'Відбій' },
] as const;

export function SmartNotificationsScreen() {
  const { features, plan, hasPlan } = useEntitlements();
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [rules, setRules] = useState<NotificationRule[]>([]);
  const [limit, setLimit] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [regionInput, setRegionInput] = useState('');
  const [quietStart, setQuietStart] = useState('23:00');
  const [quietEnd, setQuietEnd] = useState('07:00');
  const [quietOn, setQuietOn] = useState(false);
  const [criticalOverride, setCriticalOverride] = useState(true);
  const [dedupeMin, setDedupeMin] = useState('5');
  const [selectedThreats, setSelectedThreats] = useState<string[]>(['air_alarm', 'shahed']);

  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      root: { flex: 1, backgroundColor: t.colors.background },
      scroll: { padding: 20, gap: 16 },
      card: {
        padding: 16,
        borderRadius: 12,
        backgroundColor: t.colors.surface,
        borderWidth: 1,
        borderColor: t.colors.border,
        gap: 10,
      },
      input: {
        borderWidth: 1,
        borderColor: t.colors.border,
        borderRadius: 10,
        padding: 12,
        color: t.colors.textPrimary,
        fontSize: 15,
      },
      chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
      chip: {
        paddingHorizontal: 12,
        paddingVertical: 8,
        borderRadius: 999,
        borderWidth: 1,
        borderColor: t.colors.border,
      },
      chipOn: { backgroundColor: t.colors.primaryMuted, borderColor: t.colors.primary },
      lock: { opacity: 0.5 },
    }),
  );

  const hydrateForm = useCallback((list: NotificationRule[]) => {
    const r = list[0];
    if (!r) return;
    setRegionInput(r.regionIds.join(', '));
    setQuietOn(r.quietModeEnabled);
    setQuietStart(r.quietModeStart ?? '23:00');
    setQuietEnd(r.quietModeEnd ?? '07:00');
    setCriticalOverride(r.criticalOverrideEnabled);
    setDedupeMin(String(r.dedupeWindowMinutes));
    setSelectedThreats(r.threatTypes.length ? r.threatTypes : ['air_alarm']);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await monetizationApi.fetchNotificationRules();
      setRules(data.rules);
      setLimit(data.limit);
      hydrateForm(data.rules);
    } catch {
      setError('Не вдалося завантажити правила');
    } finally {
      setLoading(false);
    }
  }, [hydrateForm]);

  useEffect(() => {
    monetizationAnalytics.smartNotificationsOpened(plan);
    if (features.smartNotifications) void load();
    else setLoading(false);
  }, [features.smartNotifications, load, plan]);

  const saveRule = async () => {
    const regionIds = regionInput
      .split(/[,;\s]+/)
      .map((s) => s.trim())
      .filter(Boolean);
    const payload = {
      regionIds,
      threatTypes: hasPlan('pro_plus') ? selectedThreats : selectedThreats.slice(0, 2),
      quietModeEnabled: features.quietMode ? quietOn : false,
      quietModeStart: quietStart,
      quietModeEnd: quietEnd,
      criticalOverrideEnabled: criticalOverride,
      dedupeWindowMinutes: Number(dedupeMin) || 5,
      enabled: true,
    };

    try {
      if (rules[0]) {
        await monetizationApi.updateNotificationRule(rules[0].id, payload);
        monetizationAnalytics.notificationRuleUpdated(plan);
      } else {
        await monetizationApi.createNotificationRule(payload);
        monetizationAnalytics.notificationRuleCreated(plan);
      }
      if (quietOn) monetizationAnalytics.quietModeEnabled(true);
      await load();
      Alert.alert('Збережено', 'Правила синхронізовано з сервером NEPTUN');
    } catch {
      Alert.alert('Помилка', 'Не вдалося зберегти');
    }
  };

  if (!features.smartNotifications) {
    return (
      <FeatureGate minPlan="pro" featureName="Розумні сповіщення">
        <View />
      </FeatureGate>
    );
  }

  if (loading) return <NeptunLoading label="Завантаження…" />;

  return (
    <NeptunViewScreen style={styles.root}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text title>Розумні сповіщення</Text>
        <Text muted>Області через ID (напр. 16, 9). Без точної геолокації.</Text>
        {error ? <Text muted>{error}</Text> : null}

        <View style={styles.card}>
          <Text subtitle>Мої регіони</Text>
          <TextInput
            style={styles.input}
            value={regionInput}
            onChangeText={setRegionInput}
            placeholder="ID областей через кому"
            placeholderTextColor="#888"
          />
          <Text muted>Ліміт: {limit} правил · регіонів у правилі</Text>
        </View>

        <View style={[styles.card, !features.threatTypeFilters && styles.lock]}>
          <Text subtitle>Типи загроз</Text>
          {!features.threatTypeFilters ? (
            <Text muted>Фільтри типів — з тарифу PRO+</Text>
          ) : null}
          <View style={styles.chipRow}>
            {THREAT_TYPES.map((t) => {
              const on = selectedThreats.includes(t.id);
              return (
                <View
                  key={t.id}
                  style={[styles.chip, on && styles.chipOn]}
                  onTouchEnd={() => {
                    if (!features.threatTypeFilters && !['air_alarm', 'shahed'].includes(t.id)) {
                      router.push('/premium');
                      return;
                    }
                    setSelectedThreats((prev) =>
                      on ? prev.filter((x) => x !== t.id) : [...prev, t.id],
                    );
                  }}
                >
                  <Text>{t.label}</Text>
                </View>
              );
            })}
          </View>
        </View>

        <View style={[styles.card, !features.quietMode && styles.lock]}>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
            <Text subtitle>Тихий режим</Text>
            <Switch value={quietOn} onValueChange={setQuietOn} disabled={!features.quietMode} />
          </View>
          {features.quietMode ? (
            <>
              <TextInput style={styles.input} value={quietStart} onChangeText={setQuietStart} placeholder="Початок HH:MM" />
              <TextInput style={styles.input} value={quietEnd} onChangeText={setQuietEnd} placeholder="Кінець HH:MM" />
            </>
          ) : null}
        </View>

        <View style={styles.card}>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
            <Text subtitle>Критичні виключення</Text>
            <Switch value={criticalOverride} onValueChange={setCriticalOverride} />
          </View>
          <Text muted>Балістика/ракети можуть пройти під час тихого режиму</Text>
        </View>

        <View style={styles.card}>
          <Text subtitle>Антиспам (хв)</Text>
          <TextInput style={styles.input} value={dedupeMin} onChangeText={setDedupeMin} keyboardType="number-pad" />
        </View>

        <View style={[styles.card, !features.customSounds && styles.lock]}>
          <Text subtitle>Звуки</Text>
          <Text muted>
            {features.customSounds
              ? 'Кастомні звуки — у системних налаштуваннях сповіщень ОС'
              : 'Доступно з PRO'}
          </Text>
        </View>

        <PrimaryButton onPress={() => void saveRule()}>Зберегти на сервері</PrimaryButton>
      </ScrollView>
    </NeptunViewScreen>
  );
}

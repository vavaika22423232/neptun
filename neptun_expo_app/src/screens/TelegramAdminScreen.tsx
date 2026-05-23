import * as Clipboard from 'expo-clipboard';
import { useCallback, useEffect, useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { PrimaryButton } from '../components/PrimaryButton';
import { Text } from '../components/Text';
import { NeptunLoading } from '../design/components/NeptunLoading';
import { NeptunViewScreen } from '../design/components/NeptunScrollScreen';
import { FeatureGate } from '../features/monetization/components/FeatureGate';
import { useEntitlements } from '../features/monetization/hooks/useEntitlements';
import { monetizationApi } from '../features/monetization/services/monetizationApi';
import { monetizationAnalytics } from '../features/monetization/services/monetizationAnalytics';
import { useThemedStyles } from '../theme/useAppTheme';

export function TelegramAdminScreen() {
  const { features, plan, hasPlan } = useEntitlements();
  const [loading, setLoading] = useState(true);
  const [templates, setTemplates] = useState<{ id: string; label: string }[]>([]);
  const [selected, setSelected] = useState('active_threats');
  const [generated, setGenerated] = useState('');

  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      root: { flex: 1, backgroundColor: t.colors.background },
      scroll: { padding: 20, gap: 12 },
      tpl: {
        padding: 12,
        borderRadius: 10,
        borderWidth: 1,
        borderColor: t.colors.border,
        backgroundColor: t.colors.surface,
      },
      tplSelected: {
        backgroundColor: t.colors.surfaceElevated,
      },
      output: {
        padding: 14,
        borderRadius: 10,
        backgroundColor: t.colors.surface,
        borderWidth: 1,
        borderColor: t.colors.border,
      },
    }),
  );

  const loadTemplates = useCallback(async () => {
    setLoading(true);
    try {
      const data = await monetizationApi.fetchTelegramTemplates();
      setTemplates(data.templates);
    } catch {
      Alert.alert('Помилка', 'Не вдалося завантажити шаблони');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    monetizationAnalytics.telegramAdminOpened(plan);
    if (features.telegramAdminMode) void loadTemplates();
    else setLoading(false);
  }, [features.telegramAdminMode, loadTemplates, plan]);

  const generate = async () => {
    try {
      const res = await monetizationApi.generateTelegramSummary({
        templateId: selected,
        regionName: 'Україна',
        language: 'uk',
      });
      setGenerated(res.text);
      monetizationAnalytics.telegramSummaryGenerated(selected);
    } catch {
      Alert.alert('Помилка', 'Генерація недоступна');
    }
  };

  const copy = async () => {
    if (!generated) return;
    await Clipboard.setStringAsync(generated);
    monetizationAnalytics.telegramSummaryCopied(selected);
    Alert.alert('Скопійовано', 'Текст у буфері обміну');
  };

  if (!hasPlan('max')) {
    return (
      <FeatureGate minPlan="max" featureName="Telegram Admin Mode">
        <View />
      </FeatureGate>
    );
  }

  if (loading) return <NeptunLoading label="Завантаження…" />;

  return (
    <NeptunViewScreen style={styles.root}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text title>Для адміністраторів каналів</Text>
        <Text muted>Генерація на сервері NEPTUN. Формулювання обережні.</Text>

        {templates.map((t) => (
          <Pressable
            key={t.id}
            style={[styles.tpl, selected === t.id && styles.tplSelected]}
            onPress={() => setSelected(t.id)}
          >
            <Text>{t.label}</Text>
          </Pressable>
        ))}

        <PrimaryButton onPress={() => void generate()}>Згенерувати</PrimaryButton>

        {generated ? (
          <View style={styles.output}>
            <Text>{generated}</Text>
          </View>
        ) : null}

        {generated ? (
          <>
            <PrimaryButton variant="secondary" onPress={() => void copy()}>
              Копіювати
            </PrimaryButton>
            <PrimaryButton
              variant="secondary"
              onPress={async () => {
                try {
                  const res = await monetizationApi.exportTelegramCard({
                    templateId: selected,
                    regionName: 'Україна',
                  });
                  setGenerated(res.text);
                  await Clipboard.setStringAsync(res.text);
                  Alert.alert('Експорт', `Збережено як ${res.filename}`);
                } catch {
                  Alert.alert('Помилка', 'Експорт недоступний');
                }
              }}
            >
              Експорт (MAX)
            </PrimaryButton>
          </>
        ) : null}
      </ScrollView>
    </NeptunViewScreen>
  );
}

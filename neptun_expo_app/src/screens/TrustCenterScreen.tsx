import { Ionicons } from '@expo/vector-icons';
import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, RefreshControl, ScrollView, StyleSheet, View } from 'react-native';
import { Card } from '../components/Card';
import { Text } from '../components/Text';
import { endpoints } from '../config/api';
import { apiRequest } from '../services/apiClient';
import { colors } from '../theme/colors';
import { fonts } from '../theme/fonts';
import { spacing } from '../theme/colors';
import { useLegacyScreenStyles } from '../theme/useLegacyScreenStyles';

type StatusMap = Record<'api' | 'sse' | 'worker' | 'fcm', string>;

export function TrustCenterScreen() {
  const styles = useScreenStyles();
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<StatusMap | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiRequest<Record<string, unknown>>(endpoints.health, { timeoutMs: 5000 });
      setStatus({
        api: 'operational',
        sse: data.sse === true ? 'operational' : 'degraded',
        worker: data.worker === true ? 'operational' : 'degraded',
        fcm: 'operational',
      });
    } catch {
      setStatus({
        api: 'degraded',
        sse: 'unknown',
        worker: 'unknown',
        fcm: 'unknown',
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <ScrollView
      style={styles.root}
      contentContainerStyle={styles.pad}
      refreshControl={<RefreshControl refreshing={loading} onRefresh={() => void load()} tintColor={colors.accent} />}
    >
      <Card>
        <View style={styles.cardHead}>
          <Ionicons name="server" size={20} color={colors.accent} />
          <Text style={styles.cardTitle}>Статус серверів</Text>
          {!loading && status?.api === 'operational' ? (
            <View style={styles.badgeOk}>
              <Text style={styles.badgeOkText}>Працює</Text>
            </View>
          ) : null}
        </View>
        {loading ? (
          <ActivityIndicator style={{ marginVertical: 24 }} color={colors.accent} />
        ) : (
          <View style={styles.statusList}>
            <StatusRow label="API" status={status?.api ?? 'unknown'} />
            <StatusRow label="SSE (реал-тайм)" status={status?.sse ?? 'unknown'} />
            <StatusRow label="Worker (обробка загроз)" status={status?.worker ?? 'unknown'} />
            <StatusRow label="FCM (push-повідомлення)" status={status?.fcm ?? 'unknown'} />
          </View>
        )}
      </Card>

      <Card style={styles.gap}>
        <View style={styles.cardHead}>
          <Ionicons name="layers" size={20} color={colors.accent} />
          <Text style={styles.cardTitle}>Джерела даних</Text>
        </View>
        <Text muted style={styles.body}>
          Дані про загрози збираються з 12+ верифікованих Telegram-каналів у реальному часі. Кожне повідомлення
          обробляється AI для витягування типу загрози, геолокації та траєкторії.
        </Text>
      </Card>

      <Card style={styles.gap}>
        <View style={styles.cardHead}>
          <Ionicons name="git-network" size={20} color={colors.accent} />
          <Text style={styles.cardTitle}>Як це працює</Text>
        </View>
        <PipelineStep step="1" title="Моніторинг каналів" subtitle="Автоматичний збір даних з Telegram" />
        <PipelineStep step="2" title="AI-аналіз" subtitle="GPT-4o-mini витягує тип загрози та локацію" />
        <PipelineStep step="3" title="Геокодування" subtitle="Визначення точних координат (4 рівня)" />
        <PipelineStep step="4" title="Push-повідомлення" subtitle="Миттєва доставка через FCM" isLast />
      </Card>
    </ScrollView>
  );
}

function StatusRow({ label, status }: { label: string; status: string }) {
  const styles = useScreenStyles();
  const ok = status === 'operational';
  return (
    <View style={styles.statusRow}>
      <View style={[styles.dot, { backgroundColor: ok ? colors.success : colors.danger }]} />
      <Text style={styles.statusLabel}>{label}</Text>
    </View>
  );
}

function PipelineStep({
  step,
  title,
  subtitle,
  isLast,
}: {
  step: string;
  title: string;
  subtitle: string;
  isLast?: boolean;
}) {
  const styles = useScreenStyles();
return (
    <View style={styles.pipeRow}>
      <View style={styles.pipeCol}>
        <View style={styles.stepCircle}>
          <Text style={styles.stepNum}>{step}</Text>
        </View>
        {!isLast ? <View style={styles.pipeLine} /> : null}
      </View>
      <View style={{ flex: 1, paddingBottom: isLast ? 0 : 8 }}>
        <Text style={styles.pipeTitle}>{title}</Text>
        <Text muted style={styles.pipeSub}>
          {subtitle}
        </Text>
      </View>
    </View>
  );
}


function useScreenStyles() {
  return useLegacyScreenStyles((c) => ({
  root: { flex: 1, backgroundColor: c.bg },
  pad: { padding: spacing.lg, gap: 0 },
  gap: { marginTop: spacing.lg },
  cardHead: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
  },
  cardTitle: {
    flex: 1,
    fontFamily: fonts.semiBold,
    fontSize: 15,
  },
  badgeOk: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
    backgroundColor: c.success + '22',
  },
  badgeOkText: {
    fontFamily: fonts.bold,
    fontSize: 11,
    color: c.success,
  },
  statusList: { gap: 12 },
  statusRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  dot: { width: 8, height: 8, borderRadius: 4 },
  statusLabel: { fontSize: 13, color: c.textSoft },
  body: { fontSize: 13, lineHeight: 20 },
  pipeRow: { flexDirection: 'row', gap: 12, marginTop: 8 },
  pipeCol: { alignItems: 'center' },
  stepCircle: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: c.accent + '22',
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepNum: {
    fontFamily: fonts.bold,
    fontSize: 12,
    color: c.accent,
  },
  pipeLine: {
    width: 1,
    height: 24,
    backgroundColor: c.border,
    marginTop: 4,
  },
  pipeTitle: {
    fontFamily: fonts.semiBold,
    fontSize: 14,
  },
  pipeSub: { fontSize: 12, marginTop: 2 },
}));
}

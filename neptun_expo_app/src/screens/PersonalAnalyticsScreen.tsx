import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { useCallback, useEffect, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, View } from 'react-native';
import { Card } from '../components/Card';
import { ProFeatureGate } from '../components/ProFeatureGate';
import { Text } from '../components/Text';
import { ProFeature } from '../core/pro/proGate';
import { getAnalyticsRegionLabel } from '../services/analyticsRegionLabel';
import { getStatsTotals } from '../services/alarmStatsService';
import { radii, spacing } from '../theme/colors';
import { fonts } from '../theme/fonts';
import { useLegacyColors } from '../theme/useAppTheme';
import { useLegacyScreenStyles } from '../theme/useLegacyScreenStyles';

type Totals = { alarms: number; minutes: number };

export function PersonalAnalyticsScreen() {
  const styles = useScreenStyles();
  const c = useLegacyColors();
  const [totals, setTotals] = useState<Totals>({ alarms: 0, minutes: 0 });
  const [region, setRegion] = useState('');

  const load = useCallback(async () => {
    const [t, r] = await Promise.all([getStatsTotals(), Promise.resolve(getAnalyticsRegionLabel())]);
    setTotals(t);
    setRegion(r);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const safetyScore =
    totals.alarms > 0 ? Math.round((1 - Math.min(totals.alarms / 100, 1)) * 100) : null;

  return (
    <ProFeatureGate feature={ProFeature.PersonalAnalytics}>
      <ScrollView
        style={styles.root}
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl refreshing={false} onRefresh={() => void load()} tintColor={c.accent} />
        }
      >
        {totals.alarms === 0 && totals.minutes === 0 ? (
          <Card style={styles.hintCard}>
            <View style={styles.hintRow}>
              <View style={styles.hintIcon}>
                <Ionicons name="information-circle-outline" size={22} color={c.accent} />
              </View>
              <Text style={styles.hintText}>
                {region === 'Невизначено'
                  ? 'Оберіть регіони у You → Live: ваші регіони. Статистика оновлюватиметься під час тривог у ваших регіонах.'
                  : 'Регіон обрано. Статистика почне збиратися при наступній тривозі у ваших регіонах.'}
              </Text>
            </View>
          </Card>
        ) : null}

        <Card style={styles.regionCard}>
          <View style={styles.hintRow}>
            <View style={styles.hintIcon}>
              <Ionicons name="location" size={22} color={c.accent} />
            </View>
            <View>
              <Text muted style={styles.regionLabel}>
                Ваш регіон
              </Text>
              <Text style={styles.regionValue}>{region}</Text>
            </View>
          </View>
        </Card>

        <View style={styles.statRow}>
          <StatCard
            icon="notifications"
            label="Тривог"
            value={String(totals.alarms)}
            accent={c.danger}
          />
          <StatCard icon="timer-outline" label="Хвилин" value={String(totals.minutes)} accent={c.accent} />
        </View>

        <Card style={styles.sectionCard}>
          <View style={styles.sectionTitleRow}>
            <Ionicons name="timer-outline" size={20} color={c.accent} />
            <Text style={styles.sectionTitle}>Час під тривогами</Text>
          </View>
          <StatRow label="Сьогодні" value={totals.minutes > 0 ? `${totals.minutes % 60} хв` : '—'} />
          <StatRow label="Цього тижня" value={totals.minutes > 0 ? `${Math.floor(totals.minutes / 60)} г` : '—'} />
          <StatRow label="Цього місяця" value={totals.minutes > 0 ? `${Math.floor(totals.minutes / 60)} г` : '—'} />
        </Card>

        <Card style={styles.sectionCard}>
          <View style={styles.sectionTitleRow}>
            <Ionicons name="shield-checkmark-outline" size={20} color={c.accent2} />
            <Text style={styles.sectionTitle}>Рейтинг безпеки</Text>
          </View>
          <Text style={styles.safetyNumber}>{safetyScore != null ? String(safetyScore) : '—'}</Text>
          <Text muted style={styles.safetySub}>
            {safetyScore != null ? 'Ваш рейтинг безпеки' : 'Використовуйте додаток для збору статистики'}
          </Text>
        </Card>
      </ScrollView>
    </ProFeatureGate>
  );
}

function StatCard({
  icon,
  label,
  value,
  accent,
}: {
  icon: ComponentProps<typeof Ionicons>['name'];
  label: string;
  value: string;
  accent: string;
}) {
  const styles = useScreenStyles();
return (
    <Card style={styles.statCard}>
      <Ionicons name={icon} size={20} color={accent} />
      <Text style={styles.statValue}>{value}</Text>
      <Text muted style={styles.statLabel}>
        {label}
      </Text>
    </Card>
  );
}

function StatRow({ label, value }: { label: string; value: string }) {
  const styles = useScreenStyles();
return (
    <View style={styles.statRowLine}>
      <Text muted style={styles.statRowLabel}>
        {label}
      </Text>
      <Text style={styles.statRowValue}>{value}</Text>
    </View>
  );
}


function useScreenStyles() {
  return useLegacyScreenStyles((c) => ({
  root: { flex: 1, backgroundColor: c.bg },
  content: { padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xxl },
  hintCard: { padding: spacing.md },
  hintRow: { flexDirection: 'row', alignItems: 'flex-start', gap: spacing.md },
  hintIcon: {
    width: 44,
    height: 44,
    borderRadius: radii.md,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(76,201,240,0.12)',
  },
  hintText: { flex: 1, fontSize: 14, lineHeight: 20, color: c.textSoft },
  regionCard: { padding: spacing.md },
  regionLabel: { fontSize: 12 },
  regionValue: { marginTop: 2, fontFamily: fonts.semiBold, fontSize: 16, color: c.text },
  statRow: { flexDirection: 'row', gap: spacing.md },
  statCard: { flex: 1, gap: spacing.sm, padding: spacing.md },
  statValue: { fontFamily: fonts.bold, fontSize: 28, color: c.text },
  statLabel: { fontSize: 12 },
  sectionCard: { padding: spacing.md, gap: spacing.sm },
  sectionTitleRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, marginBottom: spacing.sm },
  sectionTitle: { fontFamily: fonts.semiBold, fontSize: 15, color: c.text },
  statRowLine: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 6,
  },
  statRowLabel: { fontSize: 13 },
  statRowValue: { fontFamily: fonts.semiBold, fontSize: 14, color: c.text },
  safetyNumber: {
    alignSelf: 'center',
    fontFamily: fonts.bold,
    fontSize: 48,
    color: c.accent2,
    marginTop: spacing.sm,
  },
  safetySub: { textAlign: 'center', fontSize: 12, marginTop: 4 },
}));
}

import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useRouter } from 'expo-router';
import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  StyleSheet,
  View,
  useWindowDimensions,
} from 'react-native';
import { Text } from '../components/Text';
import { randomSafetyTip } from '../features/briefing/constants/safetyTips';
import type { BriefingData } from '../features/briefing/domain/briefingData';
import {
  briefingHasMultipleRegions,
  briefingTotalThreats,
} from '../features/briefing/domain/briefingData';
import { briefingService } from '../features/briefing/services/briefingService';
import { colors, radii, spacing } from '../theme/colors';
import { fonts } from '../theme/fonts';
import { useLegacyScreenStyles } from '../theme/useLegacyScreenStyles';

const AUTO_MS = 5000;

type PageItem = { key: string; render: (data: BriefingData, tip: string) => ReactNode };

function GradientCard({
  colors: gradientColors,
  children,
  width,
}: {
  colors: [string, string];
  children: ReactNode;
  width: number;
}) {
  const styles = useScreenStyles();
return (
    <View style={[styles.page, { width }]}>
      <LinearGradient colors={gradientColors} style={styles.gradient}>
        {children}
      </LinearGradient>
    </View>
  );
}

function CounterLine({ value, suffix }: { value: number; suffix: string }) {
  const styles = useScreenStyles();
return (
    <Text style={styles.counter}>
      {value}
      {suffix}
    </Text>
  );
}

function ThreatItem({ label, count }: { label: string; count: number }) {
  const styles = useScreenStyles();
return (
    <View style={styles.threatItem}>
      <Text style={styles.threatCount}>{count}</Text>
      <Text style={styles.threatLabel}>{label}</Text>
    </View>
  );
}

/** Flutter `BriefingPage` — 5-card story, 5s auto-advance. */
export function BriefingScreen() {
  const styles = useScreenStyles();
  const router = useRouter();
  const { width } = useWindowDimensions();
  const listRef = useRef<FlatList<PageItem>>(null);
  const [data, setData] = useState<BriefingData | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [tip] = useState(() => randomSafetyTip());

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const next = await briefingService.fetchBriefing();
      setData(next);
      setPage(0);
      listRef.current?.scrollToOffset({ offset: 0, animated: false });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (loading || !data) return;
    const id = setInterval(() => {
      setPage((p) => {
        const next = p < 4 ? p + 1 : p;
        if (next !== p) {
          listRef.current?.scrollToIndex({ index: next, animated: true });
        }
        return next;
      });
    }, AUTO_MS);
    return () => clearInterval(id);
  }, [loading, data]);

  const pages: PageItem[] = data
    ? [
        {
          key: 'greeting',
          render: (d) => (
            <GradientCard width={width} colors={['#1A237E', '#0D47A1']}>
              <Text style={styles.cardTitle}>{d.isMorning ? 'Доброго ранку' : 'Доброго вечора'}</Text>
              <CounterLine
                value={d.totalAlarmsToday}
                suffix={
                  d.totalAlarmsToday === 0 ? ' — все спокійно' : ' тривог сьогодні'
                }
              />
            </GradientCard>
          ),
        },
        {
          key: 'alarms',
          render: (d) => (
            <GradientCard width={width} colors={['#1B5E20', '#2E7D32']}>
              <Text style={styles.cardTitle}>Live-мапа тривог</Text>
              {d.alarmRegions.length === 0 ? (
                <Text style={styles.cardSub}>Жодного регіону з тривогою</Text>
              ) : (
                <View style={styles.chips}>
                  {d.alarmRegions.slice(0, 8).map((r) => (
                    <View key={r} style={styles.chip}>
                      <Text style={styles.chipText}>{r.replace(/\s+область$/i, '')}</Text>
                    </View>
                  ))}
                </View>
              )}
            </GradientCard>
          ),
        },
        {
          key: 'threats',
          render: (d) => (
            <GradientCard width={width} colors={['#B71C1C', '#C62828']}>
              <Text style={styles.cardTitle}>Загрози сьогодні</Text>
              <View style={styles.threatRow}>
                <ThreatItem label="Шахеди" count={d.drones} />
                <ThreatItem label="Ракети" count={d.missiles} />
                <ThreatItem label="КАБ" count={d.kab} />
                <ThreatItem label="Балістика" count={d.ballistic} />
              </View>
              {briefingTotalThreats(d) === 0 ? (
                <Text style={styles.cardSub}>Загроз не зафіксовано</Text>
              ) : null}
            </GradientCard>
          ),
        },
        {
          key: 'region',
          render: (d) => (
            <GradientCard width={width} colors={['#4A148C', '#6A1B9A']}>
              <Text style={styles.cardTitle}>
                {briefingHasMultipleRegions(d) ? 'Ваші регіони' : 'Ваш регіон'}
              </Text>
              {d.userRegionName || d.userRegionsTotal > 0 ? (
                <>
                  {!briefingHasMultipleRegions(d) && d.userRegionName ? (
                    <Text style={styles.cardSub}>{d.userRegionName}</Text>
                  ) : briefingHasMultipleRegions(d) ? (
                    <Text style={styles.cardSub}>{d.userRegionsTotal} обраних</Text>
                  ) : null}
                  <CounterLine
                    value={d.userRegionAlarmCount}
                    suffix={briefingHasMultipleRegions(d) ? ' з тривогою' : ' тривог'}
                  />
                </>
              ) : (
                <Text style={styles.cardSub}>Оберіть регіон у налаштуваннях</Text>
              )}
            </GradientCard>
          ),
        },
        {
          key: 'tip',
          render: (_d, safetyTip) => (
            <GradientCard width={width} colors={['#E65100', '#EF6C00']}>
              <Ionicons name="bulb" size={48} color="rgba(255,255,255,0.9)" />
              <Text style={[styles.cardTitle, { marginTop: 16 }]}>Порада дня</Text>
              <Text style={styles.tipBody}>{safetyTip}</Text>
            </GradientCard>
          ),
        },
      ]
    : [];

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.accent} size="large" />
        <Text muted style={styles.loadingText}>
          Завантаження брифінгу...
        </Text>
      </View>
    );
  }

  if (!data) {
    return (
      <View style={styles.center}>
        <Text>Не вдалося завантажити брифінг</Text>
        <Pressable onPress={() => void load()} style={styles.textBtn}>
          <Text style={styles.textBtnLabel}>Спробувати знову</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <View style={styles.root}>
      {data.fromCache ? (
        <Pressable onPress={() => void load()} style={styles.offlineBar}>
          <Text style={styles.offlineText}>Офлайн. Показуємо останні дані — тап для оновлення</Text>
          <Ionicons name="refresh" size={16} color={colors.warning} />
        </Pressable>
      ) : null}

      <View style={styles.dots}>
        {[0, 1, 2, 3, 4].map((i) => (
          <View key={i} style={[styles.dot, i <= page && styles.dotActive, i === page && styles.dotWide]} />
        ))}
      </View>

      <FlatList
        ref={listRef}
        data={pages}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        keyExtractor={(item) => item.key}
        onMomentumScrollEnd={(e) => {
          const i = Math.round(e.nativeEvent.contentOffset.x / width);
          setPage(i);
        }}
        getItemLayout={(_, index) => ({ length: width, offset: width * index, index })}
        renderItem={({ item }) => <View>{item.render(data, tip)}</View>}
      />

      <View style={styles.footer}>
        <Pressable onPress={() => void load()} style={styles.textBtn}>
          <Ionicons name="refresh" size={18} color={colors.textSoft} />
          <Text style={styles.textBtnLabel}>Оновити</Text>
        </Pressable>
        <Pressable onPress={() => router.back()} style={styles.textBtn}>
          <Text style={styles.textBtnLabel}>Закрити</Text>
        </Pressable>
      </View>
    </View>
  );
}


function useScreenStyles() {
  return useLegacyScreenStyles((c) => ({
  root: { flex: 1, backgroundColor: c.bg },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 12 },
  loadingText: { marginTop: 8 },
  offlineBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 10,
    backgroundColor: 'rgba(245,158,11,0.12)',
  },
  offlineText: { fontSize: 12, color: c.warning },
  dots: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 12,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: 'rgba(255,255,255,0.25)',
  },
  dotActive: { backgroundColor: c.accent },
  dotWide: { width: 24 },
  page: { paddingHorizontal: 12 },
  gradient: {
    flex: 1,
    marginVertical: 8,
    borderRadius: radii.xl,
    padding: 24,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 360,
  },
  cardTitle: {
    fontFamily: fonts.bold,
    fontSize: 28,
    color: '#fff',
    textAlign: 'center',
  },
  cardSub: {
    marginTop: 12,
    fontSize: 17,
    color: 'rgba(255,255,255,0.9)',
    textAlign: 'center',
  },
  counter: {
    marginTop: 20,
    fontFamily: fonts.bold,
    fontSize: 22,
    color: '#fff',
    textAlign: 'center',
  },
  chips: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 8,
    marginTop: 16,
  },
  chip: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    backgroundColor: 'rgba(255,255,255,0.2)',
  },
  chipText: { color: '#fff', fontSize: 14 },
  threatRow: {
    flexDirection: 'row',
    justifyContent: 'space-evenly',
    width: '100%',
    marginTop: 20,
  },
  threatItem: { alignItems: 'center', minWidth: 64 },
  threatCount: { fontFamily: fonts.bold, fontSize: 26, color: '#fff' },
  threatLabel: { fontSize: 12, color: 'rgba(255,255,255,0.75)', marginTop: 4 },
  tipBody: {
    marginTop: 20,
    fontSize: 18,
    lineHeight: 28,
    color: 'rgba(255,255,255,0.95)',
    textAlign: 'center',
    paddingHorizontal: 16,
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 24,
    padding: spacing.lg,
  },
  textBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, padding: 8 },
  textBtnLabel: { fontFamily: fonts.semiBold, fontSize: 15, color: c.textSoft },
}));
}

import { Ionicons } from '@expo/vector-icons';
import { useCallback, useEffect, useState } from 'react';
import { ScrollView, StyleSheet, Switch, TextInput, View } from 'react-native';
import { Card } from '../components/Card';
import { Text } from '../components/Text';
import {
  getSleepModeCached,
  hydrateSleepMode,
  saveSleepModeSettings,
  type SleepModeSettings,
} from '../services/sleepModeStore';
import { colors } from '../theme/colors';
import { fonts } from '../theme/fonts';

function clampInt(text: string, max: number): number {
  const n = Number(text.replace(/[^\d]/g, ''));
  if (!Number.isFinite(n)) return 0;
  return Math.min(max, Math.max(0, n));
}

function fmtHm(h: number, m: number): string {
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

export function SleepModeScreen() {
  const [s, setS] = useState<SleepModeSettings>(getSleepModeCached());
  const [startH, setStartH] = useState(String(s.startHour));
  const [startM, setStartM] = useState(String(s.startMinute));
  const [endH, setEndH] = useState(String(s.endHour));
  const [endM, setEndM] = useState(String(s.endMinute));

  const reload = useCallback(async () => {
    await hydrateSleepMode();
    const next = getSleepModeCached();
    setS(next);
    setStartH(String(next.startHour));
    setStartM(String(next.startMinute));
    setEndH(String(next.endHour));
    setEndM(String(next.endMinute));
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function applyTimes() {
    await saveSleepModeSettings({
      startHour: clampInt(startH, 23),
      startMinute: clampInt(startM, 59),
      endHour: clampInt(endH, 23),
      endMinute: clampInt(endM, 59),
    });
    await reload();
  }

  return (
    <ScrollView style={styles.root} contentContainerStyle={styles.pad}>
      <Text muted style={styles.intro}>
        У години сну частину push можна приглушити. Фільтрація не замінює офіційні канали МІП та має
        узгоджуватися з вашими очікуваннями безпеки.
      </Text>

      <Card style={styles.row}>
        <View style={{ flex: 1 }}>
          <Text style={styles.title}>Увімкнути режим сну</Text>
          <Text muted style={styles.hint}>
            Застосовується до сповіщень Expo у передньому плані (див. обробник у застосунку).
          </Text>
        </View>
        <Switch
          value={s.enabled}
          onValueChange={(v) => {
            setS((p) => ({ ...p, enabled: v }));
            void saveSleepModeSettings({ enabled: v }).then(reload);
          }}
          trackColor={{ false: colors.border, true: colors.premium + '88' }}
          thumbColor={s.enabled ? colors.premium : colors.muted}
        />
      </Card>

      <Card>
        <Text style={styles.section}>Інтервал тиші</Text>
        <Text muted style={styles.rangeHint}>
          Зараз: {fmtHm(s.startHour, s.startMinute)} → {fmtHm(s.endHour, s.endMinute)} (типовий нічний
          відрізок перетинає північ)
        </Text>
        <View style={styles.timeGrid}>
          <View style={styles.timeCol}>
            <Text muted style={styles.timeLbl}>
              Початок (год / хв)
            </Text>
            <View style={styles.timeInputs}>
              <TextInput
                value={startH}
                onChangeText={setStartH}
                keyboardType="number-pad"
                style={styles.input}
                maxLength={2}
              />
              <TextInput
                value={startM}
                onChangeText={setStartM}
                keyboardType="number-pad"
                style={styles.input}
                maxLength={2}
              />
            </View>
          </View>
          <View style={styles.timeCol}>
            <Text muted style={styles.timeLbl}>
              Кінець (год / хв)
            </Text>
            <View style={styles.timeInputs}>
              <TextInput
                value={endH}
                onChangeText={setEndH}
                keyboardType="number-pad"
                style={styles.input}
                maxLength={2}
              />
              <TextInput
                value={endM}
                onChangeText={setEndM}
                keyboardType="number-pad"
                style={styles.input}
                maxLength={2}
              />
            </View>
          </View>
        </View>
        <Text
          style={styles.apply}
          onPress={() => void applyTimes()}
        >
          Застосувати час
        </Text>
      </Card>

      <Card>
        <Text style={styles.section}>Завжди пропускати вночі</Text>
        <SleepToggleRow
          label="Ракетна небезпека / КАБ"
          value={s.allowRockets}
          topBorder={false}
          onChange={(v) => {
            setS((p) => ({ ...p, allowRockets: v }));
            void saveSleepModeSettings({ allowRockets: v }).then(reload);
          }}
        />
        <SleepToggleRow
          label="БПЛА / шахеди"
          value={s.allowDrones}
          onChange={(v) => {
            setS((p) => ({ ...p, allowDrones: v }));
            void saveSleepModeSettings({ allowDrones: v }).then(reload);
          }}
        />
        <SleepToggleRow
          label="Відбій тривоги"
          value={s.allowAllClear}
          onChange={(v) => {
            setS((p) => ({ ...p, allowAllClear: v }));
            void saveSleepModeSettings({ allowAllClear: v }).then(reload);
          }}
        />
      </Card>

      <View style={styles.note}>
        <Ionicons name="information-circle-outline" size={18} color={colors.muted} />
        <Text muted style={styles.noteTxt}>
          Логіка збігається з Flutter `SleepModeService`: якщо тип не впізнано як ракетний — і дозволені
          «ракети», таке повідомлення все одно показується.
        </Text>
      </View>
    </ScrollView>
  );
}

function SleepToggleRow({
  label,
  value,
  onChange,
  topBorder = true,
}: {
  label: string;
  value: boolean;
  onChange: (v: boolean) => void;
  topBorder?: boolean;
}) {
  return (
    <View style={[styles.toggleRow, !topBorder && styles.toggleRowFirst]}>
      <Text style={styles.toggleLbl}>{label}</Text>
      <Switch
        value={value}
        onValueChange={onChange}
        trackColor={{ false: colors.border, true: colors.success + '66' }}
        thumbColor={value ? colors.success : colors.muted}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  pad: { padding: 16, gap: 14, paddingBottom: 40 },
  intro: { fontSize: 13, lineHeight: 19, marginBottom: 4 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  title: { fontFamily: fonts.semiBold, fontSize: 16 },
  hint: { fontSize: 12, marginTop: 4, lineHeight: 17 },
  section: { fontFamily: fonts.bold, fontSize: 15, marginBottom: 6 },
  rangeHint: { fontSize: 12, lineHeight: 17, marginBottom: 12 },
  timeGrid: { flexDirection: 'row', gap: 12 },
  timeCol: { flex: 1 },
  timeLbl: { fontSize: 12, marginBottom: 6 },
  timeInputs: { flexDirection: 'row', gap: 8 },
  input: {
    flex: 1,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    color: colors.text,
    fontFamily: fonts.semiBold,
    fontSize: 16,
    backgroundColor: colors.bg2,
  },
  apply: {
    marginTop: 14,
    fontFamily: fonts.semiBold,
    fontSize: 15,
    color: colors.accent,
    textAlign: 'right',
  },
  toggleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 10,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border,
  },
  toggleRowFirst: {
    borderTopWidth: 0,
  },
  toggleLbl: { flex: 1, fontFamily: fonts.medium, fontSize: 14, color: colors.text, paddingRight: 12 },
  note: { flexDirection: 'row', gap: 10, alignItems: 'flex-start', paddingHorizontal: 4 },
  noteTxt: { flex: 1, fontSize: 12, lineHeight: 17 },
});

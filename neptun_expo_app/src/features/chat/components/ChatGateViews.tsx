import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps, ReactNode } from 'react';
import { useState } from 'react';
import { Alert, Pressable, StyleSheet, TextInput, View } from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { PrimaryButton } from '../../../components/PrimaryButton';
import { Text } from '../../../components/Text';
import { NeptunSurface } from '../../../design/components/NeptunSurface';
import { fonts } from '../../../theme/fonts';
import { useAppTheme, useThemedStyles } from '../../../theme/useAppTheme';
import { ChatAmbientBackground } from './ChatAmbientBackground';

export const MIN_CHAT_AGE = 16;

export type GatePrefs = {
  ageConfirmed: boolean;
  birthYear?: number | null;
  rulesAgreed: boolean;
};

function useChatGateStyles() {
  return useThemedStyles((t) => {
    const ch = t.chat;
    return StyleSheet.create({
      root: { flex: 1, backgroundColor: ch.bg },
      center: { flex: 1, justifyContent: 'center', padding: 24 },
      card: { gap: 14, width: '100%', maxWidth: 400, alignSelf: 'center' },
      iconWrap: {
        width: 72,
        height: 72,
        borderRadius: 36,
        alignSelf: 'center',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: ch.accentMuted,
      },
      iconDanger: { backgroundColor: t.colors.dangerMuted },
      title: {
        textAlign: 'center',
        fontFamily: fonts.bold,
        fontSize: 24,
        lineHeight: 30,
        color: ch.text,
      },
      body: { textAlign: 'center', lineHeight: 21, color: ch.textSoft },
      input: {
        minHeight: 50,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: ch.borderStrong,
        borderRadius: 14,
        color: ch.text,
        fontFamily: fonts.medium,
        fontSize: 15,
        paddingHorizontal: 14,
        backgroundColor: ch.surfaceInput,
      },
      error: { color: ch.danger, textAlign: 'center' },
      stepper: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 12, marginVertical: 4 },
      stepBtn: {
        width: 44,
        height: 44,
        borderRadius: 14,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: t.colors.surfaceHighlight,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: ch.border,
      },
      yearText: { fontFamily: fonts.bold, fontSize: 17, color: ch.text },
      ruleRow: {
        borderRadius: 14,
        padding: 14,
        backgroundColor: t.colors.surfaceHighlight,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: ch.border,
      },
      ruleTitle: { fontFamily: fonts.bold, fontSize: 15, color: ch.text },
      ruleBody: { marginTop: 4, lineHeight: 18, color: ch.textSoft },
    });
  });
}

export function ChatGateShell({ children }: { children: ReactNode }) {
  const styles = useChatGateStyles();
  return (
    <View style={styles.root}>
      <ChatAmbientBackground />
      <View style={styles.center}>{children}</View>
    </View>
  );
}

export function ChatNicknameGate({
  nickInput,
  error,
  onChangeNick,
  onSubmit,
}: {
  nickInput: string;
  error: string | null;
  onChangeNick: (v: string) => void;
  onSubmit: () => void;
}) {
  const { theme } = useAppTheme();
  const ch = theme.chat;
  const styles = useChatGateStyles();

  return (
    <ChatGateShell>
      <GateCard icon="chatbubbles" iconColor={ch.accentSoft} title="Вхід у чат" delay={0} styles={styles} radiusGate={ch.radiusGate}>
        <Text style={styles.body}>Оберіть нікнейм. «Анонім» зарезервований системою.</Text>
        <TextInput
          value={nickInput}
          onChangeText={onChangeNick}
          placeholder="Нікнейм"
          placeholderTextColor={ch.textFaint}
          style={styles.input}
          autoCapitalize="none"
        />
        {error ? <Text style={styles.error}>{error}</Text> : null}
        <PrimaryButton onPress={onSubmit}>Увійти</PrimaryButton>
      </GateCard>
    </ChatGateShell>
  );
}

export function ChatAgeGate({
  gate,
  onCommit,
}: {
  gate: GatePrefs;
  onCommit: (next: GatePrefs) => void;
}) {
  const { theme } = useAppTheme();
  const ch = theme.chat;
  const styles = useChatGateStyles();
  const [year, setYear] = useState(gate.birthYear ?? new Date().getFullYear() - 18);
  const age = new Date().getFullYear() - year;

  return (
    <ChatGateShell>
      <GateCard icon="calendar-outline" iconColor={ch.accentSoft} title={`Чат лише для ${MIN_CHAT_AGE}+`} delay={0} styles={styles} radiusGate={ch.radiusGate}>
        <Text style={styles.body}>Оберіть рік народження для безпеки всіх учасників.</Text>
        <View style={styles.stepper}>
          <Pressable style={styles.stepBtn} onPress={() => setYear((y) => y - 1)}>
            <Ionicons name="remove" size={20} color={ch.text} />
          </Pressable>
          <Text style={styles.yearText}>
            {year} · {age} років
          </Text>
          <Pressable style={styles.stepBtn} onPress={() => setYear((y) => y + 1)}>
            <Ionicons name="add" size={20} color={ch.text} />
          </Pressable>
        </View>
        <PrimaryButton
          onPress={() => {
            if (age < MIN_CHAT_AGE) Alert.alert('Обмеження', `Чат доступний з ${MIN_CHAT_AGE} років.`);
            else void onCommit({ ...gate, ageConfirmed: true, birthYear: year });
          }}
        >
          Продовжити
        </PrimaryButton>
      </GateCard>
    </ChatGateShell>
  );
}

export function ChatRulesGate({ onAgree }: { onAgree: () => void }) {
  const { theme } = useAppTheme();
  const ch = theme.chat;
  const styles = useChatGateStyles();
  const rules = [
    ['Будьте ввічливими', 'Поважайте інших учасників чату та їх думку.'],
    ['Без спаму', 'Не надсилайте однакові повідомлення або беззмістовний текст.'],
    ['Без мату', 'Культурне спілкування без нецензурної лексики.'],
    ['Без реклами', 'Реклама сторонніх ресурсів або послуг заборонена.'],
  ] as const;

  return (
    <ChatGateShell>
      <GateCard icon="shield-checkmark-outline" iconColor={ch.accentSoft} title="Правила спільноти" delay={0} styles={styles} radiusGate={ch.radiusGate}>
        {rules.map(([title, body], i) => (
          <Animated.View key={title} entering={FadeInDown.delay(80 + i * 50).duration(280)} style={styles.ruleRow}>
            <Text style={styles.ruleTitle}>{title}</Text>
            <Text style={styles.ruleBody}>{body}</Text>
          </Animated.View>
        ))}
        <PrimaryButton onPress={onAgree}>Я згоден з правилами</PrimaryButton>
      </GateCard>
    </ChatGateShell>
  );
}

export function ChatBannedGate({ reason, onCheck }: { reason?: string | null; onCheck: () => void }) {
  const { theme } = useAppTheme();
  const ch = theme.chat;
  const styles = useChatGateStyles();

  return (
    <ChatGateShell>
      <GateCard icon="ban" iconColor={ch.danger} title="Доступ обмежено" tone="danger" delay={0} styles={styles} radiusGate={ch.radiusGate}>
        <Text style={styles.body}>
          {reason || 'Ваш акаунт було заблоковано за порушення правил спільноти.'}
        </Text>
        <PrimaryButton onPress={onCheck}>Перевірити ще раз</PrimaryButton>
      </GateCard>
    </ChatGateShell>
  );
}

function GateCard({
  icon,
  iconColor,
  title,
  tone,
  delay,
  children,
  styles,
  radiusGate,
}: {
  icon: ComponentProps<typeof Ionicons>['name'];
  iconColor: string;
  title: string;
  tone?: 'danger';
  delay: number;
  children: ReactNode;
  styles: {
    card: object;
    iconWrap: object;
    iconDanger: object;
    title: object;
    [key: string]: object;
  };
  radiusGate: number;
}) {
  const { theme } = useAppTheme();
  const ch = theme.chat;

  return (
    <Animated.View entering={FadeInDown.delay(delay).duration(400).springify().damping(22)}>
      <NeptunSurface variant="raised" padding={22} radius={radiusGate} style={styles.card}>
        <View style={[styles.iconWrap, tone === 'danger' && styles.iconDanger]}>
          <Ionicons name={icon} size={32} color={iconColor} />
        </View>
        <Text style={[styles.title, tone === 'danger' && { color: ch.danger }]}>{title}</Text>
        {children}
      </NeptunSurface>
    </Animated.View>
  );
}

import { Ionicons } from '@expo/vector-icons';
import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  TextInput,
  View,
} from 'react-native';
import { Card } from '../components/Card';
import { PrimaryButton } from '../components/PrimaryButton';
import { Text } from '../components/Text';
import { endpoints } from '../config/api';
import { AppConstants } from '../config/constants';
import { apiRequest } from '../services/apiClient';
import { storage } from '../services/storage';
import { colors } from '../theme/colors';
import { fonts } from '../theme/fonts';
import { spacing } from '../theme/colors';
import { useLegacyScreenStyles } from '../theme/useLegacyScreenStyles';

const TYPES = [
  { id: 'general', label: 'Загальне', icon: 'chatbubble-outline' as const },
  { id: 'bug', label: 'Помилка', icon: 'bug-outline' as const },
  { id: 'suggestion', label: 'Пропозиція', icon: 'bulb-outline' as const },
];

type Ticket = Record<string, unknown>;

export function FeedbackScreen() {
  const styles = useScreenStyles();
  const [selectedType, setSelectedType] = useState('general');
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loadingTickets, setLoadingTickets] = useState(true);

  const loadTickets = useCallback(async () => {
    setLoadingTickets(true);
    try {
      const deviceId = await storage.getDeviceId();
      const data = await apiRequest<{ feedback?: Ticket[] }>(
        `${endpoints.feedback}?device_id=${encodeURIComponent(deviceId)}&limit=30`,
      );
      setTickets(Array.isArray(data.feedback) ? data.feedback : []);
    } catch {
      setTickets([]);
    } finally {
      setLoadingTickets(false);
    }
  }, []);

  useEffect(() => {
    void loadTickets();
  }, [loadTickets]);

  async function submit() {
    const text = message.trim();
    if (!text) {
      Alert.alert('NEPTUN', 'Введіть текст звернення');
      return;
    }
    setSending(true);
    try {
      const deviceId = await storage.getDeviceId();
      await apiRequest(endpoints.feedback, {
        method: 'POST',
        body: JSON.stringify({
          device_id: deviceId,
          type: selectedType,
          message: text,
          app_version: AppConstants.appVersion,
        }),
      });
      setMessage('');
      await loadTickets();
      Alert.alert('Дякуємо', 'Звернення надіслано');
    } catch (e) {
      Alert.alert('Помилка', e instanceof Error ? e.message : 'Не вдалося надіслати');
    } finally {
      setSending(false);
    }
  }

  return (
    <ScrollView style={styles.root} contentContainerStyle={styles.pad} keyboardShouldPersistTaps="handled">
      <Text style={styles.title}>Зворотній зв'язок</Text>
      <Text muted style={styles.intro}>
        Повідомте про помилки або запропонуйте покращення. Відповіді з'являться нижче.
      </Text>

      <View style={styles.typeRow}>
        {TYPES.map((t) => {
          const active = selectedType === t.id;
          return (
            <Pressable
              key={t.id}
              style={[styles.typeChip, active && styles.typeChipActive]}
              onPress={() => setSelectedType(t.id)}
            >
              <Ionicons name={t.icon} size={16} color={active ? colors.accent : colors.muted} />
              <Text style={[styles.typeLabel, active && styles.typeLabelActive]}>{t.label}</Text>
            </Pressable>
          );
        })}
      </View>

      <TextInput
        style={styles.input}
        placeholder="Опишіть проблему або пропозицію…"
        placeholderTextColor={colors.muted}
        multiline
        value={message}
        onChangeText={setMessage}
        textAlignVertical="top"
      />

      <PrimaryButton onPress={() => void submit()} disabled={sending}>
        {sending ? 'Надсилання…' : 'Надіслати'}
      </PrimaryButton>

      <Text style={styles.historyTitle}>Історія звернень</Text>
      {loadingTickets ? (
        <ActivityIndicator color={colors.accent} style={{ marginTop: 16 }} />
      ) : tickets.length === 0 ? (
        <Text muted style={styles.empty}>
          Поки немає звернень
        </Text>
      ) : (
        tickets.map((ticket, i) => {
          const id = String(ticket.id ?? i);
          const type = String(ticket.type ?? 'general');
          const status = String(ticket.status ?? 'open');
          const body = String(ticket.message ?? ticket.body ?? '');
          return (
            <Card key={id} style={styles.ticket}>
              <View style={styles.ticketHead}>
                <Text style={styles.ticketType}>{type}</Text>
                <Text muted style={styles.ticketStatus}>
                  {status}
                </Text>
              </View>
              <Text style={styles.ticketBody} numberOfLines={6}>
                {body}
              </Text>
            </Card>
          );
        })
      )}
    </ScrollView>
  );
}


function useScreenStyles() {
  return useLegacyScreenStyles((c) => ({
  root: { flex: 1, backgroundColor: c.bg },
  pad: { padding: spacing.lg, paddingBottom: 40 },
  title: {
    fontFamily: fonts.bold,
    fontSize: 22,
    marginBottom: 8,
  },
  intro: { fontSize: 13, lineHeight: 18, marginBottom: 16 },
  typeRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 12,
  },
  typeChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: c.border,
    backgroundColor: c.surface2,
  },
  typeChipActive: {
    borderColor: c.accent + '66',
    backgroundColor: c.accent + '18',
  },
  typeLabel: {
    fontFamily: fonts.semiBold,
    fontSize: 12,
    color: c.muted,
  },
  typeLabelActive: {
    color: c.accent,
  },
  input: {
    minHeight: 120,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: c.border,
    backgroundColor: c.inputBg,
    color: c.text,
    fontFamily: fonts.regular,
    fontSize: 15,
    padding: 14,
    marginBottom: 14,
  },
  historyTitle: {
    marginTop: 28,
    marginBottom: 10,
    fontFamily: fonts.bold,
    fontSize: 16,
  },
  empty: { marginTop: 8 },
  ticket: { marginBottom: 10, gap: 8 },
  ticketHead: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  ticketType: {
    fontFamily: fonts.semiBold,
    fontSize: 13,
    textTransform: 'capitalize',
  },
  ticketStatus: { fontSize: 12 },
  ticketBody: { fontSize: 14, lineHeight: 20, color: c.textSoft },
}));
}

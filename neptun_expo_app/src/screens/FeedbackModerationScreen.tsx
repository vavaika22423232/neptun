import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import { useCallback, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  TextInput,
  View,
} from 'react-native';
import { AppErrorState } from '../components/ui/AppErrorState';
import { PrimaryButton } from '../components/PrimaryButton';
import { Text } from '../components/Text';
import { AppCard } from '../components/ui/AppCard';
import { useModeratorScreenGuard } from '../core/moderator/useModeratorScreenGuard';
import { feedbackModerationService } from '../features/moderation/services/feedbackModerationService';
import type { FeedbackTicket } from '../features/moderation/types';
import { ApiError } from '../services/apiClient';
import { colors, spacing } from '../theme/colors';
import { fonts } from '../theme/fonts';
import { useLegacyScreenStyles } from '../theme/useLegacyScreenStyles';

const STATUS_FILTERS = [
  { id: 'all', label: 'Все' },
  { id: 'open', label: 'Відкриті' },
  { id: 'in_progress', label: 'В роботі' },
  { id: 'resolved', label: 'Вирішені' },
  { id: 'closed', label: 'Закриті' },
] as const;

const STATUS_ACTIONS = [
  { id: 'in_progress', label: 'В роботу', icon: 'play-outline' as const },
  { id: 'resolved', label: 'Вирішено', icon: 'checkmark-circle-outline' as const },
  { id: 'closed', label: 'Закрити', icon: 'close-outline' as const },
  { id: 'open', label: 'Відкрити', icon: 'refresh-outline' as const },
] as const;

function statusLabel(status: string): string {
  switch (status) {
    case 'open':
      return 'Відкритий';
    case 'in_progress':
      return 'В роботі';
    case 'resolved':
      return 'Вирішений';
    case 'closed':
      return 'Закритий';
    default:
      return status;
  }
}

function typeLabel(type: string): string {
  switch (type) {
    case 'bug':
      return 'Помилка';
    case 'suggestion':
      return 'Пропозиція';
    default:
      return 'Загальне';
  }
}

function formatDate(iso?: string): string {
  if (!iso) return '';
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return iso;
  const diffMin = Math.floor((Date.now() - dt.getTime()) / 60_000);
  if (diffMin < 60) return `${diffMin} хв тому`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `${diffH} год тому`;
  const diffD = Math.floor(diffH / 24);
  if (diffD < 7) return `${diffD} дн тому`;
  return `${dt.getDate()}.${String(dt.getMonth() + 1).padStart(2, '0')}.${dt.getFullYear()}`;
}

export function FeedbackModerationScreen() {
  const isModerator = useModeratorScreenGuard();
  const styles = useScreenStyles();
  const [tickets, setTickets] = useState<FeedbackTicket[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [replies, setReplies] = useState<Record<string, string>>({});
  const [sendingReply, setSendingReply] = useState<string | null>(null);
  const [updatingStatus, setUpdatingStatus] = useState<string | null>(null);

  const loadTickets = useCallback(
    async (isRefresh = false, statusOverride?: string) => {
      const status = statusOverride ?? filterStatus;
      if (isRefresh) setRefreshing(true);
      else setLoading(true);
      setError(null);
      try {
        const list = await feedbackModerationService.loadTickets(status);
        setTickets(list);
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) {
          setError('Невірний доступ. Увійдіть як модератор.');
        } else {
          setError(e instanceof Error ? e.message : 'Помилка завантаження');
        }
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [filterStatus],
  );

  useFocusEffect(
    useCallback(() => {
      void loadTickets();
    }, [loadTickets]),
  );

  const onUpdateStatus = useCallback(
    async (ticketId: string, status: string) => {
      setUpdatingStatus(ticketId);
      try {
        await feedbackModerationService.updateStatus(ticketId, status);
        await loadTickets(true);
      } catch (e) {
        Alert.alert('Помилка', e instanceof Error ? e.message : 'Не вдалося оновити статус');
      } finally {
        setUpdatingStatus(null);
      }
    },
    [loadTickets],
  );

  const onSendReply = useCallback(
    async (ticketId: string) => {
      const message = (replies[ticketId] ?? '').trim();
      if (!message) return;
      setSendingReply(ticketId);
      try {
        await feedbackModerationService.sendReply(ticketId, message);
        setReplies((prev) => ({ ...prev, [ticketId]: '' }));
        await loadTickets(true);
      } catch (e) {
        Alert.alert('Помилка', e instanceof Error ? e.message : 'Не вдалося надіслати відповідь');
      } finally {
        setSendingReply(null);
      }
    },
    [loadTickets, replies],
  );

  if (!isModerator) return null;

  if (loading && !refreshing) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.accent} size="large" />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.root}>
        <AppErrorState title="Помилка завантаження" subtitle={error} onRetry={() => void loadTickets()} />
      </View>
    );
  }

  return (
    <View style={styles.root}>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.filters}
      >
        {STATUS_FILTERS.map((f) => {
          const active = filterStatus === f.id;
          return (
            <Pressable
              key={f.id}
              style={[styles.filterChip, active && styles.filterChipActive]}
              onPress={() => {
                setFilterStatus(f.id);
                void loadTickets(false, f.id);
              }}
            >
              <Text style={[styles.filterLabel, active && styles.filterLabelActive]}>{f.label}</Text>
            </Pressable>
          );
        })}
      </ScrollView>

      <ScrollView
        contentContainerStyle={styles.listPad}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={() => void loadTickets(true)} tintColor={colors.accent} />
        }
      >
        {tickets.length === 0 ? (
          <Text muted style={styles.empty}>
            Немає відгуків
          </Text>
        ) : (
          tickets.map((ticket) => {
            const expanded = expandedId === ticket.id;
            return (
              <Pressable key={ticket.id} onPress={() => setExpandedId(expanded ? null : ticket.id)}>
                <AppCard style={styles.card}>
                  <View style={styles.cardHead}>
                    <View style={styles.badges}>
                      <View style={styles.statusBadge}>
                        <Text style={styles.badgeText}>{statusLabel(ticket.status)}</Text>
                      </View>
                      <Text muted style={styles.typeBadge}>
                        {typeLabel(ticket.type)}
                      </Text>
                    </View>
                    <View style={styles.expandMeta}>
                      {ticket.responses.length > 0 ? (
                        <Text muted style={styles.replyCount}>
                          💬 {ticket.responses.length}
                        </Text>
                      ) : null}
                      <Ionicons
                        name={expanded ? 'chevron-up' : 'chevron-down'}
                        size={18}
                        color={colors.muted}
                      />
                    </View>
                  </View>

                  <Text style={styles.message} numberOfLines={expanded ? undefined : 2}>
                    {ticket.message}
                  </Text>

                  {!expanded ? (
                    <Text muted style={styles.datePreview}>
                      {formatDate(ticket.created_at)}
                    </Text>
                  ) : null}

                  {expanded ? (
                    <View style={styles.details}>
                      <MetaRow label="Пристрій" value={ticket.device || '—'} />
                      <MetaRow
                        label="Device ID"
                        value={
                          ticket.device_id
                            ? `${ticket.device_id.slice(0, Math.min(8, ticket.device_id.length))}…`
                            : '—'
                        }
                      />
                      <MetaRow label="Версія" value={ticket.app_version || '—'} />
                      <MetaRow label="Дата" value={formatDate(ticket.created_at)} />

                      <View style={styles.statusActions}>
                        {STATUS_ACTIONS.filter((a) => a.id !== ticket.status).map((action) => (
                          <Pressable
                            key={action.id}
                            style={styles.statusAction}
                            disabled={updatingStatus === ticket.id}
                            onPress={() => void onUpdateStatus(ticket.id, action.id)}
                          >
                            <Ionicons name={action.icon} size={14} color={colors.accent} />
                            <Text style={styles.statusActionLabel}>{action.label}</Text>
                          </Pressable>
                        ))}
                      </View>

                      {ticket.responses.length > 0 ? (
                        <View style={styles.responses}>
                          <Text style={styles.responsesTitle}>Відповіді</Text>
                          {ticket.responses.map((r, idx) => {
                            const isAdmin = r.author === 'admin';
                            return (
                              <View
                                key={`${ticket.id}-r-${idx}`}
                                style={[styles.responseBox, isAdmin && styles.responseBoxAdmin]}
                              >
                                <Text style={styles.responseAuthor}>
                                  {isAdmin ? 'Модератор' : 'Користувач'}
                                </Text>
                                <Text style={styles.responseMessage}>{r.message ?? ''}</Text>
                                <Text muted style={styles.responseDate}>
                                  {formatDate(r.created_at)}
                                </Text>
                              </View>
                            );
                          })}
                        </View>
                      ) : null}

                      <View style={styles.replyRow}>
                        <TextInput
                          style={styles.replyInput}
                          placeholder="Відповідь модератора…"
                          placeholderTextColor={colors.muted}
                          multiline
                          value={replies[ticket.id] ?? ''}
                          onChangeText={(text) =>
                            setReplies((prev) => ({ ...prev, [ticket.id]: text }))
                          }
                        />
                        <Pressable
                          style={styles.sendBtn}
                          disabled={sendingReply === ticket.id}
                          onPress={() => void onSendReply(ticket.id)}
                        >
                          {sendingReply === ticket.id ? (
                            <ActivityIndicator color="#fff" size="small" />
                          ) : (
                            <Ionicons name="send" size={18} color="#fff" />
                          )}
                        </Pressable>
                      </View>
                    </View>
                  ) : null}
                </AppCard>
              </Pressable>
            );
          })
        )}
      </ScrollView>
    </View>
  );
}

function MetaRow({ label, value }: { label: string; value: string }) {
  const styles = useScreenStyles();
return (
    <View style={styles.metaRow}>
      <Text muted style={styles.metaLabel}>
        {label}
      </Text>
      <Text style={styles.metaValue}>{value}</Text>
    </View>
  );
}


function useScreenStyles() {
  return useLegacyScreenStyles((c) => ({
  root: { flex: 1, backgroundColor: c.bg },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: c.bg },
  filters: { paddingHorizontal: spacing.lg, paddingVertical: 10, gap: 8 },
  filterChip: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: c.border,
    backgroundColor: c.surface2,
  },
  filterChipActive: {
    borderColor: c.accent + '66',
    backgroundColor: c.accent + '18',
  },
  filterLabel: { fontFamily: fonts.semiBold, fontSize: 12, color: c.muted },
  filterLabelActive: { color: c.accent },
  listPad: { padding: spacing.lg, paddingBottom: 40, gap: 10 },
  empty: { textAlign: 'center', marginTop: 32 },
  card: { gap: 8 },
  cardHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  badges: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
    backgroundColor: c.warning + '33',
  },
  badgeText: { fontFamily: fonts.semiBold, fontSize: 11 },
  typeBadge: { fontSize: 11 },
  expandMeta: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  replyCount: { fontSize: 12 },
  message: { fontSize: 14, lineHeight: 20, color: c.textSoft },
  datePreview: { fontSize: 11 },
  details: { gap: 8, marginTop: 4 },
  metaRow: { flexDirection: 'row', gap: 8 },
  metaLabel: { width: 80, fontSize: 12 },
  metaValue: { flex: 1, fontSize: 12 },
  statusActions: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 4 },
  statusAction: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: c.border,
  },
  statusActionLabel: { fontSize: 12, color: c.accent },
  responses: { gap: 6, marginTop: 8 },
  responsesTitle: { fontFamily: fonts.semiBold, fontSize: 13, color: c.textSoft },
  responseBox: {
    padding: 10,
    borderRadius: 10,
    backgroundColor: c.surface2,
    gap: 4,
  },
  responseBoxAdmin: { backgroundColor: c.accent + '14' },
  responseAuthor: { fontFamily: fonts.semiBold, fontSize: 11, color: c.accent },
  responseMessage: { fontSize: 13, lineHeight: 18 },
  responseDate: { fontSize: 10 },
  replyRow: { flexDirection: 'row', gap: 8, alignItems: 'flex-end', marginTop: 8 },
  replyInput: {
    flex: 1,
    minHeight: 44,
    maxHeight: 100,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: c.border,
    backgroundColor: c.inputBg,
    color: c.text,
    fontFamily: fonts.regular,
    fontSize: 14,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  sendBtn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: c.accent,
  },
}));
}

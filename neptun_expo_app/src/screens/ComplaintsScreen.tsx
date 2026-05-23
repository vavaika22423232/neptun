import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import { useCallback, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Image,
  Modal,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';
import { AppErrorState } from '../components/ui/AppErrorState';
import { PrimaryButton } from '../components/PrimaryButton';
import { Text } from '../components/Text';
import { AppCard } from '../components/ui/AppCard';
import { useModeratorScreenGuard } from '../core/moderator/useModeratorScreenGuard';
import { chatReportsService } from '../features/moderation/services/chatReportsService';
import type { ChatReport } from '../features/moderation/types';
import { absoluteUrl } from '../config/api';
import { ApiError } from '../services/apiClient';
import { colors, spacing } from '../theme/colors';
import { fonts } from '../theme/fonts';
import { useLegacyScreenStyles } from '../theme/useLegacyScreenStyles';

type Filter = 'PENDING' | 'ALL';

function formatTime(iso?: string): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const dd = String(d.getDate()).padStart(2, '0');
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const hh = String(d.getHours()).padStart(2, '0');
  const min = String(d.getMinutes()).padStart(2, '0');
  return `${dd}.${mm} ${hh}:${min}`;
}

function mediaUrl(url?: string): string | null {
  if (!url) return null;
  return url.startsWith('http') ? url : absoluteUrl(url);
}

function hasValidUser(report: ChatReport): boolean {
  const nick = report.reportedNickname.trim().toLowerCase();
  return (nick.length > 0 && nick !== 'анонім') || report.reportedDeviceId.length > 0;
}

export function ComplaintsScreen() {
  const isModerator = useModeratorScreenGuard();
  const styles = useScreenStyles();
  const [reports, setReports] = useState<ChatReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>('PENDING');
  const [previewImage, setPreviewImage] = useState<string | null>(null);

  const loadReports = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);
    try {
      const list = await chatReportsService.loadReports();
      setReports(list);
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
  }, []);

  useFocusEffect(
    useCallback(() => {
      void loadReports();
    }, [loadReports]),
  );

  const filtered = useMemo(
    () => (filter === 'ALL' ? reports : reports.filter((r) => r.status === 'PENDING')),
    [filter, reports],
  );

  const confirm = useCallback((title: string, message: string, onConfirm: () => void) => {
    Alert.alert(title, message, [
      { text: 'Скасувати', style: 'cancel' },
      { text: 'Так', style: 'destructive', onPress: onConfirm },
    ]);
  }, []);

  const onDeleteAndResolve = useCallback(
    (report: ChatReport) => {
      confirm('Підтвердження', 'Видалити повідомлення та закрити скаргу?', () => {
        void (async () => {
          try {
            const result = await chatReportsService.deleteMessage(report.messageId);
            await chatReportsService.resolveReport(report.id, 'RESOLVED');
            Alert.alert(
              'NEPTUN',
              result === 'missing'
                ? 'Повідомлення вже видалено, скаргу закрито'
                : 'Повідомлення видалено, скарга закрита',
            );
            await loadReports(true);
          } catch (e) {
            Alert.alert('Помилка', e instanceof Error ? e.message : 'Не вдалося виконати дію');
          }
        })();
      });
    },
    [confirm, loadReports],
  );

  const onReject = useCallback(
    (report: ChatReport) => {
      void (async () => {
        try {
          await chatReportsService.resolveReport(report.id, 'REJECTED');
          Alert.alert('NEPTUN', 'Скаргу відхилено');
          await loadReports(true);
        } catch (e) {
          Alert.alert('Помилка', e instanceof Error ? e.message : 'Не вдалося відхилити');
        }
      })();
    },
    [loadReports],
  );

  const onBlock = useCallback(
    (report: ChatReport) => {
      if (!hasValidUser(report)) {
        Alert.alert('NEPTUN', 'Немає даних про користувача для блокування');
        return;
      }
      const label = report.reportedNickname || 'користувача';
      confirm('Заблокувати', `Заблокувати ${label}? Він не зможе писати в чат.`, () => {
        void (async () => {
          try {
            const nick = report.reportedNickname.trim().toLowerCase();
            await chatReportsService.banUser({
              nickname: nick && nick !== 'анонім' ? report.reportedNickname : undefined,
              deviceId: report.reportedDeviceId || undefined,
              reason: `Скарга: ${report.reason}`,
            });
            Alert.alert('NEPTUN', 'Користувача заблоковано');
            await loadReports(true);
          } catch (e) {
            Alert.alert('Помилка', e instanceof Error ? e.message : 'Не вдалося заблокувати');
          }
        })();
      });
    },
    [confirm, loadReports],
  );

  const onDeleteAll = useCallback(
    (report: ChatReport) => {
      if (!hasValidUser(report)) {
        Alert.alert('NEPTUN', 'Немає даних про користувача для видалення');
        return;
      }
      const label = report.reportedNickname || 'цього користувача';
      confirm('Видалити всі повідомлення', `Видалити всі повідомлення від ${label}?`, () => {
        void (async () => {
          try {
            const nick = report.reportedNickname.trim().toLowerCase();
            const deleted = await chatReportsService.deleteAllUserMessages({
              nickname: nick && nick !== 'анонім' ? report.reportedNickname : undefined,
              deviceId: report.reportedDeviceId || undefined,
            });
            Alert.alert('NEPTUN', `Видалено повідомлень: ${deleted}`);
            await loadReports(true);
          } catch (e) {
            Alert.alert('Помилка', e instanceof Error ? e.message : 'Не вдалося видалити');
          }
        })();
      });
    },
    [confirm, loadReports],
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
        <AppErrorState title="Помилка завантаження" subtitle={error} onRetry={() => void loadReports()} />
      </View>
    );
  }

  return (
    <View style={styles.root}>
      <View style={styles.filterRow}>
        {(['PENDING', 'ALL'] as const).map((value) => {
          const active = filter === value;
          return (
            <Pressable
              key={value}
              style={[styles.filterChip, active && styles.filterChipActive]}
              onPress={() => setFilter(value)}
            >
              <Text style={[styles.filterLabel, active && styles.filterLabelActive]}>
                {value === 'PENDING' ? 'Нові' : 'Всі'}
              </Text>
            </Pressable>
          );
        })}
      </View>

      <ScrollView
        contentContainerStyle={styles.listPad}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={() => void loadReports(true)} tintColor={colors.accent} />
        }
      >
        {filtered.length === 0 ? (
          <View style={styles.empty}>
            <Ionicons name="file-tray-outline" size={48} color={colors.muted} />
            <Text style={styles.emptyTitle}>Немає скарг</Text>
          </View>
        ) : (
          filtered.map((report) => (
            <ReportCard
              key={report.id}
              report={report}
              onDelete={() => onDeleteAndResolve(report)}
              onReject={() => onReject(report)}
              onBlock={() => onBlock(report)}
              onDeleteAll={() => onDeleteAll(report)}
              onPreviewImage={(url) => setPreviewImage(url)}
            />
          ))
        )}
      </ScrollView>

      <Modal visible={!!previewImage} transparent animationType="fade" onRequestClose={() => setPreviewImage(null)}>
        <Pressable style={styles.modalBackdrop} onPress={() => setPreviewImage(null)}>
          {previewImage ? (
            <Image source={{ uri: previewImage }} style={styles.modalImage} resizeMode="contain" />
          ) : null}
        </Pressable>
      </Modal>
    </View>
  );
}

function ReportCard({
  report,
  onDelete,
  onReject,
  onBlock,
  onDeleteAll,
  onPreviewImage,
}: {
  report: ChatReport;
  onDelete: () => void;
  onReject: () => void;
  onBlock: () => void;
  onDeleteAll: () => void;
  onPreviewImage: (url: string) => void;
}) {
  const styles = useScreenStyles();
  const isPending = report.status === 'PENDING';
  const image = mediaUrl(report.imageUrl);
  const hasVoice = !!report.audioUrl;
  const userOk = hasValidUser(report);
  const duration = report.audioDuration ?? 0;
  const voiceLabel = `${Math.floor(duration / 60)}:${String(duration % 60).padStart(2, '0')}`;

  return (
    <AppCard style={styles.card}>
      <View style={styles.cardHead}>
        <View style={[styles.statusBadge, report.status !== 'PENDING' && styles.statusBadgeMuted]}>
          <Text style={styles.statusText}>{report.status}</Text>
        </View>
        <Text muted style={styles.time}>
          {formatTime(report.createdAt)}
        </Text>
      </View>

      <Text style={styles.reason}>Причина: {report.reason}</Text>

      {image ? (
        <Pressable onPress={() => onPreviewImage(image)}>
          <Image source={{ uri: image }} style={styles.reportImage} resizeMode="cover" />
        </Pressable>
      ) : null}

      {hasVoice ? (
        <View style={styles.voiceBox}>
          <Ionicons name="mic-outline" size={18} color={colors.accent} />
          <Text style={styles.voiceText}>Голосове повідомлення · {voiceLabel}</Text>
        </View>
      ) : null}

      <View style={styles.messageBox}>
        <Text style={styles.messageText}>
          {report.originalText.trim() ||
            (image || hasVoice ? '(медіа)' : '<без тексту>')}
        </Text>
      </View>

      <View style={styles.metaRow}>
        <Text style={styles.reporter}>Скаржник: {report.reporterNickname}</Text>
        {report.reportedNickname ? (
          <Text style={styles.author}>Автор: {report.reportedNickname}</Text>
        ) : null}
      </View>

      {isPending ? (
        <View style={styles.actions}>
          <PrimaryButton onPress={onDelete}>Видалити</PrimaryButton>
          <PrimaryButton variant="secondary" onPress={onReject}>
            Відхилити
          </PrimaryButton>
          {userOk ? (
            <>
              <PrimaryButton variant="secondary" onPress={onBlock}>
                Заблокувати
              </PrimaryButton>
              <PrimaryButton variant="ghost" onPress={onDeleteAll}>
                Видалити всі
              </PrimaryButton>
            </>
          ) : null}
        </View>
      ) : null}
    </AppCard>
  );
}


function useScreenStyles() {
  return useLegacyScreenStyles((c) => ({
  root: { flex: 1, backgroundColor: c.bg },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: c.bg },
  filterRow: {
    flexDirection: 'row',
    gap: 8,
    paddingHorizontal: spacing.lg,
    paddingVertical: 10,
  },
  filterChip: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 10,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: c.border,
    backgroundColor: c.surface2,
  },
  filterChipActive: {
    borderColor: c.accent + '66',
    backgroundColor: c.accent + '18',
  },
  filterLabel: { fontFamily: fonts.semiBold, fontSize: 13, color: c.muted },
  filterLabelActive: { color: c.accent },
  listPad: { padding: spacing.lg, paddingBottom: 40, gap: 12 },
  empty: { alignItems: 'center', paddingVertical: 48, gap: 12 },
  emptyTitle: { fontFamily: fonts.bold, fontSize: 17 },
  card: { gap: 10 },
  cardHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
    backgroundColor: c.warning + '33',
  },
  statusBadgeMuted: { backgroundColor: c.border },
  statusText: { fontFamily: fonts.semiBold, fontSize: 11 },
  time: { fontSize: 12 },
  reason: { fontFamily: fonts.semiBold, fontSize: 13, color: c.textSoft },
  reportImage: { width: '100%', height: 160, borderRadius: 10, backgroundColor: c.surface2 },
  voiceBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    padding: 10,
    borderRadius: 10,
    backgroundColor: c.surface2,
  },
  voiceText: { fontSize: 13, color: c.textSoft },
  messageBox: {
    padding: 10,
    borderRadius: 10,
    backgroundColor: c.surface2,
  },
  messageText: { fontSize: 14, lineHeight: 20 },
  metaRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  reporter: { fontSize: 12, color: c.accent },
  author: { fontSize: 12, color: c.danger },
  actions: { gap: 8, marginTop: 4 },
  modalBackdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.92)',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
  },
  modalImage: { width: '100%', height: '80%' },
}));
}

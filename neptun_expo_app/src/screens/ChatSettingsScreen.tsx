import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import type { ComponentProps } from 'react';
import { useCallback, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  TextInput,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { PrimaryButton } from '../components/PrimaryButton';
import { Text } from '../components/Text';
import { useApp } from '../context/AppContext';
import { NeptunPressable } from '../design/components/NeptunPressable';
import { NeptunSurface } from '../design/components/NeptunSurface';
import { ChatAmbientBackground } from '../features/chat/components/ChatAmbientBackground';
import { chat } from '../features/chat/theme/chatTokens';
import { chatService } from '../services/chatService';
import { moderatorService } from '../services/moderatorService';
import { fonts } from '../theme/fonts';

export function ChatSettingsScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { nickname, isModerator, refreshIdentity } = useApp();
  const [newNick, setNewNick] = useState('');
  const [nickError, setNickError] = useState<string | null>(null);
  const [nickBusy, setNickBusy] = useState(false);
  const [modSecret, setModSecret] = useState('');
  const [modError, setModError] = useState<string | null>(null);
  const [modSuccess, setModSuccess] = useState<string | null>(null);
  const [showModSection, setShowModSection] = useState(false);
  const [banList, setBanList] = useState<string[] | null>(null);
  const [banLoading, setBanLoading] = useState(false);

  const changeNickname = useCallback(async () => {
    const nick = newNick.trim();
    if (nick.length < 2 || nick.length > 20) {
      setNickError('Від 2 до 20 символів');
      return;
    }
    setNickBusy(true);
    setNickError(null);
    const check = await chatService.checkNickname(nick);
    if (!check.available) {
      setNickBusy(false);
      setNickError(check.error ?? 'Нікнейм зайнятий');
      return;
    }
    const result = await chatService.registerNickname(nick);
    setNickBusy(false);
    if (!result.success) {
      setNickError(result.error ?? 'Помилка');
      return;
    }
    setNewNick('');
    await refreshIdentity();
    Alert.alert('NEPTUN', 'Нікнейм змінено');
  }, [newNick, refreshIdentity]);

  const activateModerator = useCallback(async () => {
    const formatErr = moderatorService.validateModeratorSecretInput(modSecret);
    if (formatErr) {
      setModError(formatErr);
      setModSuccess(null);
      return;
    }
    setModError(null);
    const err = await moderatorService.login(modSecret);
    if (err) setModError(err);
    else {
      setModSuccess('Модератор активовано ✓');
      await refreshIdentity();
    }
  }, [modSecret, refreshIdentity]);

  const loadBans = useCallback(async () => {
    setBanLoading(true);
    const list = await chatService.getBanList();
    setBanList(list);
    setBanLoading(false);
  }, []);

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      <ChatAmbientBackground />
      <View style={styles.appBar}>
        <NeptunPressable haptic onPress={() => router.back()} style={styles.backBtn}>
          <Ionicons name="chevron-back" size={24} color={chat.text} />
        </NeptunPressable>
        <Text style={styles.appBarTitle}>Налаштування чату</Text>
        <View style={styles.backBtn} />
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {isModerator ? (
          <NeptunPressable haptic onPress={() => router.push('/chat-admin')} style={styles.adminCard}>
            <View style={styles.adminIcon}>
              <Ionicons name="shield" size={22} color={chat.premium} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.adminTitle}>Адмін панель</Text>
              <Text muted style={styles.adminSub}>Заблоковані та розблокування</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color={chat.textMuted} />
          </NeptunPressable>
        ) : null}

        <SectionLabel title="Ваш нікнейм" />
        <NeptunSurface variant="flat" padding={14} radius={chat.radiusGate}>
          <Row icon="person-circle-outline" label={nickname ?? '—'} />
        </NeptunSurface>

        <SectionLabel title="Змінити нікнейм" />
        <NeptunSurface variant="flat" padding={14} radius={chat.radiusGate} style={{ gap: 12 }}>
          <TextInput
            value={newNick}
            onChangeText={setNewNick}
            maxLength={20}
            placeholder="Новий нікнейм"
            placeholderTextColor={chat.textFaint}
            style={styles.input}
            autoCapitalize="none"
          />
          {nickError ? <Text style={styles.fieldError}>{nickError}</Text> : null}
          <PrimaryButton onPress={() => void changeNickname()} disabled={nickBusy}>
            {nickBusy ? 'Збереження…' : 'Зберегти'}
          </PrimaryButton>
        </NeptunSurface>

        {isModerator ? (
          <>
            <SectionLabel title="Модерація" />
            <NeptunSurface variant="flat" padding={14} radius={chat.radiusGate}>
              <NeptunPressable haptic onPress={() => setShowModSection((v) => !v)} style={styles.expandRow}>
                <Ionicons name="shield-checkmark" size={20} color={chat.success} />
                <Text style={styles.rowLabel}>Ви модератор</Text>
                <Ionicons name={showModSection ? 'chevron-up' : 'chevron-down'} size={18} color={chat.textMuted} />
              </NeptunPressable>
              {showModSection ? (
                <View style={styles.modInner}>
                  <TextInput
                    value={modSecret}
                    onChangeText={setModSecret}
                    secureTextEntry
                    placeholder="Пароль модератора"
                    placeholderTextColor={chat.textFaint}
                    style={styles.input}
                  />
                  <NeptunPressable haptic onPress={() => void activateModerator()} style={styles.tonalBtn}>
                    <Text style={styles.tonalBtnText}>Оновити</Text>
                  </NeptunPressable>
                  {modError ? <Text style={styles.fieldError}>{modError}</Text> : null}
                  {modSuccess ? <Text style={styles.success}>{modSuccess}</Text> : null}
                </View>
              ) : null}
            </NeptunSurface>

            <SectionLabel title="Заблоковані" />
            <NeptunSurface variant="flat" padding={14} radius={chat.radiusGate}>
              <NeptunPressable haptic onPress={() => void loadBans()} style={styles.expandRow}>
                <Ionicons name="ban" size={20} color={chat.danger} />
                <Text style={styles.rowLabel}>Список заблокованих</Text>
                {banLoading ? (
                  <ActivityIndicator size="small" color={chat.textMuted} />
                ) : (
                  <Ionicons name="refresh" size={18} color={chat.textMuted} />
                )}
              </NeptunPressable>
              {banList?.map((nick) => (
                <NeptunPressable
                  key={nick}
                  haptic
                  onPress={() => {
                    Alert.alert(nick, 'Розблокувати користувача?', [
                      { text: 'Скасувати', style: 'cancel' },
                      {
                        text: 'Розблокувати',
                        onPress: () => {
                          void chatService.unbanUser(nick).then((ok) => {
                            if (ok) setBanList((list) => list?.filter((n) => n !== nick) ?? []);
                          });
                        },
                      },
                    ]);
                  }}
                  style={styles.banRow}
                >
                  <Text style={styles.banNick}>{nick}</Text>
                  <Text muted style={styles.unbanHint}>
                    Розблокувати
                  </Text>
                </NeptunPressable>
              ))}
              {banList && banList.length === 0 ? (
                <Text muted style={styles.emptyBan}>
                  Список порожній
                </Text>
              ) : null}
            </NeptunSurface>
          </>
        ) : null}
      </ScrollView>
    </View>
  );
}

function SectionLabel({ title }: { title: string }) {
  return <Text style={styles.sectionLabel}>{title}</Text>;
}

function Row({ icon, label }: { icon: ComponentProps<typeof Ionicons>['name']; label: string }) {
  return (
    <View style={styles.row}>
      <Ionicons name={icon} size={22} color={chat.accentSoft} />
      <Text style={styles.rowLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: chat.bg },
  appBar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingBottom: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: chat.border,
  },
  backBtn: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center' },
  appBarTitle: { flex: 1, textAlign: 'center', fontFamily: fonts.bold, fontSize: 17, color: chat.text },
  scroll: { padding: 20, paddingBottom: 40, gap: 12 },
  sectionLabel: {
    marginTop: 8,
    marginBottom: 2,
    marginLeft: 4,
    fontFamily: fonts.semiBold,
    fontSize: 11,
    color: chat.textFaint,
    letterSpacing: 0.6,
    textTransform: 'uppercase',
  },
  adminCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    padding: 16,
    borderRadius: chat.radiusGate,
    backgroundColor: chat.surfaceGlass,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: chat.borderStrong,
    marginBottom: 4,
  },
  adminIcon: {
    width: 44,
    height: 44,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(212, 184, 122, 0.14)',
  },
  adminTitle: { fontFamily: fonts.semiBold, fontSize: 16, color: chat.text },
  adminSub: { fontSize: 12, marginTop: 2 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  rowLabel: { flex: 1, fontFamily: fonts.semiBold, fontSize: 15, color: chat.text },
  input: {
    borderRadius: 14,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: chat.borderStrong,
    backgroundColor: chat.surfaceInput,
    color: chat.text,
    fontFamily: fonts.medium,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 15,
  },
  fieldError: { color: chat.danger, fontSize: 12 },
  success: { color: chat.success, fontSize: 12 },
  expandRow: { flexDirection: 'row', alignItems: 'center', gap: 10, width: '100%' },
  modInner: { width: '100%', marginTop: 14, gap: 10 },
  tonalBtn: {
    height: 44,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(255,255,255,0.06)',
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: chat.border,
  },
  tonalBtnText: { fontFamily: fonts.semiBold, color: chat.accentSoft },
  banRow: {
    width: '100%',
    paddingVertical: 12,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: chat.divider,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  banNick: { fontSize: 14, color: chat.text },
  unbanHint: { fontSize: 11 },
  emptyBan: { paddingTop: 12, fontSize: 13 },
});

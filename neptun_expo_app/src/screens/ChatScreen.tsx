import { Ionicons } from '@expo/vector-icons';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Alert,
  Animated,
  Easing,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  TextInput,
  View,
} from 'react-native';
import { Card } from '../components/Card';
import { MainChrome } from '../components/MainChrome';
import { PrimaryButton } from '../components/PrimaryButton';
import { Text } from '../components/Text';
import { chatThemeById, CHAT_THEME_DEFAULT_ID } from '../config/chatThemes';
import { useApp } from '../context/AppContext';
import { RootStackParamList } from '../navigation/types';
import { chatService } from '../services/chatService';
import { applySsePayloadToMessages, connectChatSse } from '../services/chatSseService';
import { storage } from '../services/storage';
import { colors } from '../theme/colors';
import { fonts } from '../theme/fonts';
import { avatarAccent, displayInitials } from '../utils/avatarPalette';
import { ChatMessage } from '../types/chat';

function formatClock(ts: number): string {
  const d = new Date(ts);
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  return `${hh}:${mm}`;
}

export function ChatScreen() {
  const { nickname, deviceId, setNickname, setOnlineCount, isModerator, refreshIdentity, isPremium } =
    useApp();
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [text, setText] = useState('');
  const [nickInput, setNickInput] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [ban, setBan] = useState<{ banned: boolean; reason?: string | null } | null>(null);
  const [sseConnected, setSseConnected] = useState(false);
  const listRef = useRef<FlatList<ChatMessage>>(null);
  const avatarPulse = useRef(new Animated.Value(1)).current;
  const [proBubbleTint, setProBubbleTint] = useState<string | null>(null);
  const [animatedAvatar, setAnimatedAvatar] = useState(false);

  useFocusEffect(
    useCallback(() => {
      void (async () => {
        const tid = (await storage.getProChatThemeId()) || CHAT_THEME_DEFAULT_ID;
        const theme = chatThemeById(tid);
        setProBubbleTint(isPremium && theme.bubbleTint ? theme.bubbleTint : null);
        setAnimatedAvatar(isPremium && (await storage.getProAnimatedAvatar()));
      })();
    }, [isPremium]),
  );

  useEffect(() => {
    if (!animatedAvatar) {
      avatarPulse.setValue(1);
      return;
    }
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(avatarPulse, {
          toValue: 1.07,
          duration: 900,
          easing: Easing.inOut(Easing.sin),
          useNativeDriver: true,
        }),
        Animated.timing(avatarPulse, {
          toValue: 1,
          duration: 900,
          easing: Easing.inOut(Easing.sin),
          useNativeDriver: true,
        }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [animatedAvatar, avatarPulse]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await chatService.fetchMessages();
      setMessages(data.messages);
      setOnlineCount(data.online);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Помилка завантаження');
    } finally {
      setLoading(false);
    }
  }, [setOnlineCount]);

  useEffect(() => {
    if (!nickname) {
      setBan(null);
      return;
    }
    let cancelled = false;
    void chatService.checkBanStatus().then((r) => {
      if (!cancelled) setBan(r);
    });
    return () => {
      cancelled = true;
    };
  }, [nickname]);

  useEffect(() => {
    if (!nickname || ban?.banned) return;
    const ac = new AbortController();
    setSseConnected(false);
    void connectChatSse(
      {
        onPayload(p) {
          if (p.type === 'connected') {
            const online = (p.data as { online?: number } | undefined)?.online;
            if (typeof online === 'number') setOnlineCount(online);
            setSseConnected(true);
          }
          setMessages((prev) => applySsePayloadToMessages(prev, p));
          if (p.type === 'new_message') {
            requestAnimationFrame(() => listRef.current?.scrollToEnd({ animated: true }));
          }
        },
        onError: () => setSseConnected(false),
      },
      { signal: ac.signal },
    ).catch(() => setSseConnected(false));
    return () => {
      ac.abort();
      setSseConnected(false);
    };
  }, [nickname, ban?.banned, setOnlineCount]);

  useEffect(() => {
    if (!nickname || ban?.banned) return;
    void load();
    const ms = sseConnected ? 55_000 : 12_000;
    const id = setInterval(load, ms);
    return () => clearInterval(id);
  }, [nickname, ban?.banned, load, sseConnected]);

  async function registerNickname() {
    setError(null);
    const nick = nickInput.trim();
    if (!nick) return;
    const check = await chatService.checkNickname(nick);
    if (!check.available) {
      setError(check.error || 'Нікнейм недоступний');
      return;
    }
    const result = await chatService.registerNickname(nick);
    if (!result.success) {
      setError(result.error || 'Помилка реєстрації');
      return;
    }
    setNickname(nick);
    await refreshIdentity();
    const b = await chatService.checkBanStatus();
    setBan(b);
  }

  async function send() {
    const trimmed = text.trim();
    if (!trimmed) return;
    setText('');
    try {
      const sent = await chatService.sendMessage(trimmed);
      setMessages((prev) => [...prev, sent]);
      requestAnimationFrame(() => listRef.current?.scrollToEnd({ animated: true }));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Помилка відправки');
      setText(trimmed);
    }
  }

  const gateChrome = (
    <MainChrome contextLabel="Чат" subtitleLeadingIcon="chatbubble-outline" showSearch />
  );

  if (!nickname) {
    return (
      <View style={styles.root}>
        {gateChrome}
        <View style={[styles.flex, styles.gatePad]}>
          <Card>
            <Text title>Вхід у чат</Text>
            <Text muted>Обери нікнейм. «Анонім» зарезервований системою.</Text>
            <TextInput
              value={nickInput}
              onChangeText={setNickInput}
              placeholder="Нікнейм"
              placeholderTextColor={colors.muted}
              style={styles.inputGate}
              autoCapitalize="none"
            />
            {error ? <Text style={styles.error}>{error}</Text> : null}
            <PrimaryButton onPress={registerNickname}>Увійти</PrimaryButton>
          </Card>
        </View>
      </View>
    );
  }

  if (ban?.banned) {
    return (
      <View style={styles.root}>
        {gateChrome}
        <View style={[styles.flex, styles.gatePad]}>
          <Card>
            <Text title>Доступ обмежено</Text>
            <Text muted>
              Ваш акаунт у чаті заблоковано.
              {ban.reason ? `\n\n${ban.reason}` : ''}
            </Text>
          </Card>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.root}>
      <MainChrome
        contextLabel="Чат"
        subtitleLeadingIcon="chatbubble-outline"
        showSearch
        onSearchPress={() => Alert.alert('Пошук', 'Незабаром у цьому екрані.')}
      />
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.select({ ios: 'padding', android: undefined })}
        keyboardVerticalOffset={0}
      >
        <View style={styles.statusBar}>
          <Text muted style={styles.statusTxt}>
            {loading ? 'Оновлення…' : sseConnected ? `SSE · ${nickname}` : `Polling · ${nickname}`}
          </Text>
          {isModerator ? (
            <Pressable onPress={() => navigation.navigate('ChatAdmin')} style={styles.modChip}>
              <Text style={styles.modChipTxt}>Модерація</Text>
            </Pressable>
          ) : null}
        </View>
        {error ? <Text style={styles.errorBar}>{error}</Text> : null}

        <FlatList
          ref={listRef}
          data={messages}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.messages}
          renderItem={({ item }) => {
            const hue = avatarAccent(item.userId);
            const initials = displayInitials(item.userId);
            const ts = item.timestamp;
            const isOwn = !!deviceId && item.deviceId === deviceId;
            const bubbleBg =
              isOwn && proBubbleTint ? proBubbleTint : colors.surface;
            const bubbleBorder =
              isOwn && proBubbleTint ? proBubbleTint + 'aa' : colors.border;

            const avatarInner = (
              <View style={[styles.avatar, { backgroundColor: hue + '28' }]}>
                <Text style={[styles.avatarTxt, { color: hue }]}>{initials}</Text>
              </View>
            );

            return (
              <View style={styles.msgRow}>
                {isOwn && animatedAvatar ? (
                  <Animated.View style={{ transform: [{ scale: avatarPulse }] }}>{avatarInner}</Animated.View>
                ) : (
                  avatarInner
                )}
                <View style={styles.bubbleWrap}>
                  <View style={[styles.bubble, { backgroundColor: bubbleBg, borderColor: bubbleBorder }]}>
                    <View style={styles.bubbleMeta}>
                      <Text style={[styles.author, { color: hue }]}>{item.userId}</Text>
                      {item.isModerator ? (
                        <View style={styles.modBadge}>
                          <Text style={styles.modBadgeTxt}>MOD</Text>
                        </View>
                      ) : null}
                      {item.isPro ? (
                        <View style={styles.proBadge}>
                          <Text style={styles.proBadgeTxt}>PRO</Text>
                        </View>
                      ) : null}
                    </View>
                    {item.replyTo?.text ? (
                      <View style={styles.replyBox}>
                        <Text muted numberOfLines={3} style={styles.replyTxt}>
                          {item.replyTo.nickname ? `${item.replyTo.nickname}: ` : ''}
                          {item.replyTo.text}
                        </Text>
                      </View>
                    ) : null}
                    <Text style={styles.msgBody}>{item.message}</Text>
                    <Text muted style={styles.time}>
                      {formatClock(ts)}
                    </Text>
                  </View>
                </View>
              </View>
            );
          }}
        />

        <View style={styles.composer}>
          <Pressable
            style={styles.circleBtn}
            onPress={() => Alert.alert('Вкладення', 'Фото та файли — незабаром.')}
          >
            <Ionicons name="add" size={26} color={colors.text} />
          </Pressable>
          <TextInput
            value={text}
            onChangeText={setText}
            placeholder="Напишіть повідомлення…"
            placeholderTextColor={colors.muted}
            style={styles.composerField}
            multiline
            maxLength={500}
          />
          <Pressable
            style={styles.circleBtn}
            onPress={() => (text.trim() ? void send() : undefined)}
            disabled={!text.trim()}
          >
            <Ionicons
              name="send"
              size={20}
              color={text.trim() ? colors.accent : colors.tabInactive}
            />
          </Pressable>
          <Pressable
            style={styles.circleBtn}
            onPress={() => Alert.alert('Голос', 'Голосові повідомлення — незабаром.')}
          >
            <Ionicons name="mic-outline" size={22} color={colors.text} />
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  flex: { flex: 1 },
  gatePad: { paddingHorizontal: 16, paddingTop: 8 },
  statusBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  statusTxt: { fontSize: 12, fontFamily: fonts.regular },
  modChip: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 999,
    backgroundColor: colors.surface2,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
  },
  modChipTxt: { fontFamily: fonts.semiBold, fontSize: 12, color: colors.accent },
  messages: { paddingHorizontal: 14, paddingBottom: 12, gap: 14 },
  msgRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 10 },
  avatar: {
    width: 38,
    height: 38,
    borderRadius: 19,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarTxt: { fontFamily: fonts.bold, fontSize: 13 },
  bubbleWrap: { flex: 1, minWidth: 0 },
  bubble: {
    backgroundColor: colors.surface,
    borderRadius: 18,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
  },
  bubbleMeta: { flexDirection: 'row', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 4 },
  author: { fontFamily: fonts.semiBold, fontSize: 14 },
  modBadge: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 6,
    backgroundColor: colors.danger + '22',
  },
  modBadgeTxt: { fontFamily: fonts.bold, fontSize: 10, color: colors.danger },
  proBadge: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 6,
    backgroundColor: colors.premium + '22',
  },
  proBadgeTxt: { fontFamily: fonts.bold, fontSize: 10, color: colors.premium },
  replyBox: {
    backgroundColor: colors.bg2,
    borderRadius: 10,
    padding: 8,
    marginBottom: 8,
    borderLeftWidth: 3,
    borderLeftColor: colors.borderStrong,
  },
  replyTxt: { fontSize: 13, fontFamily: fonts.regular },
  msgBody: { fontFamily: fonts.regular, fontSize: 15, lineHeight: 21, color: colors.text },
  time: { alignSelf: 'flex-end', marginTop: 8, fontSize: 11, fontFamily: fonts.regular },
  composer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    paddingBottom: 12,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border,
    backgroundColor: colors.bg,
  },
  circleBtn: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: colors.surface2,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    marginBottom: 2,
  },
  composerField: {
    flex: 1,
    minHeight: 44,
    maxHeight: 120,
    borderRadius: 999,
    paddingHorizontal: 16,
    paddingVertical: 10,
    backgroundColor: colors.inputBg,
    color: colors.text,
    fontFamily: fonts.regular,
    fontSize: 15,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
  },
  inputGate: {
    minHeight: 44,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    borderRadius: 12,
    color: colors.text,
    fontFamily: fonts.regular,
    fontSize: 14,
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginVertical: 12,
    backgroundColor: colors.bg2,
  },
  error: { color: colors.danger, marginBottom: 10 },
  errorBar: { color: colors.danger, paddingHorizontal: 16, marginBottom: 6 },
});

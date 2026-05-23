import * as Clipboard from 'expo-clipboard';
import * as ImagePicker from 'expo-image-picker';
import { useRouter } from 'expo-router';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  type AlertButton,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Share,
  StyleSheet,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Text } from '../components/Text';
import { bottomNavComposerInset } from '../components/BottomNavigationBar';
import { absoluteUrl } from '../config/api';
import { useApp } from '../context/AppContext';
import { ProFeature, ProGate } from '../core/pro/proGate';
import { validateChatMessageInput } from '../features/chat/logic/chatMessageValidation';
import { ChatAmbientBackground } from '../features/chat/components/ChatAmbientBackground';
import { ChatAttachSheet } from '../features/chat/components/ChatAttachSheet';
import { ChatCommunityNotice } from '../features/chat/components/ChatCommunityNotice';
import { ChatComposer } from '../features/chat/components/ChatComposer';
import { ChatFilterBar, type ChatMessageFilter } from '../features/chat/components/ChatFilterBar';
import { ChatContextMenu } from '../features/chat/components/ChatContextMenu';
import { ChatEmojiPickerSheet } from '../features/chat/components/conversation/ChatEmojiPickerSheet';
import { ChatSelectionActions } from '../features/chat/components/conversation/ChatSelectionActions';
import { ChatUserProfileSheet } from '../features/chat/components/conversation/ChatUserProfileSheet';
import { ChatPinnedStrip } from '../features/chat/components/conversation/ChatPinnedStrip';
import { ChatMediaPanel } from '../features/chat/components/conversation/ChatMediaPanel';
import { useChatPrefsStore } from '../features/chat/state/chatPrefsStore';
import { ChatDateDivider } from '../features/chat/components/ChatDateDivider';
import { ChatEmptyState } from '../features/chat/components/ChatEmptyState';
import {
  ChatAgeGate,
  ChatBannedGate,
  ChatNicknameGate,
  ChatRulesGate,
  type GatePrefs,
} from '../features/chat/components/ChatGateViews';
import { ChatImageGallery } from '../features/chat/components/ChatImageGallery';
import { ChatLoadingState } from '../features/chat/components/ChatLoadingState';
import { ChatMessageBubble } from '../features/chat/components/ChatMessageBubble';
import { ChatScrollFab } from '../features/chat/components/ChatScrollFab';
import { ChatSearchHeader } from '../features/chat/components/ChatSearchHeader';
import { ChatTypingIndicator } from '../features/chat/components/ChatTypingIndicator';
import { chatChromeBridge } from '../features/chat/chatChromeBridge';
import { useChatTheme } from '../features/chat/hooks/useChatTheme';
import { useAppTheme, useThemedStyles } from '../theme/useAppTheme';
import { chatService } from '../services/chatService';
import { applySsePayloadToMessages, connectChatSse } from '../services/chatSseService';
import { storage } from '../services/storage';
import type { ChatMessage } from '../types/chat';
import { useChatVoiceAudio } from '../features/chat/hooks/useChatVoiceAudio';

const CHAT_GATE_KEY = 'chat_gate_v2';
const CHAT_BLOCK_KEY = 'chat_block_list';

function dayKey(ts: number): string {
  return new Date(ts).toLocaleDateString('uk-UA', { day: '2-digit', month: 'long' });
}

function sameAuthor(a?: ChatMessage, b?: ChatMessage): boolean {
  return !!a && !!b && a.userId === b.userId && a.deviceId === b.deviceId;
}

function locallyReact(message: ChatMessage, emoji: string, deviceId: string | null, nickname: string | null): ChatMessage {
  const list = message.reactions[emoji] ?? [];
  const mine = list.some((r) => r.deviceId === deviceId || r.nickname === nickname);
  return {
    ...message,
    reactions: {
      ...message.reactions,
      [emoji]: mine
        ? list.filter((r) => r.deviceId !== deviceId && r.nickname !== nickname)
        : [...list, { deviceId: deviceId ?? '', nickname: nickname ?? '', timestamp: Date.now() }],
    },
  };
}

export function ChatConversationScreen() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { nickname, deviceId, setNickname, setOnlineCount, onlineCount, isModerator, refreshIdentity, isPremium } = useApp();

  const requireChatMedia = useCallback((): boolean => {
    if (ProGate.isUnlockedSync(ProFeature.ChatMedia, isPremium)) return true;
    router.push('/premium');
    return false;
  }, [isPremium, router]);
  const { bubbles: bubblePalette } = useChatTheme(isPremium);
  const { theme } = useAppTheme();
  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      root: { flex: 1, backgroundColor: t.chat.bg },
      flex: { flex: 1 },
      messages: { paddingHorizontal: 12, paddingTop: 6, paddingBottom: 10 },
      messagesEmpty: { flexGrow: 1 },
      errorBar: { color: t.chat.danger, paddingHorizontal: 16, paddingTop: 8, fontSize: 13 },
      selectionBar: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingHorizontal: 20,
        paddingVertical: 10,
      },
      selectionTitle: { color: t.chat.text, fontSize: 15, fontWeight: '600' },
      selectionCancel: { color: t.chat.accentSoft, fontSize: 15 },
    }),
  );
  const hydratePrefs = useChatPrefsStore((s) => s.hydrate);
  const pinMessage = useChatPrefsStore((s) => s.pinMessage);
  const unpinMessage = useChatPrefsStore((s) => s.unpinMessage);
  const pinnedMessageIds = useChatPrefsStore((s) => s.pinnedMessageIds);
  const draftText = useChatPrefsStore((s) => s.draft);
  const setDraft = useChatPrefsStore((s) => s.setDraft);
  const clearDraft = useChatPrefsStore((s) => s.clearDraft);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [text, setText] = useState('');
  const [nickInput, setNickInput] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMoreHistory, setHasMoreHistory] = useState(true);
  const [ban, setBan] = useState<{ banned: boolean; reason?: string | null } | null>(null);
  const [sseConnected, setSseConnected] = useState(false);
  const [gate, setGate] = useState<GatePrefs>({ ageConfirmed: false, rulesAgreed: false });
  const [replyTo, setReplyTo] = useState<ChatMessage | null>(null);
  const [editing, setEditing] = useState<ChatMessage | null>(null);
  const [menuMessage, setMenuMessage] = useState<ChatMessage | null>(null);
  const [searchMode, setSearchMode] = useState(false);
  const [search, setSearch] = useState('');
  const [typingUsers, setTypingUsers] = useState<string[]>([]);
  const [isSending, setSending] = useState(false);
  const [recording, setRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [unreadCount, setUnreadCount] = useState(0);
  const [showScrollFab, setShowScrollFab] = useState(false);
  const [blockedUsers, setBlockedUsers] = useState<string[]>([]);
  const [playingVoiceId, setPlayingVoiceId] = useState<string | null>(null);
  const [galleryUrl, setGalleryUrl] = useState<string | null>(null);
  const [messageFilter, setMessageFilter] = useState<ChatMessageFilter>('all');
  const [attachOpen, setAttachOpen] = useState(false);
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [profileUser, setProfileUser] = useState<ChatMessage | null>(null);
  const [emojiOpen, setEmojiOpen] = useState(false);
  const [mediaOpen, setMediaOpen] = useState(false);
  const draftLoaded = useRef(false);

  const listRef = useRef<FlatList<ChatMessage>>(null);
  const typingTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const recordingTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const voiceAudio = useChatVoiceAudio();
  const isAtBottom = useRef(true);

  useEffect(() => {
    void hydratePrefs();
    void storage.getJson<GatePrefs>(CHAT_GATE_KEY, { ageConfirmed: false, rulesAgreed: false }).then(setGate);
    void storage.getJson<string[]>(CHAT_BLOCK_KEY, []).then(setBlockedUsers);
    chatChromeBridge.setSearchHandler(() => setSearchMode((v) => !v));
    chatChromeBridge.setMediaHandler(() => setMediaOpen((v) => !v));
    return () => {
      chatChromeBridge.setSearchHandler(null);
      chatChromeBridge.setMediaHandler(null);
    };
  }, [hydratePrefs]);

  useEffect(() => {
    if (!draftLoaded.current && draftText && !text) {
      draftLoaded.current = true;
      setText(draftText);
    }
  }, [draftText, text]);

  const load = useCallback(async () => {
    try {
      const data = await chatService.fetchMessages();
      const newestFirst = [...data.messages].sort((a, b) => b.timestamp - a.timestamp);
      setMessages(newestFirst);
      setOnlineCount(data.online);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Помилка завантаження');
    } finally {
      setLoading(false);
    }
  }, [setOnlineCount]);

  useEffect(() => {
    if (!nickname) {
      setLoading(false);
      setBan(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    void chatService.checkBanStatus().then((r) => {
      if (!cancelled) setBan(r);
    });
    void load();
    return () => {
      cancelled = true;
    };
  }, [load, nickname]);

  useEffect(() => {
    if (!nickname || ban?.banned) return;
    const ac = new AbortController();
    setSseConnected(false);
    void connectChatSse(
      {
        onPayload(p) {
          if (p.type === 'connected' || p.type === 'online') {
            const online = (p.data as { online?: number } | undefined)?.online;
            if (typeof online === 'number') setOnlineCount(online);
            setSseConnected(true);
          }
          if (p.type === 'typing') {
            const rawUsers = (p.data as { users?: unknown[]; nickname?: string } | undefined)?.users;
            if (Array.isArray(rawUsers)) {
              setTypingUsers(rawUsers.filter((u): u is string => typeof u === 'string' && u !== nickname));
            }
          }
          setMessages((prev) => {
            const next = applySsePayloadToMessages(prev, p).sort((a, b) => b.timestamp - a.timestamp);
            if (p.type === 'new_message' && !isAtBottom.current) {
              setUnreadCount((n) => n + 1);
            }
            return next;
          });
          if (p.type === 'new_message' && isAtBottom.current) {
            requestAnimationFrame(() => listRef.current?.scrollToOffset({ offset: 0, animated: true }));
          }
        },
        onError: () => setSseConnected(false),
      },
      { signal: ac.signal },
    );
    return () => {
      ac.abort();
      setSseConnected(false);
    };
  }, [ban?.banned, nickname, setOnlineCount]);

  useEffect(() => {
    if (!nickname || ban?.banned) return;
    const ms = sseConnected ? 55000 : 12000;
    const id = setInterval(load, ms);
    return () => clearInterval(id);
  }, [ban?.banned, load, nickname, sseConnected]);

  useEffect(() => {
    return () => {
      if (typingTimer.current) clearTimeout(typingTimer.current);
      if (recordingTimer.current) clearInterval(recordingTimer.current);
      void voiceAudio.cancelRecording();
      voiceAudio.stopPlayback();
    };
  }, [voiceAudio]);

  const visibleMessages = useMemo(() => {
    const blocked = new Set(blockedUsers.map((u) => u.trim().toLowerCase()).filter(Boolean));
    return blocked.size ? messages.filter((m) => !blocked.has(m.userId.trim().toLowerCase())) : messages;
  }, [blockedUsers, messages]);

  const filterCounts = useMemo(
    (): Record<ChatMessageFilter, number> => ({
      all: visibleMessages.length,
      media: visibleMessages.filter((m) => m.messageType === 'image').length,
      voice: visibleMessages.filter((m) => m.messageType === 'voice').length,
    }),
    [visibleMessages],
  );

  const filteredMessages = useMemo(() => {
    const q = search.trim().toLowerCase();
    let list = visibleMessages;
    if (messageFilter === 'media') list = list.filter((m) => m.messageType === 'image');
    else if (messageFilter === 'voice') list = list.filter((m) => m.messageType === 'voice');
    if (!q) return list;
    return list.filter((m) => m.message.toLowerCase().includes(q) || m.userId.toLowerCase().includes(q));
  }, [messageFilter, search, visibleMessages]);

  async function persistGate(next: GatePrefs) {
    setGate(next);
    await storage.setJson(CHAT_GATE_KEY, next);
  }

  async function registerNickname() {
    setError(null);
    const nick = nickInput.trim();
    if (nick.length < 2 || nick.length > 20) {
      setError('Від 2 до 20 символів');
      return;
    }
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
    await load();
  }

  function onTypingChanged(value: string) {
    setText(value);
    setDraft(value);
    if (!nickname) return;
    void chatService.sendTyping(value.trim().length > 0);
    if (typingTimer.current) clearTimeout(typingTimer.current);
    typingTimer.current = setTimeout(() => {
      void chatService.sendTyping(false);
    }, 3500);
  }

  async function send() {
    if (isSending) return;
    const validation = validateChatMessageInput(text);
    if (!validation.ok) {
      if (validation.code !== 'empty') setError(validation.message);
      return;
    }
    const trimmed = validation.text;
    setText('');
    clearDraft();
    setSending(true);

    if (editing) {
      const target = editing;
      setEditing(null);
      try {
        const updated = await chatService.editMessage(target.id, trimmed);
        if (updated) setMessages((prev) => prev.map((m) => (m.id === updated.id ? updated : m)));
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Помилка редагування');
        setText(trimmed);
        setEditing(target);
      } finally {
        setSending(false);
      }
      return;
    }

    const pendingId = `pending-${Date.now()}`;
    const optimistic: ChatMessage = {
      id: pendingId,
      userId: nickname || 'Ви',
      deviceId: deviceId || '',
      message: trimmed,
      timestamp: Date.now(),
      isModerator,
      isPro: isPremium,
      replyTo: replyTo
        ? { id: replyTo.id, nickname: replyTo.userId, text: replyTo.message }
        : null,
      reactions: {},
      messageType: 'text',
      editedAt: null,
    };
    const replyId = replyTo?.id;
    setReplyTo(null);
    setMessages((prev) => [optimistic, ...prev]);
    requestAnimationFrame(() => listRef.current?.scrollToOffset({ offset: 0, animated: true }));
    try {
      const sent = await chatService.sendMessage(trimmed, replyId);
      setMessages((prev) =>
        [sent, ...prev.filter((m) => m.id !== pendingId && m.id !== sent.id)].sort((a, b) => b.timestamp - a.timestamp),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Повідомлення збережено як pending');
    } finally {
      setSending(false);
    }
  }

  async function loadMore() {
    if (loadingMore || !hasMoreHistory || messages.length === 0) return;
    setLoadingMore(true);
    const oldest = messages[messages.length - 1];
    const beforeSec = oldest.timestamp < 10000000000 ? oldest.timestamp : Math.round(oldest.timestamp / 1000);
    try {
      const older = await chatService.fetchMoreMessages(beforeSec);
      const unique = older.filter((m) => !messages.some((x) => x.id === m.id));
      setMessages((prev) => [...prev, ...unique].sort((a, b) => b.timestamp - a.timestamp));
      if (unique.length < 50) setHasMoreHistory(false);
    } finally {
      setLoadingMore(false);
    }
  }

  async function startRecording() {
    if (!requireChatMedia()) return;
    try {
      await voiceAudio.startRecording();
      setRecording(true);
      setRecordingSeconds(0);
      if (recordingTimer.current) clearInterval(recordingTimer.current);
      recordingTimer.current = setInterval(() => {
        setRecordingSeconds((s) => {
          const next = Math.min(60, s + 1);
          if (next >= 60) void stopRecording();
          return next;
        });
      }, 1000);
    } catch (e) {
      setRecording(false);
      setError(e instanceof Error ? e.message : 'Не вдалося почати запис');
    }
  }

  async function stopRecording() {
    const duration = recordingSeconds;
    if (recordingTimer.current) clearInterval(recordingTimer.current);
    setRecording(false);
    setRecordingSeconds(0);
    try {
      const uri = await voiceAudio.stopRecording();
      if (!uri || duration < 1) return;
      setSending(true);
      const sent = await chatService.sendVoiceMessage(
        { uri, name: `voice_${Date.now()}.m4a`, type: 'audio/m4a' },
        duration,
      );
      setMessages((prev) => [sent, ...prev.filter((m) => m.id !== sent.id)].sort((a, b) => b.timestamp - a.timestamp));
      requestAnimationFrame(() => listRef.current?.scrollToOffset({ offset: 0, animated: true }));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Помилка відправки голосового');
    } finally {
      setSending(false);
    }
  }

  function cancelRecording() {
    if (recordingTimer.current) clearInterval(recordingTimer.current);
    void voiceAudio.cancelRecording();
    setRecording(false);
    setRecordingSeconds(0);
  }

  async function attachImage(source: 'library' | 'camera') {
    try {
      const permission =
        source === 'camera'
          ? await ImagePicker.requestCameraPermissionsAsync()
          : await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!permission.granted) {
        setError(source === 'camera' ? 'Немає дозволу на камеру' : 'Немає дозволу на галерею');
        return;
      }
      const result =
        source === 'camera'
          ? await ImagePicker.launchCameraAsync({ mediaTypes: ['images'], quality: 0.85, allowsEditing: false })
          : await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 0.85, allowsEditing: false });
      if (result.canceled || !result.assets[0]) return;
      const asset = result.assets[0];
      const caption = text.trim();
      if (caption) setText('');
      setSending(true);
      const sent = await chatService.sendImageMessage(
        { uri: asset.uri, name: asset.fileName || `chat_img_${Date.now()}.jpg`, type: asset.mimeType || 'image/jpeg' },
        caption || null,
      );
      setMessages((prev) => [sent, ...prev.filter((m) => m.id !== sent.id)].sort((a, b) => b.timestamp - a.timestamp));
      requestAnimationFrame(() => listRef.current?.scrollToOffset({ offset: 0, animated: true }));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Помилка відправки фото');
    } finally {
      setSending(false);
    }
  }

  function openAttachSheet() {
    if (!requireChatMedia()) return;
    setAttachOpen(true);
  }

  async function playVoice(message: ChatMessage) {
    if (!message.audioUrl) return;
    try {
      if (playingVoiceId === message.id) {
        voiceAudio.stopPlayback();
        setPlayingVoiceId(null);
        return;
      }
      voiceAudio.stopPlayback();
      setPlayingVoiceId(message.id);
      await voiceAudio.playUrl(absoluteUrl(message.audioUrl), () => setPlayingVoiceId(null));
    } catch (e) {
      setPlayingVoiceId(null);
      setError(e instanceof Error ? e.message : 'Не вдалося відтворити голосове');
    }
  }

  async function copyMessage(message: ChatMessage) {
    await Clipboard.setStringAsync(message.message);
  }

  async function blockUser(message: ChatMessage) {
    const key = message.userId.trim().toLowerCase();
    if (!key) return;
    const next = Array.from(new Set([...blockedUsers, key]));
    setBlockedUsers(next);
    await storage.setJson(CHAT_BLOCK_KEY, next);
  }

  async function banUser(message: ChatMessage) {
    try {
      await chatService.banUser(message);
      setMessages((prev) => prev.filter((m) => m.deviceId !== message.deviceId && m.userId !== message.userId));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Помилка блокування');
    }
  }

  async function deleteAllUserMessages(message: ChatMessage) {
    try {
      const deleted = await chatService.deleteAllUserMessages(message);
      if (deleted == null) {
        setError('Потрібен moderator secret для видалення всіх повідомлень');
        return;
      }
      setMessages((prev) => prev.filter((m) => m.deviceId !== message.deviceId && m.userId !== message.userId));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Помилка масового видалення');
    }
  }

  function reportMessage(message: ChatMessage) {
    const actions: AlertButton[] = ['Спам', 'Образи', 'Небезпечний контент', 'Інше'].map((reason) => ({
      text: reason,
      onPress: () => {
        void chatService.reportMessage(message.id, reason, {
          reportedDeviceId: message.deviceId,
          reportedNickname: message.userId,
          originalText: message.message,
        });
      },
    }));
    actions.push({ text: 'Скасувати', style: 'cancel' });
    Alert.alert('Поскаржитись', 'Оберіть причину скарги:', actions);
  }

  function onScroll(offset: number) {
    const bottom = offset < 80;
    isAtBottom.current = bottom;
    setShowScrollFab(!bottom);
    if (bottom) setUnreadCount(0);
  }

  const selectedMessages = filteredMessages.filter((m) => selectedIds.has(m.id));
  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  async function forwardSelected() {
    const body = selectedMessages.map((m) => `${m.userId}: ${m.message}`).join('\n\n');
    await Share.share({ message: body || ' ' });
    setSelectionMode(false);
    setSelectedIds(new Set());
  }

  async function copySelected() {
    await Clipboard.setStringAsync(selectedMessages.map((m) => m.message).join('\n'));
    setSelectionMode(false);
    setSelectedIds(new Set());
  }

  function pinSelected() {
    for (const m of selectedMessages) pinMessage(m.id);
    Alert.alert('NEPTUN', 'Повідомлення закріплено локально');
    setSelectionMode(false);
    setSelectedIds(new Set());
  }

  async function deleteSelected() {
    for (const m of selectedMessages) {
      if (m.deviceId === deviceId || isModerator) {
        setMessages((prev) => prev.filter((x) => x.id !== m.id));
        await chatService.deleteMessage(m.id).catch(() => undefined);
      }
    }
    setSelectionMode(false);
    setSelectedIds(new Set());
  }

  if (loading) return <ChatLoadingState />;
  if (!gate.ageConfirmed) return <ChatAgeGate gate={gate} onCommit={persistGate} />;
  if (!nickname) {
    return (
      <ChatNicknameGate nickInput={nickInput} error={error} onChangeNick={setNickInput} onSubmit={() => void registerNickname()} />
    );
  }
  if (!gate.rulesAgreed) return <ChatRulesGate onAgree={() => void persistGate({ ...gate, rulesAgreed: true })} />;
  if (ban?.banned) return <ChatBannedGate reason={ban.reason} onCheck={() => void load()} />;

  const showEmpty = filteredMessages.length === 0;

  return (
    <View style={styles.root}>
      <ChatAmbientBackground />
      {selectionMode ? (
        <View style={styles.selectionBar}>
          <Text style={styles.selectionTitle}>{selectedIds.size} обрано</Text>
          <Text style={styles.selectionCancel} onPress={() => { setSelectionMode(false); setSelectedIds(new Set()); }}>
            Скасувати
          </Text>
        </View>
      ) : null}
      {searchMode ? (
        <ChatSearchHeader
          topInset={0}
          search={search}
          matchCount={filteredMessages.length}
          totalCount={messages.length}
          onChangeSearch={setSearch}
          onClose={() => {
            setSearchMode(false);
            setSearch('');
          }}
        />
      ) : null}

      <KeyboardAvoidingView style={styles.flex} behavior={Platform.select({ ios: 'padding', android: undefined })}>
        {!searchMode && !selectionMode ? (
          <>
            <ChatPinnedStrip
              messages={messages}
              pinnedIds={pinnedMessageIds}
              onPressMessage={(m) => setReplyTo(m)}
              onUnpin={unpinMessage}
            />
            <ChatFilterBar active={messageFilter} counts={filterCounts} onChange={setMessageFilter} />
            <ChatCommunityNotice />
          </>
        ) : null}
        {selectionMode ? (
          <ChatSelectionActions
            canDelete={selectedMessages.every((m) => m.deviceId === deviceId || isModerator)}
            onCopy={() => void copySelected()}
            onForward={() => void forwardSelected()}
            onPin={pinSelected}
            onDelete={() => void deleteSelected()}
          />
        ) : null}
        {error ? <Text style={styles.errorBar}>{error}</Text> : null}
        <FlatList
          ref={listRef}
          inverted
          data={filteredMessages}
          keyExtractor={(item) => item.id}
          keyboardDismissMode="interactive"
          keyboardShouldPersistTaps="handled"
          removeClippedSubviews={Platform.OS === 'android'}
          initialNumToRender={18}
          maxToRenderPerBatch={12}
          windowSize={9}
          contentContainerStyle={[styles.messages, showEmpty && styles.messagesEmpty]}
          onEndReached={loadMore}
          onEndReachedThreshold={0.12}
          onScroll={(event) => onScroll(event.nativeEvent.contentOffset.y)}
          scrollEventThrottle={16}
          ListEmptyComponent={
            showEmpty ? (
              search.trim() || messageFilter !== 'all' ? (
                <ChatEmptyState
                  variant={search.trim() ? 'search' : 'filter'}
                  query={search.trim()}
                  filterLabel={
                    messageFilter === 'media' ? 'Медіа' : messageFilter === 'voice' ? 'Голос' : undefined
                  }
                />
              ) : (
                <ChatEmptyState variant="idle" />
              )
            ) : null
          }
          ListFooterComponent={loadingMore ? <ActivityIndicator color={theme.chat.accent} style={{ margin: 18 }} /> : null}
          renderItem={({ item, index }) => {
            const previous = filteredMessages[index + 1];
            const next = filteredMessages[index - 1];
            const firstInGroup = !sameAuthor(item, previous);
            const lastInGroup = !sameAuthor(item, next);
            const showDate = !previous || dayKey(previous.timestamp) !== dayKey(item.timestamp);
            return (
              <View>
                <ChatMessageBubble
                  message={item}
                  isMine={!!deviceId && item.deviceId === deviceId}
                  firstInGroup={firstInGroup}
                  lastInGroup={lastInGroup}
                  pending={item.id.startsWith('pending-')}
                  palette={bubblePalette}
                  selected={selectionMode && selectedIds.has(item.id)}
                  onReply={() => setReplyTo(item)}
                  onMenu={() => setMenuMessage(item)}
                  onPress={() => {
                    if (selectionMode) toggleSelect(item.id);
                  }}
                  onAvatarPress={() => setProfileUser(item)}
                  onPlayVoice={() => void playVoice(item)}
                  isPlayingVoice={playingVoiceId === item.id}
                  onImagePress={(url) => setGalleryUrl(url)}
                  animIndex={index}
                />
                {showDate ? <ChatDateDivider label={dayKey(item.timestamp)} /> : null}
              </View>
            );
          }}
        />

        {typingUsers.length ? <ChatTypingIndicator users={typingUsers} /> : null}
        {!selectionMode ? (
          <ChatComposer
            text={text}
            replyTo={replyTo}
            editing={editing}
            isSending={isSending}
            recording={recording}
            recordingSeconds={recordingSeconds}
            bottomInset={bottomNavComposerInset(insets.bottom)}
            onChangeText={onTypingChanged}
            onSend={() => void send()}
            onStartRecording={startRecording}
            onStopRecording={stopRecording}
            onCancelRecording={cancelRecording}
            onAttach={openAttachSheet}
            onDismissReply={() => setReplyTo(null)}
            onDismissEdit={() => setEditing(null)}
          />
        ) : null}
      </KeyboardAvoidingView>

      {showScrollFab ? (
        <ChatScrollFab
          bottom={insets.bottom + 96}
          unreadCount={unreadCount}
          onPress={() => {
            listRef.current?.scrollToOffset({ offset: 0, animated: true });
            setUnreadCount(0);
          }}
        />
      ) : null}

      <ChatAttachSheet
        visible={attachOpen}
        onClose={() => setAttachOpen(false)}
        onPickLibrary={() => void attachImage('library')}
        onPickCamera={() => void attachImage('camera')}
      />

      <ChatImageGallery visible={!!galleryUrl} imageUrl={galleryUrl ?? ''} onClose={() => setGalleryUrl(null)} />

      <ChatContextMenu
        message={menuMessage}
        isMine={!!menuMessage && !!deviceId && menuMessage.deviceId === deviceId}
        isModerator={isModerator}
        onClose={() => setMenuMessage(null)}
        onReply={(m) => setReplyTo(m)}
        onEdit={(m) => {
          setEditing(m);
          setText(m.message);
        }}
        onPin={(m) => {
          pinMessage(m.id);
          Alert.alert('NEPTUN', 'Повідомлення закріплено');
        }}
        onForward={(m) => void Share.share({ message: `${m.userId}: ${m.message}` })}
        onSelect={(m) => {
          setSelectionMode(true);
          setSelectedIds(new Set([m.id]));
        }}
        onReact={(m, emoji) => {
          setMessages((prev) => prev.map((x) => (x.id === m.id ? locallyReact(x, emoji, deviceId, nickname) : x)));
          void chatService.react(m.id, emoji).catch((e) => setError(e instanceof Error ? e.message : 'Помилка реакції'));
        }}
        onDelete={(m) => {
          setMessages((prev) => prev.filter((x) => x.id !== m.id));
          void chatService.deleteMessage(m.id).catch((e) => setError(e instanceof Error ? e.message : 'Помилка видалення'));
        }}
        onCopy={(m) => void copyMessage(m)}
        onReport={reportMessage}
        onBlock={(m) => void blockUser(m)}
        onBan={(m) => void banUser(m)}
        onDeleteAll={(m) => void deleteAllUserMessages(m)}
      />

      <ChatMediaPanel
        visible={mediaOpen}
        messages={messages}
        onClose={() => setMediaOpen(false)}
        onOpenImage={(url) => {
          setMediaOpen(false);
          setGalleryUrl(url);
        }}
      />

      <ChatEmojiPickerSheet
        visible={emojiOpen}
        onClose={() => setEmojiOpen(false)}
        onPick={(emoji) => setText((t) => `${t}${emoji}`)}
      />

      <ChatUserProfileSheet
        visible={!!profileUser}
        nickname={profileUser?.userId ?? ''}
        isModerator={profileUser?.isModerator}
        isPro={profileUser?.isPro}
        onClose={() => setProfileUser(null)}
        onMention={
          profileUser
            ? () => {
                setText((t) => `${t}@${profileUser.userId} `);
                setProfileUser(null);
              }
            : undefined
        }
        onBlock={
          profileUser
            ? () => {
                void blockUser(profileUser);
                setProfileUser(null);
              }
            : undefined
        }
        onReport={
          profileUser
            ? () => {
                reportMessage(profileUser);
                setProfileUser(null);
              }
            : undefined
        }
      />
    </View>
  );
}


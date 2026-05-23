import { Ionicons } from '@expo/vector-icons';
import { useMemo, useRef } from 'react';
import {
  Animated,
  Image,
  PanResponder,
  Pressable,
  StyleSheet,
  View,
  type ImageStyle,
  type TextStyle,
  type ViewStyle,
} from 'react-native';
import { absoluteUrl } from '../../../config/api';
import { Text } from '../../../components/Text';
import { ChatRichText } from './ChatRichText';
import { fonts } from '../../../theme/fonts';
import type { ChatMessage } from '../../../types/chat';
import { avatarAccent, avatarInitialsColor, chatPeerBubbleColor, displayInitials } from '../../../utils/avatarPalette';
import type { ChatBubblePalette } from '../theme/chatTokens';
import { getChatTokens } from '../theme/chatTokens';
import { useAppTheme, useThemedStyles } from '../../../theme/useAppTheme';

type Props = {
  message: ChatMessage;
  isMine: boolean;
  firstInGroup: boolean;
  lastInGroup: boolean;
  pending: boolean;
  palette: ChatBubblePalette;
  onReply: () => void;
  onMenu: () => void;
  onPress?: () => void;
  onAvatarPress?: () => void;
  selected?: boolean;
  onPlayVoice: () => void;
  isPlayingVoice: boolean;
  onImagePress: (url: string) => void;
  /** Stagger list entrance (unused — native lists skip enter animation). */
  animIndex?: number;
};

export function ChatMessageBubble({
  message,
  isMine,
  firstInGroup,
  lastInGroup,
  pending,
  palette: colors,
  onReply,
  onMenu,
  onPress,
  onAvatarPress,
  selected,
  onPlayVoice,
  isPlayingVoice,
  onImagePress,
  animIndex: _animIndex = 0,
}: Props) {
  const { theme } = useAppTheme();
  const chat = getChatTokens();
  const styles = useThemedStyles((t) => {
    const ch = getChatTokens();
    return StyleSheet.create({
      outer: { position: 'relative' },
      outerSelected: {
        backgroundColor: ch.accentMuted,
        borderRadius: 12,
        marginHorizontal: 4,
      },
      row: { flexDirection: 'row', alignItems: 'flex-end' },
      rowMine: { justifyContent: 'flex-end', paddingLeft: 40, paddingRight: 2 },
      rowPeer: { justifyContent: 'flex-start', paddingLeft: 2, paddingRight: 40 },
      replyHint: {
        position: 'absolute',
        top: 14,
        width: 28,
        height: 28,
        borderRadius: 14,
        backgroundColor: ch.surfaceInput,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: ch.border,
        alignItems: 'center',
        justifyContent: 'center',
      },
      replyHintMine: { right: 8 },
      replyHintPeer: { left: 36 },
      avatar: {
        width: ch.avatarSize,
        height: ch.avatarSize,
        borderRadius: ch.avatarSize / 2,
        alignItems: 'center',
        justifyContent: 'center',
        marginRight: 8,
      },
      proDot: {
        position: 'absolute',
        bottom: -1,
        right: -1,
        width: 12,
        height: 12,
        borderRadius: 6,
        backgroundColor: ch.bg,
        alignItems: 'center',
        justifyContent: 'center',
      },
      avatarGap: { width: ch.avatarGap },
      avatarText: { fontFamily: fonts.semiBold, fontSize: 11 },
      bubble: {
        maxWidth: ch.bubbleMaxWidth,
        paddingHorizontal: ch.messagePadH,
        paddingTop: ch.messagePadV,
        paddingBottom: 5,
        overflow: 'hidden',
      },
      senderRow: { flexDirection: 'row', alignItems: 'center', gap: 4, marginBottom: 2 },
      sender: { fontFamily: fonts.semiBold, fontSize: 11 },
      replyBox: { borderLeftWidth: 2, borderRadius: 4, padding: 6, marginBottom: 4 },
      replyName: { fontFamily: fonts.semiBold, fontSize: 10 },
      replyText: { fontSize: 11, marginTop: 1, lineHeight: 14 },
      bodyText: { fontFamily: fonts.regular, fontSize: 15, lineHeight: 20 },
      image: { width: 220, height: 160, borderRadius: 14, backgroundColor: ch.surfaceInput },
      voiceRow: { minWidth: 160, flexDirection: 'row', alignItems: 'center', gap: 8 },
      voicePlay: {
        width: 30,
        height: 30,
        borderRadius: 15,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: t.scheme === 'light' ? 'rgba(15,23,42,0.06)' : 'rgba(255,255,255,0.1)',
      },
      voicePlayActive: {
        backgroundColor: t.scheme === 'light' ? 'rgba(15,23,42,0.1)' : 'rgba(255,255,255,0.16)',
      },
      voiceBars: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 2, height: 22 },
      voiceBar: { width: 2, borderRadius: 1 },
      voiceDur: { fontSize: 10, fontFamily: fonts.medium },
      footer: { flexDirection: 'row', alignItems: 'center', alignSelf: 'flex-end', marginTop: 2, gap: 2 },
      time: { fontSize: 10, fontFamily: fonts.regular },
      reactionsFloat: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        gap: 4,
        marginTop: 2,
        marginBottom: 4,
      },
      reactionsFloatMine: {
        alignSelf: 'flex-end',
        marginRight: 6,
        justifyContent: 'flex-end',
      },
      reactionsFloatPeer: {
        alignSelf: 'flex-start',
        marginLeft: ch.avatarGap,
      },
      reactionPill: {
        paddingHorizontal: 9,
        paddingVertical: 4,
        borderRadius: 14,
        backgroundColor: t.scheme === 'dark' ? '#1C1C1E' : '#FFFFFF',
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.scheme === 'dark' ? 'rgba(255,255,255,0.08)' : t.colors.border,
      },
      reactionText: { fontSize: 11, fontFamily: fonts.medium },
    });
  });
  const drag = useRef(new Animated.Value(0)).current;

  const panResponder = useMemo(
    () =>
      PanResponder.create({
        onMoveShouldSetPanResponder: (_, g) => Math.abs(g.dx) > 12 && Math.abs(g.dx) > Math.abs(g.dy),
        onPanResponderMove: (_, g) => {
          drag.setValue(Math.max(0, Math.min(72, isMine ? -g.dx : g.dx)));
        },
        onPanResponderRelease: (_, g) => {
          if (Math.max(0, isMine ? -g.dx : g.dx) > 54) onReply();
          Animated.spring(drag, { toValue: 0, useNativeDriver: true, friction: 8 }).start();
        },
      }),
    [drag, isMine, onReply],
  );

  const radiiStyle = bubbleRadii(chat, isMine, firstInGroup, lastInGroup);
  const textColor = isMine ? colors.mineText : colors.peerText;
  const metaColor = isMine ? colors.mineMeta : colors.peerMeta;
  const userAccent = avatarAccent(message.userId);
  const peerBubbleBg = chatPeerBubbleColor(message.userId, theme.scheme === 'light');

  const inner = (
    <BubbleInner
      message={message}
      isMine={isMine}
      pending={pending}
      colors={colors}
      styles={styles}
      textColor={textColor}
      metaColor={metaColor}
      senderColor={userAccent}
      isPlayingVoice={isPlayingVoice}
      onPlayVoice={onPlayVoice}
      onImagePress={onImagePress}
      showSender={!isMine && firstInGroup}
    />
  );

  const bubbleShell = isMine ? (
    <Pressable
      onLongPress={onMenu}
      onPress={onPress}
      style={[
        styles.bubble,
        radiiStyle,
        theme.chat.shadowBubble,
        { backgroundColor: colors.mineGradient[0] },
      ]}
    >
      {inner}
    </Pressable>
  ) : (
    <Pressable
      onLongPress={onMenu}
      onPress={onPress}
      style={[styles.bubble, radiiStyle, { backgroundColor: peerBubbleBg }]}
    >
      {inner}
    </Pressable>
  );

  const avatar = firstInGroup ? (
    <Pressable onPress={onAvatarPress} disabled={!onAvatarPress}>
      <View style={[styles.avatar, { backgroundColor: userAccent }]}>
        <Text style={[styles.avatarText, { color: avatarInitialsColor(message.userId) }]}>
          {displayInitials(message.userId)}
        </Text>
        {message.isPro ? (
          <View style={styles.proDot}>
            <Ionicons name="star" size={7} color={chat.premium} />
          </View>
        ) : null}
      </View>
    </Pressable>
  ) : (
    <View style={styles.avatarGap} />
  );

  return (
    <View
      accessibilityRole="text"
      accessibilityLabel={`${isMine ? 'Ви' : message.userId}: ${message.message}`}
      style={[
        styles.outer,
        { paddingTop: firstInGroup ? 10 : 2, paddingBottom: lastInGroup ? 8 : 1 },
        selected && styles.outerSelected,
      ]}
    >
      <Animated.View
        style={[
          styles.replyHint,
          isMine ? styles.replyHintMine : styles.replyHintPeer,
          {
            opacity: drag.interpolate({ inputRange: [0, 54, 72], outputRange: [0, 0.85, 1] }),
            transform: [{ scale: drag.interpolate({ inputRange: [0, 54, 72], outputRange: [0.8, 1, 1.05] }) }],
          },
        ]}
        pointerEvents="none"
      >
        <Ionicons name="arrow-undo" size={17} color={theme.chat.text} />
      </Animated.View>
      <Animated.View
        {...panResponder.panHandlers}
        style={[
          styles.row,
          isMine ? styles.rowMine : styles.rowPeer,
          { transform: [{ translateX: drag.interpolate({ inputRange: [0, 72], outputRange: [0, isMine ? -72 : 72] }) }] },
        ]}
      >
        {!isMine ? avatar : null}
        {bubbleShell}
      </Animated.View>
      <ReactionRow message={message} isMine={isMine} styles={styles} />
    </View>
  );
}

type BubbleStyles = Record<string, ViewStyle | TextStyle | ImageStyle>;

function BubbleInner({
  message,
  isMine,
  pending,
  colors,
  styles,
  textColor,
  metaColor,
  senderColor,
  isPlayingVoice,
  onPlayVoice,
  onImagePress,
  showSender,
}: {
  message: ChatMessage;
  isMine: boolean;
  pending: boolean;
  colors: ChatBubblePalette;
  styles: BubbleStyles;
  textColor: string;
  metaColor: string;
  senderColor: string;
  isPlayingVoice: boolean;
  onPlayVoice: () => void;
  onImagePress: (url: string) => void;
  showSender: boolean;
}) {
  return (
    <>
      {showSender ? (
        <View style={styles.senderRow}>
          <Text style={[styles.sender, { color: senderColor }]}>{message.userId}</Text>
          {message.isModerator ? <Ionicons name="shield-checkmark" size={11} color={colors.peerMeta} /> : null}
        </View>
      ) : null}
      {message.replyTo ? (
        <View
          style={[
            styles.replyBox,
            {
              borderLeftColor: isMine ? colors.mineReplyBorder : senderColor,
              backgroundColor: isMine ? colors.mineReplyBg : colors.peerReplyBg,
            },
          ]}
        >
          <Text style={[styles.replyName, { color: isMine ? colors.mineReplyBorder : senderColor }]}>
            {message.replyTo.nickname || 'Відповідь'}
          </Text>
          <Text numberOfLines={2} style={[styles.replyText, { color: isMine ? colors.mineReplyText : colors.peerMeta }]}>
            {message.replyTo.text}
          </Text>
        </View>
      ) : null}
      <MessageBody
        message={message}
        styles={styles}
        colors={colors}
        textColor={textColor}
        isMine={isMine}
        metaColor={metaColor}
        isPlayingVoice={isPlayingVoice}
        onPlayVoice={onPlayVoice}
        onImagePress={onImagePress}
      />
      <View style={styles.footer}>
        {message.editedAt ? <Text style={[styles.time, { color: metaColor }]}>ред. </Text> : null}
        <Text style={[styles.time, { color: metaColor }]}>{formatClock(message.timestamp)}</Text>
        {isMine ? (
          <Ionicons name={pending ? 'time-outline' : 'checkmark-done'} size={12} color={metaColor} style={{ marginLeft: 2 }} />
        ) : null}
      </View>
    </>
  );
}

function bubbleRadii(
  chat: ReturnType<typeof getChatTokens>,
  isMine: boolean,
  first: boolean,
  last: boolean,
): ViewStyle {
  const r = chat.radiusBubble;
  const t = chat.radiusBubbleTail;
  if (isMine) {
    return {
      borderTopLeftRadius: r,
      borderTopRightRadius: first ? r : 6,
      borderBottomLeftRadius: r,
      borderBottomRightRadius: last ? t : 6,
    };
  }
  return {
    borderTopLeftRadius: first ? r : 6,
    borderTopRightRadius: r,
    borderBottomLeftRadius: last ? t : 6,
    borderBottomRightRadius: r,
  };
}

function MessageBody({
  message,
  styles,
  colors,
  textColor,
  isMine,
  metaColor,
  isPlayingVoice,
  onPlayVoice,
  onImagePress,
}: {
  message: ChatMessage;
  styles: BubbleStyles;
  colors: ChatBubblePalette;
  textColor: string;
  isMine: boolean;
  metaColor: string;
  isPlayingVoice: boolean;
  onPlayVoice: () => void;
  onImagePress: (url: string) => void;
}) {
  if (message.messageType === 'image' && message.imageUrl) {
    const url = absoluteUrl(message.imageUrl);
    return (
      <View>
        <Pressable onPress={() => onImagePress(url)}>
          <Image source={{ uri: url }} style={styles.image as ImageStyle} resizeMode="cover" />
        </Pressable>
        {message.message && message.message !== '🖼 Фото' ? (
          <Text style={[styles.bodyText, { color: textColor, marginTop: 8 }]}>{message.message}</Text>
        ) : null}
      </View>
    );
  }
  if (message.messageType === 'voice' && message.audioUrl) {
    const duration = message.audioDuration
      ? `${Math.floor(message.audioDuration / 60)}:${String(message.audioDuration % 60).padStart(2, '0')}`
      : '0:00';
    return (
      <Pressable onPress={onPlayVoice} style={styles.voiceRow}>
        <View style={[styles.voicePlay, isPlayingVoice && styles.voicePlayActive]}>
          <Ionicons name={isPlayingVoice ? 'pause' : 'play'} size={14} color={textColor} />
        </View>
        <View style={styles.voiceBars}>
          {Array.from({ length: 16 }).map((_, i) => (
            <View
              key={i}
              style={[
                styles.voiceBar,
                {
                  height: 6 + ((i * 5) % 18),
                  backgroundColor: isMine ? colors.mineMeta : colors.peerReplyBg,
                },
              ]}
            />
          ))}
        </View>
        <Text style={[styles.voiceDur, { color: metaColor }]}>{duration}</Text>
      </Pressable>
    );
  }
  return <ChatRichText text={message.message} color={textColor} style={styles.bodyText} />;
}

function ReactionRow({
  message,
  isMine,
  styles,
}: {
  message: ChatMessage;
  isMine: boolean;
  styles: BubbleStyles;
}) {
  const { theme } = useAppTheme();
  const entries = Object.entries(message.reactions).filter(([, list]) => list.length > 0);
  if (!entries.length) return null;
  return (
    <View style={[styles.reactionsFloat, isMine ? styles.reactionsFloatMine : styles.reactionsFloatPeer]}>
      {entries.map(([emoji, list]) => (
        <View key={emoji} style={styles.reactionPill}>
          <Text style={[styles.reactionText, { color: theme.chat.text }]}>
            {emoji} {list.length}
          </Text>
        </View>
      ))}
    </View>
  );
}

function formatClock(ts: number): string {
  const d = new Date(ts);
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}


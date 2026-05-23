import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, View } from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { Text } from '../../../components/Text';
import { fonts } from '../../../theme/fonts';
import { chat } from '../theme/chatTokens';

type Props = {
  onlineCount: number;
  live: boolean;
  nickname: string | null;
  /** Hides pinned rules when user scrolls the thread. */
  compact?: boolean;
};

/** Single-room “conversation header” — online, live, identity. */
export function ChatRoomHeader({ onlineCount, live, nickname, compact = false }: Props) {
  return (
    <Animated.View entering={FadeInDown.duration(320).springify().damping(22)} style={[styles.wrap, compact && styles.wrapCompact]}>
      <View style={styles.card}>
        <View style={styles.avatar}>
          <Ionicons name="people" size={22} color={chat.accentSoft} />
        </View>
        <View style={styles.body}>
          <Text style={styles.title}>Спільнота NEPTUN</Text>
          <Text muted style={styles.sub}>
            {nickname ? `Ви: ${nickname}` : 'Анонімний чат підтримки'}
          </Text>
        </View>
        <View style={styles.meta}>
          {live ? (
            <View style={styles.livePill}>
              <View style={styles.liveDot} />
              <Text style={styles.liveText}>Live</Text>
            </View>
          ) : (
            <View style={styles.syncPill}>
              <Ionicons name="cloud-offline-outline" size={12} color={chat.textMuted} />
            </View>
          )}
          {onlineCount > 0 ? (
            <View style={styles.onlinePill}>
              <Text style={styles.onlineText}>{onlineCount}</Text>
              <Text style={styles.onlineLabel}>онлайн</Text>
            </View>
          ) : null}
        </View>
      </View>
      {!compact ? (
        <Animated.View entering={FadeInDown.duration(200)} style={styles.pinned}>
          <Ionicons name="pin" size={14} color={chat.accentSoft} />
          <Text muted style={styles.pinnedText} numberOfLines={2}>
            Правила: ввічливість, без спаму, мату та реклами. Довге натискання — меню повідомлення.
          </Text>
        </Animated.View>
      ) : null}
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    paddingHorizontal: chat.listPadH + 4,
    paddingTop: 6,
    paddingBottom: 4,
    gap: 8,
  },
  wrapCompact: {
    paddingBottom: 2,
    gap: 4,
  },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 12,
    borderRadius: chat.radiusGate,
    backgroundColor: chat.surfaceGlass,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: chat.borderStrong,
  },
  avatar: {
    width: 44,
    height: 44,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: chat.accentMuted,
  },
  body: { flex: 1, minWidth: 0 },
  title: { fontFamily: fonts.bold, fontSize: 15, color: chat.text },
  sub: { fontSize: 12, marginTop: 2 },
  meta: { alignItems: 'flex-end', gap: 6 },
  livePill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: chat.radiusPill,
    backgroundColor: 'rgba(61, 214, 140, 0.12)',
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: 'rgba(61, 214, 140, 0.28)',
  },
  liveDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: chat.success,
  },
  liveText: {
    fontFamily: fonts.bold,
    fontSize: 10,
    color: chat.success,
    letterSpacing: 0.4,
  },
  syncPill: {
    width: 28,
    height: 24,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(255,255,255,0.05)',
  },
  onlinePill: {
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.05)',
  },
  onlineText: { fontFamily: fonts.bold, fontSize: 13, color: chat.text },
  onlineLabel: { fontSize: 9, color: chat.textMuted, marginTop: 1 },
  pinned: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 14,
    backgroundColor: 'rgba(255,255,255,0.03)',
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: chat.border,
  },
  pinnedText: { flex: 1, fontSize: 12, lineHeight: 17 },
});

import { Ionicons } from '@expo/vector-icons';
import { ScrollView, StyleSheet, View } from 'react-native';
import { Text } from '../../../../components/Text';
import { NeptunPressable } from '../../../../design/components/NeptunPressable';
import { fonts } from '../../../../theme/fonts';
import type { ChatMessage } from '../../../../types/chat';
import { avatarAccent } from '../../../../utils/avatarPalette';
import { useThemedStyles } from '../../../../theme/useAppTheme';

type Props = {
  messages: ChatMessage[];
  pinnedIds: string[];
  onPressMessage: (message: ChatMessage) => void;
  onUnpin: (id: string) => void;
};

export function ChatPinnedStrip({ messages, pinnedIds, onPressMessage, onUnpin }: Props) {
  const styles = usePinnedStyles();
  const pinned = pinnedIds
    .map((id) => messages.find((m) => m.id === id))
    .filter((m): m is ChatMessage => !!m)
    .slice(0, 6);
  if (!pinned.length) return null;

  return (
    <View style={styles.wrap}>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.scroll}>
        {pinned.map((m) => (
          <NeptunPressable key={m.id} haptic onPress={() => onPressMessage(m)} style={styles.chip}>
            <Text numberOfLines={1} style={[styles.chipAuthor, { color: avatarAccent(m.userId) }]}>
              {m.userId}
            </Text>
            <Text numberOfLines={2} style={styles.chipText}>
              {m.messageType === 'image' ? '📷 Фото' : m.messageType === 'voice' ? '🎤 Голос' : m.message}
            </Text>
            <NeptunPressable haptic onPress={() => onUnpin(m.id)} style={styles.unpin}>
              <Ionicons name="close" size={14} color={styles.mutedColor.color} />
            </NeptunPressable>
          </NeptunPressable>
        ))}
      </ScrollView>
    </View>
  );
}

function usePinnedStyles() {
  return useThemedStyles((t) => {
    const isDark = t.scheme === 'dark';
    return StyleSheet.create({
      wrap: {
        paddingBottom: 6,
        backgroundColor: 'transparent',
      },
      scroll: { paddingHorizontal: 12, paddingVertical: 6, gap: 8 },
      chip: {
        width: 160,
        padding: 10,
        borderRadius: 16,
        backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : t.colors.surface,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: isDark ? 'rgba(255,255,255,0.06)' : t.colors.border,
      },
      chipAuthor: { fontFamily: fonts.semiBold, fontSize: 11 },
      chipText: { fontSize: 12, color: t.colors.textPrimary, marginTop: 4, lineHeight: 16 },
      unpin: { position: 'absolute', top: 6, right: 6 },
      mutedColor: { color: t.colors.textMuted },
    });
  });
}

import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { Modal, Pressable, StyleSheet, View } from 'react-native';
import Animated, { FadeIn, FadeInDown } from 'react-native-reanimated';
import { Text } from '../../../components/Text';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { fonts } from '../../../theme/fonts';
import type { ChatMessage } from '../../../types/chat';
import { chat } from '../theme/chatTokens';

const REACTIONS = ['👍', '❤️', '😂', '😮', '😢', '🔥', '🇺🇦'] as const;

type Props = {
  message: ChatMessage | null;
  isMine: boolean;
  isModerator: boolean;
  onClose: () => void;
  onReply: (message: ChatMessage) => void;
  onEdit: (message: ChatMessage) => void;
  onReact: (message: ChatMessage, emoji: string) => void;
  onDelete: (message: ChatMessage) => void;
  onCopy: (message: ChatMessage) => void;
  onReport: (message: ChatMessage) => void;
  onBlock: (message: ChatMessage) => void;
  onBan: (message: ChatMessage) => void;
  onDeleteAll: (message: ChatMessage) => void;
  onPin?: (message: ChatMessage) => void;
  onForward?: (message: ChatMessage) => void;
  onSelect?: (message: ChatMessage) => void;
};

export function ChatContextMenu({
  message,
  isMine,
  isModerator,
  onClose,
  onReply,
  onEdit,
  onReact,
  onDelete,
  onCopy,
  onReport,
  onBlock,
  onBan,
  onDeleteAll,
  onPin,
  onForward,
  onSelect,
}: Props) {
  if (!message) return null;

  const run = (fn: () => void) => {
    onClose();
    fn();
  };

  return (
    <Modal visible transparent animationType="fade" onRequestClose={onClose}>
      <Pressable style={styles.backdrop} onPress={onClose}>
        <Animated.View entering={FadeIn.duration(180)} style={StyleSheet.absoluteFill} />
        <Animated.View entering={FadeInDown.duration(280).springify().damping(20)} style={styles.cardWrap}>
          <Pressable style={styles.card} onPress={(e) => e.stopPropagation()}>
            <View style={styles.reactions}>
              {REACTIONS.map((emoji) => (
                <NeptunPressable key={emoji} haptic scaleTo={0.92} onPress={() => run(() => onReact(message, emoji))} style={styles.emojiBtn}>
                  <Text style={styles.emoji}>{emoji}</Text>
                </NeptunPressable>
              ))}
            </View>
            <View style={[styles.preview, isMine && styles.previewMine]}>
              <Text numberOfLines={4} style={styles.previewText}>
                {message.message}
              </Text>
            </View>
            <MenuItem icon="arrow-undo" label="Відповісти" onPress={() => run(() => onReply(message))} />
            {onSelect ? <MenuItem icon="checkmark-circle-outline" label="Обрати" onPress={() => run(() => onSelect(message))} /> : null}
            {onForward ? <MenuItem icon="arrow-redo-outline" label="Переслати" onPress={() => run(() => onForward(message))} /> : null}
            {onPin ? <MenuItem icon="pin-outline" label="Закріпити" onPress={() => run(() => onPin(message))} /> : null}
            <MenuItem icon="copy-outline" label="Копіювати" onPress={() => run(() => onCopy(message))} />
            {isMine ? <MenuItem icon="create-outline" label="Редагувати" onPress={() => run(() => onEdit(message))} /> : null}
            {isMine || isModerator ? (
              <MenuItem danger icon="trash-outline" label="Видалити" onPress={() => run(() => onDelete(message))} />
            ) : null}
            {isModerator && !isMine ? (
              <MenuItem danger icon="ban-outline" label="Заблокувати (модератор)" onPress={() => run(() => onBan(message))} />
            ) : null}
            {isModerator && !isMine ? (
              <MenuItem danger icon="trash-bin-outline" label="Видалити всі повідомлення" onPress={() => run(() => onDeleteAll(message))} />
            ) : null}
            {!isMine ? <MenuItem icon="flag-outline" label="Поскаржитись" onPress={() => run(() => onReport(message))} /> : null}
            {!isMine ? <MenuItem icon="eye-off-outline" label="Сховати користувача" onPress={() => run(() => onBlock(message))} /> : null}
          </Pressable>
        </Animated.View>
      </Pressable>
    </Modal>
  );
}

function MenuItem({
  icon,
  label,
  danger,
  onPress,
}: {
  icon: ComponentProps<typeof Ionicons>['name'];
  label: string;
  danger?: boolean;
  onPress: () => void;
}) {
  return (
    <NeptunPressable haptic onPress={onPress} style={styles.menuItem}>
      <Ionicons name={icon} size={20} color={danger ? chat.danger : chat.textSoft} />
      <Text style={[styles.menuLabel, danger && { color: chat.danger }]}>{label}</Text>
    </NeptunPressable>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.55)',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  cardWrap: { width: '100%', maxWidth: 360 },
  card: {
    borderRadius: chat.radiusGate,
    backgroundColor: chat.surfaceGlass,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: chat.borderStrong,
    padding: 10,
    overflow: 'hidden',
  },
  reactions: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 6,
    paddingVertical: 8,
    marginBottom: 4,
  },
  emojiBtn: {
    width: 42,
    height: 42,
    borderRadius: 21,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(255,255,255,0.06)',
  },
  emoji: { fontSize: 22 },
  preview: {
    marginHorizontal: 6,
    marginBottom: 8,
    padding: 12,
    borderRadius: 14,
    backgroundColor: 'rgba(255,255,255,0.04)',
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: chat.border,
  },
  previewMine: {
    backgroundColor: chat.accentMuted,
    borderColor: chat.accent + '44',
  },
  previewText: { fontSize: 14, lineHeight: 20, color: chat.text, fontFamily: fonts.medium },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 14,
    paddingVertical: 13,
    borderRadius: 12,
  },
  menuLabel: { fontFamily: fonts.semiBold, fontSize: 15, color: chat.text },
});

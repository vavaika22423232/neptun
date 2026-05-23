import { StyleSheet, View } from 'react-native';
import { Text } from '../../../../components/Text';
import { NeptunBottomSheet } from '../../../../components/NeptunBottomSheet';
import { NeptunPressable } from '../../../../design/components/NeptunPressable';
import { chat } from '../../theme/chatTokens';

const EMOJI_ROWS = [
  '😀', '😂', '🥲', '😍', '🙏', '👍', '👎', '❤️', '🔥', '🇺🇦',
  '😮', '😢', '🎉', '💪', '🤝', '✅', '❗', '⭐', '🫡', '🕊️',
  '🚀', '💙', '💛', '🤔', '😡', '🙈', '👀', '💬', '📌', '🛡️',
];

type Props = {
  visible: boolean;
  onClose: () => void;
  onPick: (emoji: string) => void;
};

export function ChatEmojiPickerSheet({ visible, onClose, onPick }: Props) {
  return (
    <NeptunBottomSheet visible={visible} onClose={onClose} maxHeightRatio={0.42} scrollable={false}>
      <Text style={{ fontSize: 17, fontWeight: '700', color: chat.text, marginBottom: 12 }}>Емодзі</Text>
      <View style={styles.grid}>
        {EMOJI_ROWS.map((emoji) => (
          <NeptunPressable
            key={emoji}
            haptic
            scaleTo={0.92}
            onPress={() => {
              onPick(emoji);
              onClose();
            }}
            style={styles.cell}
          >
            <Text style={styles.emoji}>{emoji}</Text>
          </NeptunPressable>
        ))}
      </View>
    </NeptunBottomSheet>
  );
}

const styles = StyleSheet.create({
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  cell: {
    width: 44,
    height: 44,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(255,255,255,0.05)',
  },
  emoji: { fontSize: 24 },
});

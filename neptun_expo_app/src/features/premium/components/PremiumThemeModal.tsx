import { Ionicons } from '@expo/vector-icons';
import { Modal, Pressable, StyleSheet, View } from 'react-native';
import { Text } from '../../../components/Text';
import { CHAT_THEMES } from '../../../config/chatThemes';
import { paywall } from '../theme/paywallTokens';
import { fonts } from '../../../theme/fonts';

type Props = {
  visible: boolean;
  themeId: string;
  onSelect: (id: string) => void;
  onClose: () => void;
};

export function PremiumThemeModal({ visible, themeId, onSelect, onClose }: Props) {
  return (
    <Modal visible={visible} animationType="fade" transparent onRequestClose={onClose}>
      <Pressable style={styles.backdrop} onPress={onClose}>
        <Pressable style={styles.card} onPress={(e) => e.stopPropagation()}>
          <Text style={styles.title}>Тема чату</Text>
          {CHAT_THEMES.map((t) => {
            const selected = themeId === t.id;
            return (
              <Pressable
                key={t.id}
                style={[styles.row, selected && styles.rowOn]}
                onPress={() => onSelect(t.id)}
              >
                <View style={[styles.swatch, { backgroundColor: t.bubbleTint || paywall.textFaint }]} />
                <Text style={styles.label}>{t.label}</Text>
                {selected ? <Ionicons name="checkmark-circle" size={22} color={paywall.accent} /> : null}
              </Pressable>
            );
          })}
        </Pressable>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.55)',
    justifyContent: 'center',
    paddingHorizontal: 28,
  },
  card: {
    borderRadius: paywall.radiusCard,
    backgroundColor: paywall.surfaceStrong,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: paywall.border,
    paddingVertical: 8,
    maxHeight: '72%',
  },
  title: {
    fontFamily: fonts.bold,
    fontSize: 17,
    color: paywall.text,
    paddingHorizontal: 18,
    paddingVertical: 14,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 18,
    paddingVertical: 12,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: paywall.divider,
  },
  rowOn: { backgroundColor: paywall.accentMuted },
  swatch: {
    width: 28,
    height: 28,
    borderRadius: 8,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: paywall.border,
  },
  label: {
    flex: 1,
    fontFamily: fonts.medium,
    fontSize: 15,
    color: paywall.text,
  },
});

import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { Alert, StyleSheet, View } from 'react-native';
import { Text } from '../../../components/Text';
import { NeptunBottomSheet } from '../../../components/NeptunBottomSheet';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { fonts } from '../../../theme/fonts';
import { chat } from '../theme/chatTokens';

type Props = {
  visible: boolean;
  onClose: () => void;
  onPickLibrary: () => void;
  onPickCamera: () => void;
};

type AttachAction = {
  icon: ComponentProps<typeof Ionicons>['name'];
  label: string;
  live: boolean;
  run: (p: Props) => void;
};

const ACTIONS: AttachAction[] = [
  { icon: 'images-outline', label: 'Галерея', live: true, run: (p) => p.onPickLibrary() },
  { icon: 'camera-outline', label: 'Камера', live: true, run: (p) => p.onPickCamera() },
  { icon: 'mic-outline', label: 'Голос', live: true, run: (p) => p.onClose() },
  { icon: 'bar-chart-outline', label: 'Опитування', live: false, run: () => soon() },
  { icon: 'document-outline', label: 'Файл', live: false, run: () => soon() },
  { icon: 'location-outline', label: 'Локація', live: false, run: () => soon() },
  { icon: 'happy-outline', label: 'GIF', live: false, run: () => soon() },
  { icon: 'sparkles-outline', label: 'AI', live: false, run: () => soon() },
];

function soon() {
  Alert.alert('Скоро', 'Ця функція з’явиться в наступних оновленнях NEPTUN.');
}

export function ChatAttachSheet({ visible, onClose, onPickLibrary, onPickCamera }: Props) {
  const props = { visible, onClose, onPickLibrary, onPickCamera };

  return (
    <NeptunBottomSheet visible={visible} onClose={onClose} maxHeightRatio={0.48} scrollable={false}>
      <Text style={styles.title}>Вкладення</Text>
      <View style={styles.grid}>
        {ACTIONS.map((action) => (
          <NeptunPressable
            key={action.label}
            haptic
            onPress={() => {
              if (!action.live) {
                action.run(props);
                return;
              }
              onClose();
              action.run(props);
            }}
            style={[styles.tile, !action.live && styles.tileSoon]}
          >
            <View style={styles.tileIcon}>
              <Ionicons name={action.icon} size={24} color={action.live ? chat.accentSoft : chat.textFaint} />
            </View>
            <Text style={[styles.tileLabel, !action.live && styles.tileLabelSoon]}>{action.label}</Text>
          </NeptunPressable>
        ))}
      </View>
    </NeptunBottomSheet>
  );
}

const styles = StyleSheet.create({
  title: {
    fontFamily: fonts.bold,
    fontSize: 18,
    color: chat.text,
    marginBottom: 14,
  },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  tile: {
    width: '22%',
    minWidth: 72,
    alignItems: 'center',
    paddingVertical: 12,
    borderRadius: 14,
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: chat.border,
  },
  tileSoon: { opacity: 0.65 },
  tileIcon: {
    width: 44,
    height: 44,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: chat.accentMuted,
    marginBottom: 6,
  },
  tileLabel: { fontFamily: fonts.semiBold, fontSize: 11, color: chat.text },
  tileLabelSoon: { color: chat.textMuted },
});

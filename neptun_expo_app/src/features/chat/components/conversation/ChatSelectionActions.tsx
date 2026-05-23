import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { StyleSheet, View } from 'react-native';
import { Text } from '../../../../components/Text';
import { NeptunPressable } from '../../../../design/components/NeptunPressable';
import { fonts } from '../../../../theme/fonts';
import { chat } from '../../theme/chatTokens';

type Props = {
  canDelete: boolean;
  onCopy: () => void;
  onForward: () => void;
  onPin: () => void;
  onDelete?: () => void;
};

export function ChatSelectionActions({ canDelete, onCopy, onForward, onPin, onDelete }: Props) {
  return (
    <View style={styles.bar}>
      <Action icon="copy-outline" label="Копія" onPress={onCopy} />
      <Action icon="arrow-redo-outline" label="Переслати" onPress={onForward} />
      <Action icon="pin-outline" label="Закріпити" onPress={onPin} />
      {canDelete && onDelete ? <Action icon="trash-outline" label="Видалити" onPress={onDelete} danger /> : null}
    </View>
  );
}

function Action({
  icon,
  label,
  onPress,
  danger,
}: {
  icon: ComponentProps<typeof Ionicons>['name'];
  label: string;
  onPress: () => void;
  danger?: boolean;
}) {
  return (
    <NeptunPressable haptic onPress={onPress} style={styles.action}>
      <Ionicons name={icon} size={22} color={danger ? chat.danger : chat.textSoft} />
      <Text style={[styles.label, danger && { color: chat.danger }]}>{label}</Text>
    </NeptunPressable>
  );
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingVertical: 10,
    paddingHorizontal: 8,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: chat.border,
    backgroundColor: chat.surfaceGlass,
  },
  action: { alignItems: 'center', gap: 4, minWidth: 72 },
  label: { fontFamily: fonts.semiBold, fontSize: 11, color: chat.textMuted },
});

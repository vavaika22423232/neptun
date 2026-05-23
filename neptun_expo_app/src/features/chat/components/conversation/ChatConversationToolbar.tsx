import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, View } from 'react-native';
import { Text } from '../../../../components/Text';
import { NeptunPressable } from '../../../../design/components/NeptunPressable';
import { fonts } from '../../../../theme/fonts';
import { chat } from '../../theme/chatTokens';

type Props = {
  title: string;
  subtitle?: string;
  live?: boolean;
  onlineCount?: number;
  selectionMode?: boolean;
  selectedCount?: number;
  onBack: () => void;
  onSearch?: () => void;
  onMedia?: () => void;
  onFeatures?: () => void;
  onMore?: () => void;
  onCancelSelection?: () => void;
};

export function ChatConversationToolbar({
  title,
  subtitle,
  live,
  onlineCount,
  selectionMode,
  selectedCount = 0,
  onBack,
  onSearch,
  onMedia,
  onFeatures,
  onMore,
  onCancelSelection,
}: Props) {
  if (selectionMode) {
    return (
      <View style={styles.bar}>
        <NeptunPressable haptic onPress={onCancelSelection} style={styles.iconBtn}>
          <Ionicons name="close" size={22} color={chat.text} />
        </NeptunPressable>
        <Text style={styles.selectionTitle}>{selectedCount} обрано</Text>
        <View style={{ width: 44 }} />
      </View>
    );
  }

  return (
    <View style={styles.bar}>
      <NeptunPressable haptic onPress={onBack} style={styles.iconBtn}>
        <Ionicons name="chevron-back" size={24} color={chat.text} />
      </NeptunPressable>
      <View style={styles.center}>
        <Text style={styles.title} numberOfLines={1}>
          {title}
        </Text>
        <View style={styles.metaRow}>
          {live ? (
            <>
              <View style={styles.liveDot} />
              <Text style={styles.metaLive}>Live</Text>
            </>
          ) : null}
          {subtitle ? <Text style={styles.meta}>{subtitle}</Text> : null}
          {onlineCount != null && onlineCount > 0 ? (
            <Text style={styles.meta}> · {onlineCount} онлайн</Text>
          ) : null}
        </View>
      </View>
      {onMedia ? (
        <NeptunPressable haptic onPress={onMedia} style={styles.iconBtn}>
          <Ionicons name="images-outline" size={20} color={chat.textSoft} />
        </NeptunPressable>
      ) : null}
      {onSearch ? (
        <NeptunPressable haptic onPress={onSearch} style={styles.iconBtn}>
          <Ionicons name="search" size={20} color={chat.textSoft} />
        </NeptunPressable>
      ) : null}
      {onFeatures ? (
        <NeptunPressable haptic onPress={onFeatures} style={styles.iconBtn}>
          <Ionicons name="grid-outline" size={20} color={chat.textSoft} />
        </NeptunPressable>
      ) : null}
      {onMore ? (
        <NeptunPressable haptic onPress={onMore} style={styles.iconBtn}>
          <Ionicons name="ellipsis-vertical" size={20} color={chat.textSoft} />
        </NeptunPressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 8,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: chat.border,
    backgroundColor: 'rgba(6, 8, 15, 0.92)',
  },
  iconBtn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: 'center',
    justifyContent: 'center',
  },
  center: { flex: 1, minWidth: 0, paddingHorizontal: 4 },
  title: { fontFamily: fonts.bold, fontSize: 16, color: chat.text, textAlign: 'center' },
  metaRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', marginTop: 2 },
  meta: { fontSize: 11, color: chat.textMuted },
  metaLive: { fontSize: 11, color: chat.success, fontFamily: fonts.semiBold },
  liveDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: chat.success,
    marginRight: 4,
  },
  selectionTitle: {
    flex: 1,
    textAlign: 'center',
    fontFamily: fonts.bold,
    fontSize: 16,
    color: chat.text,
  },
});

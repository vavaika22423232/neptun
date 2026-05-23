import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, View } from 'react-native';
import { Text } from '../../../../components/Text';
import { NeptunBottomSheet } from '../../../../components/NeptunBottomSheet';
import { NeptunPressable } from '../../../../design/components/NeptunPressable';
import { fonts } from '../../../../theme/fonts';
import { avatarAccent, displayInitials } from '../../../../utils/avatarPalette';
import { chat } from '../../theme/chatTokens';

type Props = {
  visible: boolean;
  nickname: string;
  isModerator?: boolean;
  isPro?: boolean;
  onClose: () => void;
  onMention?: () => void;
  onBlock?: () => void;
  onReport?: () => void;
};

export function ChatUserProfileSheet({
  visible,
  nickname,
  isModerator,
  isPro,
  onClose,
  onMention,
  onBlock,
  onReport,
}: Props) {
  const hue = avatarAccent(nickname);

  return (
    <NeptunBottomSheet visible={visible} onClose={onClose} maxHeightRatio={0.5} scrollable={false}>
      <View style={styles.hero}>
        <View style={[styles.avatar, { backgroundColor: hue }]}>
          <Text style={styles.initials}>{displayInitials(nickname)}</Text>
        </View>
        <Text style={styles.name}>{nickname}</Text>
        <View style={styles.tags}>
          {isModerator ? (
            <View style={styles.tag}>
              <Ionicons name="shield-checkmark" size={12} color={chat.success} />
              <Text style={styles.tagText}>Модератор</Text>
            </View>
          ) : null}
          {isPro ? (
            <View style={[styles.tag, styles.tagPro]}>
              <Ionicons name="star" size={12} color={chat.premium} />
              <Text style={[styles.tagText, { color: chat.premium }]}>PRO</Text>
            </View>
          ) : null}
        </View>
      </View>
      {onMention ? (
        <NeptunPressable haptic onPress={onMention} style={styles.row}>
          <Ionicons name="at" size={20} color={chat.accentSoft} />
          <Text style={styles.rowLabel}>Згадати @{nickname}</Text>
        </NeptunPressable>
      ) : null}
      {onBlock ? (
        <NeptunPressable haptic onPress={onBlock} style={styles.row}>
          <Ionicons name="eye-off-outline" size={20} color={chat.textSoft} />
          <Text style={styles.rowLabel}>Сховати повідомлення</Text>
        </NeptunPressable>
      ) : null}
      {onReport ? (
        <NeptunPressable haptic onPress={onReport} style={styles.row}>
          <Ionicons name="flag-outline" size={20} color={chat.danger} />
          <Text style={[styles.rowLabel, { color: chat.danger }]}>Поскаржитись</Text>
        </NeptunPressable>
      ) : null}
    </NeptunBottomSheet>
  );
}

const styles = StyleSheet.create({
  hero: { alignItems: 'center', paddingVertical: 8, marginBottom: 12 },
  avatar: {
    width: 72,
    height: 72,
    borderRadius: 36,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 10,
  },
  initials: { color: '#fff', fontFamily: fonts.bold, fontSize: 24 },
  name: { fontFamily: fonts.bold, fontSize: 20, color: chat.text },
  tags: { flexDirection: 'row', gap: 8, marginTop: 8 },
  tag: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: chat.radiusPill,
    backgroundColor: 'rgba(255,255,255,0.06)',
  },
  tagPro: { backgroundColor: 'rgba(212, 184, 122, 0.14)' },
  tagText: { fontSize: 11, fontFamily: fonts.semiBold, color: chat.textMuted },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 14,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: chat.divider,
  },
  rowLabel: { fontFamily: fonts.semiBold, fontSize: 15, color: chat.text },
});

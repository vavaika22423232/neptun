import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { StyleSheet, View } from 'react-native';
import { Text } from '../../../../components/Text';
import { NeptunBottomSheet } from '../../../../components/NeptunBottomSheet';
import { fonts } from '../../../../theme/fonts';
import { CHAT_FEATURE_GROUPS, type ChatFeatureStatus } from '../../domain/chatFeatureRegistry';
import { chat } from '../../theme/chatTokens';

type Props = {
  visible: boolean;
  onClose: () => void;
};

const STATUS_LABEL: Record<ChatFeatureStatus, string> = {
  live: 'Доступно',
  partial: 'Частково',
  soon: 'Скоро',
};

const STATUS_COLOR: Record<ChatFeatureStatus, string> = {
  live: chat.success,
  partial: chat.accentSoft,
  soon: chat.textFaint,
};

export function ChatFeaturesSheet({ visible, onClose }: Props) {
  return (
    <NeptunBottomSheet visible={visible} onClose={onClose} maxHeightRatio={0.72}>
      <Text style={styles.title}>Можливості чату</Text>
      <Text muted style={styles.sub}>
        Платформа NEPTUN розширюється. Нижче — що вже працює та що в дорожній карті.
      </Text>
      {CHAT_FEATURE_GROUPS.map((group) => (
        <View key={group.title} style={styles.section}>
          <Text style={styles.sectionTitle}>{group.title}</Text>
          {group.items.map((item) => (
            <View key={item.id} style={styles.row}>
              <View style={styles.icon}>
                <Ionicons name={item.icon as ComponentProps<typeof Ionicons>['name']} size={18} color={chat.accentSoft} />
              </View>
              <View style={styles.body}>
                <Text style={styles.rowTitle}>{item.title}</Text>
                <Text muted style={styles.rowSub}>{item.description}</Text>
              </View>
              <Text style={[styles.badge, { color: STATUS_COLOR[item.status] }]}>{STATUS_LABEL[item.status]}</Text>
            </View>
          ))}
        </View>
      ))}
    </NeptunBottomSheet>
  );
}

const styles = StyleSheet.create({
  title: { fontFamily: fonts.bold, fontSize: 20, color: chat.text, marginBottom: 4 },
  sub: { fontSize: 13, lineHeight: 18, marginBottom: 16 },
  section: { marginBottom: 18 },
  sectionTitle: {
    fontFamily: fonts.semiBold,
    fontSize: 11,
    color: chat.textFaint,
    letterSpacing: 0.6,
    textTransform: 'uppercase',
    marginBottom: 8,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 10,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: chat.divider,
  },
  icon: {
    width: 36,
    height: 36,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: chat.accentMuted,
  },
  body: { flex: 1 },
  rowTitle: { fontFamily: fonts.semiBold, fontSize: 14, color: chat.text },
  rowSub: { fontSize: 11, marginTop: 2 },
  badge: { fontFamily: fonts.bold, fontSize: 10 },
});

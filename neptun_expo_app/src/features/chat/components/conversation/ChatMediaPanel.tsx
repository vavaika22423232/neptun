import { Ionicons } from '@expo/vector-icons';
import { Image, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { Text } from '../../../../components/Text';
import { absoluteUrl } from '../../../../config/api';
import { NeptunBottomSheet } from '../../../../components/NeptunBottomSheet';
import { fonts } from '../../../../theme/fonts';
import type { ChatMessage } from '../../../../types/chat';
import { chat } from '../../theme/chatTokens';

type Props = {
  visible: boolean;
  messages: ChatMessage[];
  onClose: () => void;
  onOpenImage: (url: string) => void;
};

export function ChatMediaPanel({ visible, messages, onClose, onOpenImage }: Props) {
  const images = messages.filter((m) => m.messageType === 'image' && m.imageUrl).slice(0, 40);
  const voices = messages.filter((m) => m.messageType === 'voice').length;

  return (
    <NeptunBottomSheet visible={visible} onClose={onClose} maxHeightRatio={0.55}>
      <Text style={styles.title}>Медіа в чаті</Text>
      <Text muted style={styles.sub}>
        {images.length} фото · {voices} голосових
      </Text>
      <ScrollView contentContainerStyle={styles.grid}>
        {images.map((m) => {
          const url = absoluteUrl(m.imageUrl!);
          return (
            <Pressable key={m.id} onPress={() => onOpenImage(url)} style={styles.thumb}>
              <Image source={{ uri: url }} style={styles.img} />
            </Pressable>
          );
        })}
        {!images.length ? (
          <View style={styles.empty}>
            <Ionicons name="images-outline" size={40} color={chat.textFaint} />
            <Text muted>Ще немає фото в стрічці</Text>
          </View>
        ) : null}
      </ScrollView>
    </NeptunBottomSheet>
  );
}

const styles = StyleSheet.create({
  title: { fontFamily: fonts.bold, fontSize: 18, color: chat.text },
  sub: { marginBottom: 14, fontSize: 13 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  thumb: { width: '31%', aspectRatio: 1, borderRadius: 12, overflow: 'hidden' },
  img: { width: '100%', height: '100%' },
  empty: { width: '100%', alignItems: 'center', padding: 32, gap: 10 },
});

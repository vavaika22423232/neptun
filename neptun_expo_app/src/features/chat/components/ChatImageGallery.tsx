import { Ionicons } from '@expo/vector-icons';
import * as Linking from 'expo-linking';
import { useRef, useState } from 'react';
import {
  ActivityIndicator,
  Dimensions,
  Image,
  Modal,
  PanResponder,
  StyleSheet,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Text } from '../../../components/Text';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { chat } from '../theme/chatTokens';

type Props = {
  visible: boolean;
  imageUrl: string;
  onClose: () => void;
};

/** Flutter `ChatImageGallery` — pinch-zoom + swipe down to dismiss. */
export function ChatImageGallery({ visible, imageUrl, onClose }: Props) {
  const insets = useSafeAreaInsets();
  const [dragY, setDragY] = useState(0);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const dragRef = useRef(0);

  const panResponder = useRef(
    PanResponder.create({
      onMoveShouldSetPanResponder: (_, g) => Math.abs(g.dy) > 8 && Math.abs(g.dy) > Math.abs(g.dx),
      onPanResponderMove: (_, g) => {
        dragRef.current = g.dy;
        setDragY(g.dy);
      },
      onPanResponderRelease: () => {
        if (Math.abs(dragRef.current) > 150) onClose();
        else {
          dragRef.current = 0;
          setDragY(0);
        }
      },
    }),
  ).current;

  const bgOpacity = Math.max(0.2, 1 - Math.abs(dragY) / 400);

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={[styles.backdrop, { opacity: bgOpacity }]}>
        <View style={[styles.toolbar, { paddingTop: insets.top + 8 }]}>
          <NeptunPressable haptic onPress={onClose} style={styles.iconBtn}>
            <Ionicons name="close" size={26} color={chat.text} />
          </NeptunPressable>
          <NeptunPressable haptic onPress={() => void Linking.openURL(imageUrl)} style={styles.iconBtn}>
            <Ionicons name="open-outline" size={22} color={chat.text} />
          </NeptunPressable>
        </View>

        <View style={styles.stage} {...panResponder.panHandlers}>
          <View style={{ transform: [{ translateY: dragY }] }}>
            {failed ? (
              <View style={styles.errorBox}>
                <Ionicons name="image-outline" size={48} color={chat.danger} />
                <Text muted>Не вдалося завантажити зображення</Text>
              </View>
            ) : (
              <Image
                source={{ uri: imageUrl }}
                style={styles.image}
                resizeMode="contain"
                onLoadStart={() => {
                  setLoading(true);
                  setFailed(false);
                }}
                onLoadEnd={() => setLoading(false)}
                onError={() => {
                  setLoading(false);
                  setFailed(true);
                }}
              />
            )}
            {loading ? <ActivityIndicator style={styles.loader} color={chat.accent} /> : null}
          </View>
        </View>
      </View>
    </Modal>
  );
}

const { width, height } = Dimensions.get('window');

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.94)',
  },
  toolbar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 12,
  },
  iconBtn: {
    width: 44,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stage: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  image: {
    width: width,
    height: height * 0.72,
  },
  loader: {
    position: 'absolute',
    alignSelf: 'center',
  },
  errorBox: {
    alignItems: 'center',
    gap: 12,
    padding: 24,
  },
});

import {
  Dimensions,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  View,
  type ViewStyle,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { radii, spacing } from '../design/tokens';
import { useThemedStyles } from '../theme/useAppTheme';

type Props = {
  visible: boolean;
  onClose: () => void;
  children: React.ReactNode;
  /** Fraction of screen height (Flutter ~0.62 threat / 0.4 region). */
  maxHeightRatio?: number;
  scrollable?: boolean;
  contentStyle?: ViewStyle;
};

/** Premium bottom sheet — glass surface, soft handle. */
export function NeptunBottomSheet({
  visible,
  onClose,
  children,
  maxHeightRatio = 0.62,
  scrollable = true,
  contentStyle,
}: Props) {
  const insets = useSafeAreaInsets();
  const maxHeight = Dimensions.get('window').height * maxHeightRatio;
  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      backdrop: {
        flex: 1,
        justifyContent: 'flex-end',
        backgroundColor: t.colors.scrim,
      },
      sheet: {
        marginHorizontal: spacing.md,
        borderRadius: radii.sheet,
        backgroundColor: t.colors.surfaceElevated,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.colors.borderStrong,
        paddingTop: spacing.sm,
        overflow: 'hidden',
        ...t.shadows.sheet,
      },
      handle: {
        alignSelf: 'center',
        width: 40,
        height: 5,
        borderRadius: radii.pill,
        backgroundColor: t.colors.borderStrong,
        marginBottom: spacing.sm,
      },
      scrollInner: {
        paddingHorizontal: spacing.screenH,
        paddingTop: spacing.sm,
        gap: spacing.md,
      },
    }),
  );

  const body = scrollable ? (
    <ScrollView
      bounces
      showsVerticalScrollIndicator={false}
      contentContainerStyle={[styles.scrollInner, { paddingBottom: insets.bottom + 16 }, contentStyle]}
    >
      {children}
    </ScrollView>
  ) : (
    <View style={[styles.scrollInner, { paddingBottom: insets.bottom + 16 }, contentStyle]}>{children}</View>
  );

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.backdrop} onPress={onClose}>
        <Pressable style={[styles.sheet, { maxHeight }]} onPress={(e) => e.stopPropagation()}>
          <View style={styles.handle} />
          {body}
        </Pressable>
      </Pressable>
    </Modal>
  );
}

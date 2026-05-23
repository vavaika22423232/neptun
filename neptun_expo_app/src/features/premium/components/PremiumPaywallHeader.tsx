import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, View } from 'react-native';
import { Text } from '../../../components/Text';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { paywall } from '../theme/paywallTokens';
import { fonts } from '../../../theme/fonts';

type Props = {
  onClose: () => void;
  onRestore?: () => void;
  showRestore?: boolean;
};

export function PremiumPaywallHeader({ onClose, onRestore, showRestore }: Props) {
  return (
    <View style={styles.row}>
      <NeptunPressable haptic onPress={onClose} style={styles.iconBtn} accessibilityLabel="Закрити">
        <Ionicons name="close" size={22} color={paywall.textSoft} />
      </NeptunPressable>
      {showRestore && onRestore ? (
        <NeptunPressable haptic={false} onPress={onRestore} style={styles.restore}>
          <Text style={styles.restoreText}>Відновити</Text>
        </NeptunPressable>
      ) : (
        <View style={styles.spacer} />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingBottom: 4,
  },
  iconBtn: {
    width: 42,
    height: 42,
    borderRadius: paywall.radiusPill,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: paywall.surface,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: paywall.border,
  },
  restore: { marginLeft: 'auto', paddingHorizontal: 12, paddingVertical: 10 },
  restoreText: {
    fontFamily: fonts.semiBold,
    fontSize: 15,
    color: paywall.textMuted,
  },
  spacer: { width: 42 },
});

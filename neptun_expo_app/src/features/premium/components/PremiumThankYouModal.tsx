import { Ionicons } from '@expo/vector-icons';
import { Modal, StyleSheet, View } from 'react-native';
import { PrimaryButton } from '../../../components/PrimaryButton';
import { Text } from '../../../components/Text';
import { paywall } from '../theme/paywallTokens';
import { fonts } from '../../../theme/fonts';

type Props = {
  visible: boolean;
  onDismiss: () => void;
};

export function PremiumThankYouModal({ visible, onDismiss }: Props) {
  return (
    <Modal visible={visible} animationType="fade" transparent onRequestClose={onDismiss}>
      <View style={styles.backdrop}>
        <View style={styles.card}>
          <View style={styles.iconWrap}>
            <Ionicons name="sparkles" size={32} color={paywall.accentSoft} />
          </View>
          <Text style={styles.title}>Ласкаво просимо в PRO</Text>
          <Text style={styles.sub}>
            Дякуємо за підтримку. Усі можливості вже активні — налаштуйте оформлення нижче.
          </Text>
          <PrimaryButton onPress={onDismiss}>Продовжити</PrimaryButton>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.58)',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 28,
  },
  card: {
    width: '100%',
    maxWidth: 360,
    borderRadius: paywall.radiusCard,
    backgroundColor: paywall.surfaceStrong,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: paywall.borderStrong,
    padding: 26,
    alignItems: 'center',
    gap: 14,
  },
  iconWrap: {
    width: 64,
    height: 64,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: paywall.accentMuted,
    marginBottom: 4,
  },
  title: {
    fontFamily: fonts.bold,
    fontSize: 22,
    color: paywall.text,
    textAlign: 'center',
  },
  sub: {
    fontFamily: fonts.medium,
    fontSize: 15,
    lineHeight: 22,
    color: paywall.textMuted,
    textAlign: 'center',
    marginBottom: 8,
  },
});

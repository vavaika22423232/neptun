import { LinearGradient } from 'expo-linear-gradient';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { Text } from '../../../components/Text';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { paywall } from '../theme/paywallTokens';
import { fonts } from '../../../theme/fonts';

type Props = {
  price: string;
  loading: boolean;
  onPurchase: () => void;
  bottomInset: number;
};

export function PremiumStickyCta({ price, loading, onPurchase, bottomInset }: Props) {
  return (
    <View style={[styles.container, { paddingBottom: bottomInset }]}>
      <LinearGradient
        colors={['transparent', 'rgba(6,8,15,0)', paywall.bg]}
        style={styles.fade}
        pointerEvents="none"
      />
      <View style={styles.shell}>
        <View style={styles.copy}>
          <Text style={styles.label}>Підтримка незалежного проєкту</Text>
          <Text style={styles.title}>Відкрити PRO назавжди</Text>
        </View>
        <NeptunPressable
          haptic
          onPress={onPurchase}
          disabled={loading}
          style={[styles.btnWrap, styles.btn, loading && styles.btnDisabled]}
        >
          {loading ? (
            <ActivityIndicator color={paywall.accentOnCta} />
          ) : (
            <>
              <Text style={styles.btnText}>{price}</Text>
              <Text style={styles.btnSub}>Одноразово</Text>
            </>
          )}
        </NeptunPressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
  },
  fade: {
    position: 'absolute',
    left: 0,
    right: 0,
    top: -48,
    height: 48,
  },
  shell: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    paddingHorizontal: paywall.inset,
    paddingTop: 14,
    paddingBottom: 12,
    backgroundColor: paywall.surfaceStrong,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: paywall.border,
  },
  copy: { flex: 1 },
  label: {
    fontFamily: fonts.medium,
    fontSize: 11,
    color: paywall.textFaint,
    letterSpacing: 0.3,
  },
  title: {
    marginTop: 3,
    fontFamily: fonts.bold,
    fontSize: 17,
    color: paywall.text,
    letterSpacing: -0.2,
  },
  btnWrap: {
    minWidth: 148,
    borderRadius: 18,
    overflow: 'hidden',
    ...paywall.shadows.sm,
  },
  btnDisabled: { opacity: 0.7 },
  btn: {
    minHeight: 54,
    paddingHorizontal: 20,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 18,
    gap: 1,
    backgroundColor: paywall.accent,
  },
  btnText: {
    fontFamily: fonts.bold,
    fontSize: 15,
    color: paywall.accentOnCta,
    letterSpacing: -0.2,
  },
  btnSub: {
    fontFamily: fonts.semiBold,
    fontSize: 10,
    color: paywall.accentOnCta,
    opacity: 0.75,
    letterSpacing: 0.4,
  },
});

import { Ionicons } from '@expo/vector-icons';
import { useEffect } from 'react';
import { StyleSheet, View } from 'react-native';
import Animated, {
  Easing,
  FadeInDown,
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withSequence,
  withTiming,
} from 'react-native-reanimated';
import { Text } from '../../../components/Text';
import { paywall } from '../theme/paywallTokens';
import { fonts } from '../../../theme/fonts';

type Props = {
  price: string;
  selected?: boolean;
};

export function PremiumPlanCard({ price, selected = true }: Props) {
  const floatY = useSharedValue(0);

  useEffect(() => {
    floatY.value = withRepeat(
      withSequence(
        withTiming(-3, { duration: 2200, easing: Easing.inOut(Easing.ease) }),
        withTiming(0, { duration: 2200, easing: Easing.inOut(Easing.ease) }),
      ),
      -1,
      false,
    );
  }, [floatY]);

  const floatStyle = useAnimatedStyle(() => ({
    transform: [{ translateY: floatY.value }],
  }));

  return (
    <Animated.View
      entering={FadeInDown.delay(60).duration(340).springify().damping(20)}
      style={[styles.card, selected && styles.cardOn, floatStyle]}
    >
      <View style={styles.badge}>
        <Text style={styles.badgeText}>Найкраща пропозиція</Text>
      </View>
      <View style={styles.topRow}>
        <View>
          <Text style={styles.planName}>PRO назавжди</Text>
          <Text style={styles.planHint}>Одноразова покупка · без підписки</Text>
        </View>
        <Ionicons name="checkmark-circle" size={26} color={paywall.accent} />
      </View>
      <Text style={styles.price}>{price}</Text>
      <View style={styles.trustRow}>
        {['Миттєвий доступ', 'Без реклами', 'Назавжди'].map((t) => (
          <View key={t} style={styles.trustChip}>
            <Text style={styles.trustText}>{t}</Text>
          </View>
        ))}
      </View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: paywall.radiusCard,
    padding: 20,
    paddingTop: 36,
    backgroundColor: paywall.surface,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: paywall.border,
    ...paywall.shadows.sm,
  },
  cardOn: {
    borderColor: paywall.accent + '55',
    backgroundColor: paywall.accentMuted,
  },
  badge: {
    position: 'absolute',
    top: 12,
    left: 0,
    right: 0,
    alignItems: 'center',
  },
  badgeText: {
    fontFamily: fonts.bold,
    fontSize: 10,
    letterSpacing: 0.8,
    textTransform: 'uppercase',
    color: paywall.accentSoft,
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: paywall.radiusPill,
    backgroundColor: 'rgba(255,255,255,0.06)',
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: paywall.border,
  },
  topRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: 12,
  },
  planName: {
    fontFamily: fonts.bold,
    fontSize: 20,
    color: paywall.text,
    letterSpacing: -0.3,
  },
  planHint: {
    marginTop: 4,
    fontFamily: fonts.regular,
    fontSize: 13,
    color: paywall.textMuted,
  },
  price: {
    marginTop: 18,
    fontFamily: fonts.bold,
    fontSize: 38,
    letterSpacing: -1.2,
    color: paywall.accentSoft,
  },
  trustRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginTop: 14,
  },
  trustChip: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: paywall.radiusPill,
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: paywall.border,
  },
  trustText: {
    fontFamily: fonts.medium,
    fontSize: 11,
    color: paywall.textMuted,
  },
});

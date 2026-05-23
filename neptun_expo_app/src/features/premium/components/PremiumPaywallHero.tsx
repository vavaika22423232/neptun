import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, View } from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { Text } from '../../../components/Text';
import { AppConstants } from '../../../config/constants';
import { paywall } from '../theme/paywallTokens';
import { fonts } from '../../../theme/fonts';

type Props = {
  isMember: boolean;
};

export function PremiumPaywallHero({ isMember }: Props) {
  return (
    <Animated.View entering={FadeInDown.duration(320)} style={styles.root}>
      <View style={styles.badgeWrap}>
        <View style={styles.badgeOuter}>
          <View style={styles.badgeInner}>
            <Ionicons name={isMember ? 'checkmark' : 'sparkles'} size={28} color={paywall.accentSoft} />
          </View>
        </View>
      </View>

      <Text style={styles.title}>{isMember ? 'PRO активний' : `${AppConstants.appName} PRO`}</Text>
      <Text style={styles.subtitle}>
        {isMember
          ? 'Дякуємо за підтримку — усі можливості відкриті.'
          : 'Менше реклами. Більше контролю. Швидші сповіщення.'}
      </Text>
    </Animated.View>
  );
}

const BADGE = 80;

const styles = StyleSheet.create({
  root: {
    alignItems: 'center',
    paddingTop: 8,
    paddingBottom: 20,
    paddingHorizontal: 12,
  },
  badgeWrap: {
    width: BADGE + 12,
    height: BADGE + 12,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 18,
  },
  badgeOuter: {
    width: BADGE,
    height: BADGE,
    borderRadius: BADGE / 2,
    padding: 2,
    backgroundColor: paywall.accentMuted,
  },
  badgeInner: {
    flex: 1,
    borderRadius: BADGE / 2 - 2,
    backgroundColor: paywall.surfaceStrong,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: paywall.borderStrong,
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {
    fontFamily: fonts.bold,
    fontSize: 26,
    lineHeight: 32,
    letterSpacing: -0.4,
    color: paywall.text,
    textAlign: 'center',
  },
  subtitle: {
    marginTop: 10,
    fontFamily: fonts.medium,
    fontSize: 15,
    lineHeight: 22,
    color: paywall.textMuted,
    textAlign: 'center',
    maxWidth: 320,
  },
});

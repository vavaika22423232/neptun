import { LinearGradient } from 'expo-linear-gradient';
import { StyleSheet, View } from 'react-native';
import Animated, { FadeInUp } from 'react-native-reanimated';
import { Text } from '../../../components/Text';
import { fonts } from '../../../theme/fonts';
import { avatarAccent, avatarInitialsColor, displayInitials } from '../../../utils/avatarPalette';

const NOTIFICATIONS = [
  {
    author: 'NEPTUN',
    body: 'Shahed у напрямку Києва. Перейдіть до укриття.',
    time: 'зараз',
    seed: 'NEPTUN',
  },
  {
    author: 'Спільнота',
    body: 'Київська обл. — активна загроза БПЛА.',
    time: '2 хв',
    seed: 'Спільнота',
  },
] as const;

const FLOATERS = ['АМ', 'ВС', 'ОК', 'МК', 'ІП'];

/** Lock-screen mock with sample alert cards — reference notifications page. */
export function OnboardingLockScreenHero() {
  return (
    <Animated.View entering={FadeInUp.duration(560).springify()} style={styles.wrap}>
      <View style={styles.phone}>
        <LinearGradient colors={['#F5C2D7', '#C7B6FF', '#A8C4FF']} style={styles.wallpaper}>
          <Text style={styles.date}>Понеділок, 9 вересня</Text>
          <Text style={styles.clock}>9:41</Text>
          <View style={styles.cards}>
            {NOTIFICATIONS.map((n) => (
              <View key={n.time} style={styles.card}>
                <View style={[styles.cardAvatar, { backgroundColor: avatarAccent(n.seed) }]}>
                  <Text style={[styles.cardAvatarText, { color: avatarInitialsColor(n.seed) }]}>
                    {displayInitials(n.seed)}
                  </Text>
                </View>
                <View style={styles.cardBody}>
                  <View style={styles.cardTop}>
                    <Text style={styles.cardAuthor}>{n.author}</Text>
                    <Text style={styles.cardTime}>{n.time}</Text>
                  </View>
                  <Text style={styles.cardMessage} numberOfLines={2}>
                    {n.body}
                  </Text>
                </View>
              </View>
            ))}
          </View>
        </LinearGradient>
      </View>
      <View style={styles.floaters}>
        {FLOATERS.map((seed, i) => (
          <View
            key={seed}
            style={[
              styles.floater,
              {
                backgroundColor: avatarAccent(seed),
                marginTop: i % 2 === 0 ? 0 : 12,
                transform: [{ rotate: `${(i - 2) * 6}deg` }],
              },
            ]}
          >
            <Text style={[styles.floaterText, { color: avatarInitialsColor(seed) }]}>{seed}</Text>
          </View>
        ))}
      </View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    alignItems: 'center',
    gap: 18,
  },
  phone: {
    width: 250,
    borderRadius: 34,
    overflow: 'hidden',
    backgroundColor: '#FFFFFF',
    shadowColor: '#000000',
    shadowOpacity: 0.14,
    shadowRadius: 24,
    shadowOffset: { width: 0, height: 12 },
    elevation: 12,
  },
  wallpaper: {
    minHeight: 320,
    paddingTop: 28,
    paddingHorizontal: 16,
    paddingBottom: 20,
    alignItems: 'center',
  },
  date: {
    fontFamily: fonts.medium,
    fontSize: 13,
    color: 'rgba(255,255,255,0.92)',
    marginBottom: 2,
  },
  clock: {
    fontFamily: fonts.bold,
    fontSize: 54,
    letterSpacing: -1,
    color: '#FFFFFF',
    marginBottom: 18,
  },
  cards: {
    width: '100%',
    gap: 8,
  },
  card: {
    flexDirection: 'row',
    gap: 10,
    padding: 12,
    borderRadius: 18,
    backgroundColor: 'rgba(255,255,255,0.94)',
    shadowColor: '#000000',
    shadowOpacity: 0.08,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 3,
  },
  cardAvatar: {
    width: 34,
    height: 34,
    borderRadius: 17,
    alignItems: 'center',
    justifyContent: 'center',
  },
  cardAvatarText: {
    fontFamily: fonts.bold,
    fontSize: 11,
  },
  cardBody: { flex: 1, minWidth: 0 },
  cardTop: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
    marginBottom: 2,
  },
  cardAuthor: {
    fontFamily: fonts.semiBold,
    fontSize: 13,
    color: '#000000',
  },
  cardTime: {
    fontFamily: fonts.regular,
    fontSize: 12,
    color: 'rgba(60,60,67,0.55)',
  },
  cardMessage: {
    fontFamily: fonts.regular,
    fontSize: 13,
    lineHeight: 17,
    color: 'rgba(60,60,67,0.82)',
  },
  floaters: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'center',
    gap: 10,
    paddingHorizontal: 8,
  },
  floater: {
    width: 42,
    height: 42,
    borderRadius: 21,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 3,
    borderColor: '#F2F2F7',
    shadowColor: '#000000',
    shadowOpacity: 0.12,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 4 },
    elevation: 4,
  },
  floaterText: {
    fontFamily: fonts.bold,
    fontSize: 12,
  },
});

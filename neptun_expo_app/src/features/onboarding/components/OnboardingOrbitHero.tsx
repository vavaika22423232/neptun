import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, View } from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { Text } from '../../../components/Text';
import { fonts } from '../../../theme/fonts';
import { avatarAccent, avatarInitialsColor, displayInitials } from '../../../utils/avatarPalette';

const MEMBERS = ['Олена', 'Максим', 'Ірина', 'Андрій', 'Софія', 'Тарас', 'Юлія', 'Дмитро', 'Катя', 'Віктор'];

const SIZE = 280;
const CENTER = SIZE / 2;
const ORBIT_R = 108;
const DOT = 44;
const CORE = 92;

/** Central icon with orbiting community avatars — reference onboarding style. */
export function OnboardingOrbitHero() {
  return (
    <Animated.View entering={FadeInDown.duration(520).springify()} style={styles.stage}>
      <View style={styles.orbitRing} />
      {MEMBERS.map((name, i) => {
        const angle = (i / MEMBERS.length) * Math.PI * 2 - Math.PI / 2;
        const left = CENTER + ORBIT_R * Math.cos(angle) - DOT / 2;
        const top = CENTER + ORBIT_R * Math.sin(angle) - DOT / 2;
        const color = avatarAccent(name);
        return (
          <View
            key={name}
            style={[
              styles.dot,
              {
                left,
                top,
                backgroundColor: color,
                shadowColor: color,
              },
            ]}
          >
            <Text style={[styles.dotText, { color: avatarInitialsColor(name) }]}>
              {displayInitials(name)}
            </Text>
          </View>
        );
      })}
      <View style={styles.core}>
        <Ionicons name="shield-checkmark" size={40} color="#FFFFFF" />
      </View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  stage: {
    width: SIZE,
    height: SIZE,
    alignSelf: 'center',
  },
  orbitRing: {
    position: 'absolute',
    left: CENTER - ORBIT_R - 18,
    top: CENTER - ORBIT_R - 18,
    width: (ORBIT_R + 18) * 2,
    height: (ORBIT_R + 18) * 2,
    borderRadius: ORBIT_R + 18,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.05)',
    backgroundColor: 'rgba(255,255,255,0.45)',
  },
  core: {
    position: 'absolute',
    left: CENTER - CORE / 2,
    top: CENTER - CORE / 2,
    width: CORE,
    height: CORE,
    borderRadius: CORE / 2,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#000000',
    shadowColor: '#000000',
    shadowOpacity: 0.22,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 8 },
    elevation: 8,
  },
  dot: {
    position: 'absolute',
    width: DOT,
    height: DOT,
    borderRadius: DOT / 2,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 3,
    borderColor: '#F2F2F7',
    shadowOpacity: 0.28,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 4 },
    elevation: 4,
  },
  dotText: {
    fontFamily: fonts.bold,
    fontSize: 13,
  },
});

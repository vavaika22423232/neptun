import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { StyleSheet, View } from 'react-native';
import Animated, { FadeIn } from 'react-native-reanimated';
import { Text } from '../../../components/Text';
import { fonts } from '../../../theme/fonts';

const FEATURES: { icon: ComponentProps<typeof Ionicons>['name']; label: string }[] = [
  { icon: 'map-outline', label: 'Карта live' },
  { icon: 'radio-outline', label: 'Radar' },
  { icon: 'chatbubbles-outline', label: 'Чат' },
  { icon: 'notifications-outline', label: 'Сповіщення' },
];

export function OnboardingReadyHero() {
  return (
    <Animated.View entering={FadeIn.duration(480)} style={styles.wrap}>
      <View style={styles.badge}>
        <Ionicons name="checkmark" size={34} color="#FFFFFF" />
      </View>
      <View style={styles.grid}>
        {FEATURES.map((f, i) => (
          <Animated.View
            key={f.label}
            entering={FadeIn.delay(120 + i * 70).duration(360)}
            style={styles.chip}
          >
            <View style={styles.chipIcon}>
              <Ionicons name={f.icon} size={18} color="#000000" />
            </View>
            <Text style={styles.chipLabel}>{f.label}</Text>
          </Animated.View>
        ))}
      </View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    alignItems: 'center',
    gap: 28,
  },
  badge: {
    width: 88,
    height: 88,
    borderRadius: 44,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#000000',
    shadowColor: '#000000',
    shadowOpacity: 0.2,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 8 },
    elevation: 8,
  },
  grid: {
    width: '100%',
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 10,
    maxWidth: 320,
  },
  chip: {
    width: '47%',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingHorizontal: 14,
    paddingVertical: 14,
    borderRadius: 18,
    backgroundColor: '#FFFFFF',
    shadowColor: '#000000',
    shadowOpacity: 0.06,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 2,
  },
  chipIcon: {
    width: 34,
    height: 34,
    borderRadius: 17,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#F2F2F7',
  },
  chipLabel: {
    flex: 1,
    fontFamily: fonts.semiBold,
    fontSize: 14,
    color: '#000000',
  },
});

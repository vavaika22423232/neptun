import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { Text } from '../../../components/Text';
import { paywall } from '../theme/paywallTokens';
import { fonts } from '../../../theme/fonts';

type Preview = {
  icon: ComponentProps<typeof Ionicons>['name'];
  title: string;
  subtitle: string;
  accent: string;
  variant: 'radar' | 'map' | 'chat';
};

const PREVIEWS: Preview[] = [
  {
    icon: 'radio-outline',
    title: 'Радар PRO',
    subtitle: 'Групи загроз і метадані',
    accent: '#8FD4FA',
    variant: 'radar',
  },
  {
    icon: 'map-outline',
    title: 'Карта',
    subtitle: 'Шари та траєкторії',
    accent: '#A78BFA',
    variant: 'map',
  },
  {
    icon: 'chatbubbles-outline',
    title: 'Чат',
    subtitle: 'Теми та без реклами',
    accent: '#34D399',
    variant: 'chat',
  },
];

export function PremiumPreviewCarousel() {
  return (
    <Animated.View entering={FadeInDown.delay(100).duration(320)} style={styles.wrap}>
      <Text style={styles.heading}>Як виглядає PRO</Text>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.scroll}
        decelerationRate="fast"
      >
        {PREVIEWS.map((p) => (
          <View key={p.title} style={styles.card}>
            <View style={styles.cardHeader}>
              <View style={[styles.iconPlate, { backgroundColor: p.accent + '22' }]}>
                <Ionicons name={p.icon} size={16} color={p.accent} />
              </View>
              <View style={styles.cardTitles}>
                <Text style={styles.cardTitle}>{p.title}</Text>
                <Text style={styles.cardSub}>{p.subtitle}</Text>
              </View>
            </View>
            <PreviewMock variant={p.variant} accent={p.accent} />
          </View>
        ))}
      </ScrollView>
    </Animated.View>
  );
}

function PreviewMock({ variant, accent }: { variant: Preview['variant']; accent: string }) {
  if (variant === 'radar') {
    return (
      <View style={styles.mock}>
        {[0, 1, 2].map((i) => (
          <View key={i} style={styles.mockRow}>
            <View style={[styles.mockDot, { backgroundColor: accent }]} />
            <View style={styles.mockLine} />
            <View style={[styles.mockPill, { borderColor: accent + '44' }]} />
          </View>
        ))}
      </View>
    );
  }
  if (variant === 'map') {
    return (
      <View style={[styles.mock, styles.mockMap]}>
        <View style={[styles.mockMapGrid, { borderColor: accent + '33' }]} />
        <View style={[styles.mockMapPin, { backgroundColor: accent }]} />
        <View style={styles.mockMapChip} />
      </View>
    );
  }
  return (
    <View style={styles.mock}>
      <View style={[styles.mockBubbleL, { backgroundColor: accent + '28', borderColor: accent + '44' }]} />
      <View style={styles.mockBubbleR} />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: 12 },
  heading: {
    fontFamily: fonts.semiBold,
    fontSize: 12,
    letterSpacing: 0.9,
    textTransform: 'uppercase',
    color: paywall.textFaint,
    paddingLeft: 4,
  },
  scroll: {
    gap: 12,
    paddingRight: paywall.inset,
  },
  card: {
    width: 248,
    borderRadius: 20,
    padding: 14,
    backgroundColor: paywall.surfaceStrong,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: paywall.border,
    ...paywall.shadows.sm,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginBottom: 12,
  },
  iconPlate: {
    width: 32,
    height: 32,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  cardTitles: { flex: 1 },
  cardTitle: {
    fontFamily: fonts.semiBold,
    fontSize: 14,
    color: paywall.text,
  },
  cardSub: {
    marginTop: 2,
    fontSize: 11,
    color: paywall.textMuted,
  },
  mock: {
    height: 88,
    borderRadius: 14,
    backgroundColor: 'rgba(0,0,0,0.22)',
    padding: 10,
    gap: 8,
    overflow: 'hidden',
  },
  mockRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  mockDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  mockLine: {
    flex: 1,
    height: 6,
    borderRadius: 3,
    backgroundColor: 'rgba(255,255,255,0.08)',
  },
  mockPill: {
    width: 28,
    height: 18,
    borderRadius: 9,
    borderWidth: 1,
    backgroundColor: 'rgba(255,255,255,0.04)',
  },
  mockMap: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  mockMapGrid: {
    ...StyleSheet.absoluteFillObject,
    borderWidth: 1,
    opacity: 0.5,
  },
  mockMapPin: {
    width: 12,
    height: 12,
    borderRadius: 6,
    marginBottom: 8,
  },
  mockMapChip: {
    position: 'absolute',
    bottom: 10,
    left: 10,
    width: 64,
    height: 22,
    borderRadius: 11,
    backgroundColor: 'rgba(255,255,255,0.1)',
  },
  mockBubbleL: {
    width: '72%',
    height: 28,
    borderRadius: 12,
    borderWidth: 1,
  },
  mockBubbleR: {
    alignSelf: 'flex-end',
    width: '55%',
    height: 22,
    borderRadius: 11,
    marginTop: 8,
    backgroundColor: 'rgba(255,255,255,0.07)',
  },
});

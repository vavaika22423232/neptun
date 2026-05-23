import { Ionicons } from '@expo/vector-icons';
import { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import Animated, { FadeIn, FadeInDown, FadeOut } from 'react-native-reanimated';
import { Text } from '../../../components/Text';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { PAYWALL_FAQ, paywall } from '../theme/paywallTokens';
import { fonts } from '../../../theme/fonts';

export function PremiumFaqSection() {
  const [open, setOpen] = useState<number | null>(0);

  return (
    <Animated.View entering={FadeInDown.delay(240).duration(300)} style={styles.wrap}>
      <Text style={styles.heading}>Питання</Text>
      <View style={styles.card}>
        {PAYWALL_FAQ.map((item, i) => {
          const expanded = open === i;
          return (
            <View key={item.q} style={[i > 0 && styles.itemBorder]}>
              <NeptunPressable
                haptic={false}
                onPress={() => setOpen(expanded ? null : i)}
                style={styles.questionRow}
              >
                <Text style={styles.question}>{item.q}</Text>
                <Ionicons
                  name={expanded ? 'chevron-up' : 'chevron-down'}
                  size={18}
                  color={paywall.textFaint}
                />
              </NeptunPressable>
              {expanded ? (
                <Animated.View entering={FadeIn.duration(180)} exiting={FadeOut.duration(120)} style={styles.answerWrap}>
                  <Text style={styles.answer}>{item.a}</Text>
                </Animated.View>
              ) : null}
            </View>
          );
        })}
      </View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: 14 },
  heading: {
    fontFamily: fonts.semiBold,
    fontSize: 12,
    letterSpacing: 0.9,
    textTransform: 'uppercase',
    color: paywall.textFaint,
    paddingLeft: 4,
  },
  card: {
    borderRadius: paywall.radiusCard,
    backgroundColor: paywall.surface,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: paywall.border,
    overflow: 'hidden',
  },
  itemBorder: {
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: paywall.divider,
  },
  questionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 16,
    paddingVertical: 15,
  },
  question: {
    flex: 1,
    fontFamily: fonts.semiBold,
    fontSize: 14,
    color: paywall.text,
    lineHeight: 20,
  },
  answerWrap: {
    paddingHorizontal: 16,
    paddingBottom: 16,
    paddingTop: 0,
  },
  answer: {
    fontFamily: fonts.regular,
    fontSize: 13,
    lineHeight: 20,
    color: paywall.textMuted,
  },
});

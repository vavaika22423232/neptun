import * as Linking from 'expo-linking';
import { useRouter } from 'expo-router';
import { useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, View } from 'react-native';
import { Text } from '../../../components/Text';
import { appConfig } from '../../../config/appConfig';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import type { PlanId } from '../../monetization/types';
import {
  IAP_MAX_MONTHLY,
  IAP_PRO_MONTHLY,
  IAP_PRO_PLUS_MONTHLY,
  PLAN_PRICES_UAH,
} from '../../monetization/constants/iapProducts';
import { monetizationAnalytics } from '../../monetization/services/monetizationAnalytics';
import { usePaywallTheme, getPaywallTokens } from '../theme/paywallTokens';
import { useThemedStyles } from '../../../theme/useAppTheme';
import { fonts } from '../../../theme/fonts';
import { purchaseService } from '../../../services/purchaseService';
import { monetizationConfigService } from '../../monetization/services/monetizationConfigService';

type PaidPlanId = Exclude<PlanId, 'free'>;

type TierSpec = {
  id: PlanId;
  title: string;
  price: string;
  cadence?: string;
  badge?: string;
  description: string;
  productId?: string;
  highlighted?: boolean;
};

const PAID_TIERS: Array<TierSpec & { id: PaidPlanId; productId: string }> = [
  {
    id: 'pro',
    title: 'PRO',
    price: `${PLAN_PRICES_UAH.pro} грн`,
    cadence: '/ місяць',
    description: 'Без реклами, обрані регіони, тихі години, базова історія та персональні сповіщення.',
    productId: IAP_PRO_MONTHLY,
  },
  {
    id: 'pro_plus',
    title: 'PRO+',
    price: `${PLAN_PRICES_UAH.pro_plus} грн`,
    cadence: '/ місяць',
    badge: 'Popular',
    highlighted: true,
    description: 'Розширена історія, аналітика, до 10 локацій, зводки та глибші картки подій.',
    productId: IAP_PRO_PLUS_MONTHLY,
  },
  {
    id: 'max',
    title: 'MAX',
    price: `${PLAN_PRICES_UAH.max} грн`,
    cadence: '/ місяць',
    badge: 'Power',
    description: 'Професійний моніторинг, Telegram Admin Mode, експорт зводок і ранній доступ.',
    productId: IAP_MAX_MONTHLY,
  },
];

type Props = {
  onRestore: () => void;
  restoring: boolean;
  hideHero?: boolean;
  lockedFeature?: string;
};

export function PremiumTierPaywall({ onRestore, restoring, hideHero, lockedFeature }: Props) {
  const router = useRouter();
  const remote = monetizationConfigService.get();
  const paywall = usePaywallTheme();
  const visiblePaidTiers = useMemo(
    () =>
      PAID_TIERS.filter((tier) => {
        if (tier.id === 'pro_plus' && !remote.enableProPlus) return false;
        if (tier.id === 'max' && !remote.enableMaxPlan) return false;
        return remote.enableProPaywall || tier.id === 'pro';
      }).map((tier) => ({
        ...tier,
        badge:
          tier.id === 'pro_plus'
            ? remote.paywall.proPlusBadge || tier.badge
            : tier.badge,
      })),
    [remote],
  );
  const defaultSelected = visiblePaidTiers.find((tier) => tier.highlighted)?.id ?? visiblePaidTiers[0]?.id ?? 'free';
  const [selectedPlan, setSelectedPlan] = useState<PlanId>(defaultSelected);
  const [loadingPlan, setLoadingPlan] = useState<PlanId | null>(null);

  const plans = useMemo<TierSpec[]>(
    () => [
      {
        id: 'free',
        title: 'Free',
        price: 'Безкоштовно',
        description: 'Базові сповіщення та live-карта для щоденного користування без підписки.',
      },
      ...visiblePaidTiers,
    ],
    [visiblePaidTiers],
  );

  const selectedPaidPlan = visiblePaidTiers.find((tier) => tier.id === selectedPlan);
  const ctaDisabled = loadingPlan != null || (selectedPlan !== 'free' && !selectedPaidPlan);

  const styles = useThemedStyles((t) => {
    const pw = getPaywallTokens(t);
    return StyleSheet.create({
      root: {
        width: '100%',
        maxWidth: 430,
        alignSelf: 'center',
        gap: 18,
      },
      hero: {
        gap: 10,
        paddingTop: 4,
      },
      eyebrow: {
        fontFamily: fonts.semiBold,
        fontSize: 12,
        lineHeight: 16,
        color: pw.accent,
        letterSpacing: 0,
      },
      title: {
        fontFamily: fonts.bold,
        fontSize: 32,
        lineHeight: 38,
        color: pw.text,
        letterSpacing: 0,
      },
      sub: {
        maxWidth: 330,
        fontFamily: fonts.medium,
        fontSize: 15,
        lineHeight: 22,
        color: pw.textMuted,
      },
      segmented: {
        height: 42,
        flexDirection: 'row',
        alignItems: 'center',
        borderRadius: 999,
        backgroundColor: pw.surface,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: pw.border,
        padding: 3,
      },
      segment: {
        flex: 1,
        height: 36,
        borderRadius: 999,
        alignItems: 'center',
        justifyContent: 'center',
      },
      segmentActive: {
        backgroundColor: pw.text,
      },
      segmentDisabled: {
        opacity: 0.46,
      },
      segmentText: {
        fontFamily: fonts.semiBold,
        fontSize: 13,
        color: pw.textMuted,
      },
      segmentTextActive: {
        color: pw.bg,
      },
      planList: {
        gap: 12,
      },
      planCard: {
        minHeight: 118,
        borderRadius: 18,
        borderWidth: 1,
        borderColor: pw.border,
        backgroundColor: pw.surfaceStrong,
        padding: 15,
        gap: 10,
      },
      planCardSelected: {
        borderColor: pw.text,
        backgroundColor: pw.text,
      },
      planTop: {
        flexDirection: 'row',
        alignItems: 'flex-start',
        gap: 12,
      },
      planText: {
        flex: 1,
        gap: 4,
      },
      planTitle: {
        fontFamily: fonts.bold,
        fontSize: 20,
        lineHeight: 24,
        color: pw.text,
        letterSpacing: 0,
      },
      planTitleSelected: {
        color: pw.bg,
      },
      priceLine: {
        flexDirection: 'row',
        alignItems: 'baseline',
        flexWrap: 'wrap',
        columnGap: 4,
      },
      price: {
        fontFamily: fonts.bold,
        fontSize: 16,
        lineHeight: 20,
        color: pw.text,
      },
      priceSelected: {
        color: pw.bg,
      },
      cadence: {
        fontFamily: fonts.medium,
        fontSize: 12,
        color: pw.textMuted,
      },
      cadenceSelected: {
        color: 'rgba(0,0,0,0.58)',
      },
      description: {
        fontFamily: fonts.regular,
        fontSize: 13,
        lineHeight: 19,
        color: pw.textMuted,
      },
      descriptionSelected: {
        color: 'rgba(0,0,0,0.62)',
      },
      badge: {
        alignSelf: 'flex-start',
        borderRadius: 999,
        paddingHorizontal: 10,
        paddingVertical: 5,
        backgroundColor: pw.bg,
      },
      badgeSelected: {
        backgroundColor: 'rgba(0,0,0,0.12)',
      },
      badgeText: {
        fontFamily: fonts.bold,
        fontSize: 11,
        lineHeight: 13,
        color: pw.text,
      },
      badgeTextSelected: {
        color: pw.bg,
      },
      radio: {
        width: 24,
        height: 24,
        borderRadius: 999,
        borderWidth: 1,
        borderColor: pw.borderStrong,
        alignItems: 'center',
        justifyContent: 'center',
      },
      radioSelected: {
        borderColor: pw.bg,
        backgroundColor: pw.bg,
      },
      check: {
        width: 9,
        height: 14,
        borderRightWidth: 2,
        borderBottomWidth: 2,
        borderColor: pw.text,
        transform: [{ rotate: '45deg' }],
        marginTop: -2,
      },
      actions: {
        gap: 14,
        paddingTop: 18,
      },
      continueButton: {
        minHeight: 54,
        borderRadius: 999,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: pw.text,
        paddingHorizontal: 20,
      },
      continueButtonDisabled: {
        opacity: 0.52,
      },
      continueText: {
        fontFamily: fonts.bold,
        fontSize: 17,
        lineHeight: 22,
        color: pw.bg,
      },
      restoreButton: {
        alignSelf: 'center',
        minHeight: 36,
        justifyContent: 'center',
        paddingHorizontal: 12,
      },
      restoreText: {
        fontFamily: fonts.semiBold,
        fontSize: 14,
        color: pw.text,
      },
      skipButton: {
        alignSelf: 'center',
        minHeight: 34,
        justifyContent: 'center',
        paddingHorizontal: 12,
      },
      skipText: {
        fontFamily: fonts.bold,
        fontSize: 15,
        color: pw.textMuted,
      },
      legal: {
        fontFamily: fonts.regular,
        fontSize: 11,
        lineHeight: 17,
        color: pw.textFaint,
        textAlign: 'center',
      },
      link: {
        color: pw.textMuted,
        textDecorationLine: 'underline',
      },
    });
  });

  async function buySelectedPlan() {
    if (selectedPlan === 'free') {
      router.back();
      return;
    }
    const tier = visiblePaidTiers.find((item) => item.id === selectedPlan);
    if (!tier) return;

    monetizationAnalytics.paywallPlanSelected(tier.id);
    monetizationAnalytics.purchaseStarted(tier.id, tier.productId);
    setLoadingPlan(tier.id);
    const ok = await purchaseService.buyTier(tier.productId);
    setLoadingPlan(null);
    if (!ok) monetizationAnalytics.purchaseFailed('purchase_not_started');
  }

  return (
    <View style={styles.root}>
      {!hideHero ? (
        <View style={styles.hero}>
          {lockedFeature ? <Text style={styles.eyebrow}>Для цієї функції потрібен PRO</Text> : null}
          <Text style={styles.title}>Оберіть план</Text>
          <Text style={styles.sub}>
            Підписка відкриває спокійніший Neptun: менше шуму, більше контролю та точніші зводки.
          </Text>
        </View>
      ) : (
        <View style={styles.hero}>
          {lockedFeature ? <Text style={styles.eyebrow}>Для цієї функції потрібен PRO</Text> : null}
          <Text style={styles.title}>Оберіть план</Text>
        </View>
      )}

      <View style={styles.segmented} accessibilityRole="tablist">
        <View style={[styles.segment, styles.segmentActive]}>
          <Text style={[styles.segmentText, styles.segmentTextActive]}>Місячно</Text>
        </View>
        <View style={[styles.segment, styles.segmentDisabled]}>
          <Text style={styles.segmentText}>Річно</Text>
        </View>
      </View>

      <View style={styles.planList}>
        {plans.map((plan) => {
          const selected = plan.id === selectedPlan;
          const loading = loadingPlan === plan.id;
          return (
            <NeptunPressable
              key={plan.id}
              accessibilityRole="radio"
              accessibilityState={{ checked: selected }}
              haptic
              scaleTo={0.985}
              onPress={() => setSelectedPlan(plan.id)}
              style={[styles.planCard, selected && styles.planCardSelected]}
            >
              <View style={styles.planTop}>
                <View style={styles.planText}>
                  <Text style={[styles.planTitle, selected && styles.planTitleSelected]}>{plan.title}</Text>
                  <View style={styles.priceLine}>
                    <Text style={[styles.price, selected && styles.priceSelected]}>{plan.price}</Text>
                    {plan.cadence ? (
                      <Text style={[styles.cadence, selected && styles.cadenceSelected]}>{plan.cadence}</Text>
                    ) : null}
                  </View>
                </View>
                {plan.badge ? (
                  <View style={[styles.badge, selected && styles.badgeSelected]}>
                    <Text style={[styles.badgeText, selected && styles.badgeTextSelected]}>{plan.badge}</Text>
                  </View>
                ) : null}
                <View style={[styles.radio, selected && styles.radioSelected]}>
                  {selected ? loading ? <ActivityIndicator color={paywall.text} size="small" /> : <View style={styles.check} /> : null}
                </View>
              </View>
              <Text style={[styles.description, selected && styles.descriptionSelected]}>{plan.description}</Text>
            </NeptunPressable>
          );
        })}
      </View>

      <View style={styles.actions}>
        <NeptunPressable
          disabled={ctaDisabled}
          haptic={!ctaDisabled}
          onPress={() => void buySelectedPlan()}
          style={[styles.continueButton, ctaDisabled && styles.continueButtonDisabled]}
        >
          <Text style={styles.continueText}>
            {loadingPlan ? 'Очікування…' : selectedPlan === 'free' ? 'Продовжити без PRO' : 'Continue'}
          </Text>
        </NeptunPressable>

        <Pressable style={styles.restoreButton} onPress={onRestore} disabled={restoring}>
          <Text style={styles.restoreText}>{restoring ? 'Відновлення…' : 'Відновити покупки'}</Text>
        </Pressable>

        <Pressable style={styles.skipButton} onPress={() => router.back()}>
          <Text style={styles.skipText}>Skip</Text>
        </Pressable>

        <Text style={styles.legal}>
          Оплата через App Store / Google Play. Підписка поновлюється автоматично, доки не скасуєте її в
          налаштуваннях магазину.{' '}
          <Text style={styles.link} onPress={() => void Linking.openURL(appConfig.termsUrl)}>
            Умови
          </Text>
          {' · '}
          <Text style={styles.link} onPress={() => void Linking.openURL(appConfig.privacyUrl)}>
            Конфіденційність
          </Text>
        </Text>
      </View>
    </View>
  );
}

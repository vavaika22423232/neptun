import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useNavigation } from '@react-navigation/native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Alert, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Text } from '../components/Text';
import { CHAT_THEME_DEFAULT_ID, chatThemeById } from '../config/chatThemes';
import { useApp } from '../context/AppContext';
import { PremiumMemberHub } from '../features/premium/components/PremiumMemberHub';
import { PremiumPaywallBackground } from '../features/premium/components/PremiumPaywallBackground';
import { PremiumPaywallHeader } from '../features/premium/components/PremiumPaywallHeader';
import { PremiumPaywallHero } from '../features/premium/components/PremiumPaywallHero';
import { PremiumTierPaywall } from '../features/premium/components/PremiumTierPaywall';
import { monetizationAnalytics } from '../features/monetization/services/monetizationAnalytics';
import { PremiumThankYouModal } from '../features/premium/components/PremiumThankYouModal';
import { PremiumThemeModal } from '../features/premium/components/PremiumThemeModal';
import { usePremiumStore } from '../features/premium/hooks/usePremiumStore';
import { getPaywallTokens, usePaywallTheme } from '../features/premium/theme/paywallTokens';
import { useThemedStyles } from '../theme/useAppTheme';
import type { RootStackParamList } from '../navigation/types';
import { purchaseService } from '../services/purchaseService';
import { storage } from '../services/storage';
import { fonts } from '../theme/fonts';

export function PremiumScreen() {
  const insets = useSafeAreaInsets();
  const paywall = usePaywallTheme();
  const styles = useThemedStyles((t) => {
    const pw = getPaywallTokens(t);
    return StyleSheet.create({
      root: {
        flex: 1,
        backgroundColor: pw.bg,
      },
      centered: {
        alignItems: 'center',
        justifyContent: 'center',
        gap: 14,
      },
      loadingText: {
        marginTop: 8,
        fontFamily: fonts.medium,
        fontSize: 14,
        color: pw.textMuted,
      },
      scroll: {
        paddingHorizontal: pw.inset,
        gap: pw.sectionGap,
      },
      paywallBody: {
        gap: pw.sectionGap,
      },
      legal: {
        fontFamily: fonts.regular,
        fontSize: 12,
        lineHeight: 18,
        color: pw.textFaint,
        textAlign: 'center',
      },
      devLink: { alignSelf: 'center', paddingVertical: 8 },
      devNote: { fontSize: 11, textAlign: 'center', color: pw.textFaint },
    });
  });
  const router = useRouter();
  const params = useLocalSearchParams<{ source?: string; feature?: string }>();
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const { isPremium } = useApp();
  const premium = usePremiumStore();
  const [themeId, setThemeIdState] = useState(CHAT_THEME_DEFAULT_ID);
  const [animAvatar, setAnimAvatarState] = useState(false);
  const [themeModal, setThemeModal] = useState(false);

  const paywallSource =
    typeof params.source === 'string' && params.source.length > 0
      ? params.source
      : 'premium_screen';
  const lockedFeature =
    typeof params.feature === 'string' && params.feature.length > 0
      ? params.feature
      : undefined;

  useEffect(() => {
    monetizationAnalytics.paywallOpened(paywallSource);
    return () => monetizationAnalytics.paywallClosed();
  }, [paywallSource]);

  useEffect(() => {
    if (!premium.error) return;
    monetizationAnalytics.purchaseFailed(premium.error);
    Alert.alert('Помилка', premium.error, [{ text: 'OK', onPress: premium.clearError }]);
  }, [premium.error, premium.clearError]);

  const refreshPrefs = useCallback(async () => {
    const tid = (await storage.getProChatThemeId()) || CHAT_THEME_DEFAULT_ID;
    setThemeIdState(chatThemeById(tid).id);
    setAnimAvatarState(await storage.getProAnimatedAvatar());
  }, []);

  useEffect(() => {
    void refreshPrefs();
  }, [refreshPrefs]);

  const goProfileSoundSection = useCallback(() => {
    navigation.navigate('MainTabs', { screen: 'Profile' });
    navigation.goBack();
  }, [navigation]);

  if (premium.isLoading && !premium.isPurchasing && !isPremium) {
    return (
      <View style={[styles.root, styles.centered, { paddingTop: insets.top }]}>
        <PremiumPaywallBackground />
        <ActivityIndicator color={paywall.accent} size="large" />
        <Text muted style={styles.loadingText}>
          Завантаження…
        </Text>
      </View>
    );
  }

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      <PremiumPaywallBackground />

      <PremiumPaywallHeader
        onClose={() => router.back()}
        showRestore={!isPremium}
        onRestore={() => void premium.restorePurchases()}
      />

      <ScrollView
        contentContainerStyle={[
          styles.scroll,
          { paddingBottom: insets.bottom + (isPremium ? 32 : 128) },
        ]}
        showsVerticalScrollIndicator={false}
      >
        {isPremium ? <PremiumPaywallHero isMember /> : null}

        {isPremium ? (
          <PremiumMemberHub
            navigation={navigation}
            themeLabel={chatThemeById(themeId).label}
            animAvatar={animAvatar}
            onThemePress={() => setThemeModal(true)}
            onAnimAvatarChange={(v) => {
              setAnimAvatarState(v);
              void storage.setProAnimatedAvatar(v);
            }}
            onProfileSounds={goProfileSoundSection}
          />
        ) : (
          <View style={styles.paywallBody}>
            <PremiumTierPaywall
              hideHero
              lockedFeature={lockedFeature}
              restoring={premium.isPurchasing}
              onRestore={() => {
                monetizationAnalytics.restoreClicked();
                void premium.restorePurchases().then(() => monetizationAnalytics.restoreSuccess('pro'));
              }}
            />
            {__DEV__ && process.env.EXPO_PUBLIC_DEBUG_PRO === 'true' ? (
              <Pressable style={styles.devLink} onPress={() => void purchaseService.enableLocalPro()}>
                <Text muted style={styles.devNote}>
                  Debug: увімкнути локальний PRO
                </Text>
              </Pressable>
            ) : null}
          </View>
        )}
      </ScrollView>

      <PremiumThankYouModal visible={premium.showThankYou} onDismiss={premium.dismissThankYou} />

      <PremiumThemeModal
        visible={themeModal}
        themeId={themeId}
        onClose={() => setThemeModal(false)}
        onSelect={(id) => {
          setThemeIdState(id);
          void storage.setProChatThemeId(id);
          setThemeModal(false);
        }}
      />
    </View>
  );
}

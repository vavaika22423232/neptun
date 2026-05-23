import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useCallback, useRef, useState } from 'react';
import { FlatList, StyleSheet, useWindowDimensions, View } from 'react-native';
import Animated, { FadeIn, FadeOut, useSharedValue } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Text } from '../components/Text';
import { PrefsKeys } from '../config/prefsKeys';
import { NeptunPressable } from '../design/components/NeptunPressable';
import { AnimatedPageDots } from '../features/onboarding/components/AnimatedPageDots';
import { OnboardingLockScreenHero } from '../features/onboarding/components/OnboardingLockScreenHero';
import { OnboardingOrbitHero } from '../features/onboarding/components/OnboardingOrbitHero';
import {
  OnboardingPager,
  scrollOnboardingToPage,
} from '../features/onboarding/components/OnboardingPager';
import { OnboardingPillButton } from '../features/onboarding/components/OnboardingPillButton';
import { OnboardingReadyHero } from '../features/onboarding/components/OnboardingReadyHero';
import {
  ONBOARDING_REGIONS,
  ONBOARDING_TOTAL_PAGES,
} from '../features/onboarding/constants/regions';
import { fullNamesFromOnboardingSelection } from '../features/onboarding/utils/regionNames';
import {
  isPushNotificationsSupported,
  notificationService,
} from '../services/notificationService';
import { persistentStorage } from '../services/persistentStorage';
import { fonts } from '../theme/fonts';

const CANVAS = '#F2F2F7';

export function OnboardingScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const pagerRef = useRef<FlatList<number>>(null);
  const scrollX = useSharedValue(0);
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [notifGranted, setNotifGranted] = useState(false);
  const [finishing, setFinishing] = useState(false);

  const goToPage = useCallback(
    (index: number) => {
      const clamped = Math.min(ONBOARDING_TOTAL_PAGES - 1, Math.max(0, index));
      setPage(clamped);
      scrollOnboardingToPage(pagerRef, clamped, width);
    },
    [width],
  );

  const finish = useCallback(async () => {
    if (finishing) return;
    setFinishing(true);
    try {
      persistentStorage.setBoolean(PrefsKeys.firstLaunch, false);
      if (selected.size > 0) {
        const first = [...selected][0];
        persistentStorage.setString('onboarding_region', first);
        const full = fullNamesFromOnboardingSelection(selected);
        persistentStorage.setStringList(PrefsKeys.selectedRegions, full);
        await Promise.race([
          notificationService.updateRegions(full),
          new Promise((r) => setTimeout(r, 5000)),
        ]);
      }
      router.replace('/(tabs)');
    } catch {
      router.replace('/(tabs)');
    }
  }, [finishing, router, selected]);

  const next = useCallback(() => {
    if (page < ONBOARDING_TOTAL_PAGES - 1) goToPage(page + 1);
    else void finish();
  }, [page, finish, goToPage]);

  const requestNotifications = useCallback(async () => {
    if (!isPushNotificationsSupported()) {
      next();
      return;
    }
    const token = await notificationService.registerForPushNotifications();
    setNotifGranted(!!token);
    next();
  }, [next]);

  const toggleRegion = (name: string) => {
    setSelected((prev) => {
      const nextSet = new Set(prev);
      if (nextSet.has(name)) nextSet.delete(name);
      else nextSet.add(name);
      return nextSet;
    });
  };

  const toggleAllRegions = () => {
    setSelected((prev) =>
      prev.size === ONBOARDING_REGIONS.length ? new Set() : new Set(ONBOARDING_REGIONS),
    );
  };

  const showFooterCta = page === 0 || page === ONBOARDING_TOTAL_PAGES - 1;
  const pagerScrollEnabled = page !== 1;

  const renderPage = useCallback(
    (index: number) => {
      switch (index) {
        case 0:
          return <WelcomePage />;
        case 1:
          return (
            <RegionsPage
              selected={selected}
              onToggle={toggleRegion}
              onToggleAll={toggleAllRegions}
              onNext={next}
            />
          );
        case 2:
          return (
            <NotificationsPage
              granted={notifGranted}
              onEnable={() => void requestNotifications()}
              onLater={next}
            />
          );
        case 3:
          return <ReadyPage />;
        default:
          return null;
      }
    },
    [next, notifGranted, requestNotifications, selected, toggleAllRegions, toggleRegion],
  );

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      <View style={styles.topBar}>
        {page < ONBOARDING_TOTAL_PAGES - 1 ? (
          <NeptunPressable haptic={false} onPress={() => void finish()} style={styles.skipHit}>
            <Text style={styles.skipText}>Пропустити</Text>
          </NeptunPressable>
        ) : (
          <View />
        )}
      </View>

      <OnboardingPager
        pagerRef={pagerRef}
        page={page}
        totalPages={ONBOARDING_TOTAL_PAGES}
        scrollEnabled={pagerScrollEnabled}
        scrollX={scrollX}
        onPageChange={setPage}
        renderPage={renderPage}
      />

      <View style={[styles.footer, { paddingBottom: Math.max(insets.bottom, 20) + 12 }]}>
        <AnimatedPageDots
          total={ONBOARDING_TOTAL_PAGES}
          scrollX={scrollX}
          pageWidth={Math.max(width, 1)}
        />
        {showFooterCta ? (
          <Animated.View
            entering={FadeIn.duration(220)}
            exiting={FadeOut.duration(180)}
            style={styles.footerCta}
          >
            <OnboardingPillButton
              label={page === ONBOARDING_TOTAL_PAGES - 1 ? (finishing ? '…' : 'Почати') : 'Чудово!'}
              onPress={next}
              disabled={finishing}
              loading={finishing && page === ONBOARDING_TOTAL_PAGES - 1}
            />
          </Animated.View>
        ) : (
          <View style={styles.footerSpacer} />
        )}
      </View>
    </View>
  );
}

function WelcomePage() {
  return (
    <View style={styles.heroPage}>
      <View style={styles.heroVisual}>
        <OnboardingOrbitHero />
      </View>
      <View style={styles.copyBlock}>
        <Text style={styles.title}>Разом безпечніше</Text>
        <Text style={styles.subtitle}>
          Тисячі людей уже отримують миттєві попередження, live-карту та перевірений чат.
        </Text>
      </View>
    </View>
  );
}

function RegionsPage({
  selected,
  onToggle,
  onToggleAll,
  onNext,
}: {
  selected: Set<string>;
  onToggle: (name: string) => void;
  onToggleAll: () => void;
  onNext: () => void;
}) {
  const allSelected = selected.size === ONBOARDING_REGIONS.length;

  return (
    <View style={styles.regionPage}>
      <View style={styles.regionHeader}>
        <View style={styles.regionIcon}>
          <Ionicons name="location-outline" size={28} color="#000000" />
        </View>
        <Text style={styles.title}>Оберіть регіони</Text>
        <Text style={styles.subtitle}>Сповіщення лише для обраних зон — без зайвого шуму.</Text>
      </View>
      <FlatList
        data={['__all__', ...ONBOARDING_REGIONS]}
        keyExtractor={(item) => item}
        style={styles.regionList}
        contentContainerStyle={styles.regionListContent}
        showsVerticalScrollIndicator={false}
        renderItem={({ item }) => {
          if (item === '__all__') {
            return (
              <NeptunPressable haptic onPress={onToggleAll}>
                <View style={[styles.regionRow, allSelected && styles.regionRowOn]}>
                  <Ionicons name="globe-outline" size={20} color={allSelected ? '#000000' : 'rgba(60,60,67,0.55)'} />
                  <Text style={[styles.regionName, allSelected && styles.regionNameOn]}>Всі регіони</Text>
                  {allSelected ? <Ionicons name="checkmark-circle" size={22} color="#000000" /> : null}
                </View>
              </NeptunPressable>
            );
          }
          const on = selected.has(item);
          return (
            <NeptunPressable haptic onPress={() => onToggle(item)}>
              <View style={[styles.regionRow, on && styles.regionRowOn]}>
                <Text style={[styles.regionName, on && styles.regionNameOn]}>{item}</Text>
                {on ? <Ionicons name="checkmark-circle" size={22} color="#000000" /> : null}
              </View>
            </NeptunPressable>
          );
        }}
      />
      <View style={styles.regionCta}>
        <OnboardingPillButton
          label={selected.size === 0 ? 'Пропустити' : `Далі${selected.size > 1 ? ` · ${selected.size}` : ''}`}
          onPress={onNext}
        />
      </View>
    </View>
  );
}

function NotificationsPage({
  granted,
  onEnable,
  onLater,
}: {
  granted: boolean;
  onEnable: () => void;
  onLater: () => void;
}) {
  return (
    <View style={styles.heroPage}>
      <View style={styles.heroVisual}>
        <OnboardingLockScreenHero />
      </View>
      <View style={styles.copyBlock}>
        <Text style={styles.title}>Не пропускайте{'\n'}важливі моменти</Text>
        <Text style={styles.subtitle}>
          Критичні тривоги надходять миттєво — навіть коли застосунок закритий.
        </Text>
      </View>
      <View style={styles.inlineActions}>
        <OnboardingPillButton
          label={granted ? 'Сповіщення увімкнено' : 'Увімкнути сповіщення'}
          onPress={granted ? onLater : onEnable}
        />
        {!granted ? (
          <NeptunPressable haptic={false} onPress={onLater} style={styles.laterHit}>
            <Text style={styles.later}>Пізніше</Text>
          </NeptunPressable>
        ) : null}
      </View>
    </View>
  );
}

function ReadyPage() {
  return (
    <View style={styles.heroPage}>
      <View style={styles.heroVisual}>
        <OnboardingReadyHero />
      </View>
      <View style={styles.copyBlock}>
        <Text style={styles.title}>Все готово</Text>
        <Text style={styles.subtitle}>
          Карта, Radar і спільнота — в одному спокійному, зрозумілому інтерфейсі.
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: CANVAS,
  },
  topBar: {
    minHeight: 44,
    paddingHorizontal: 20,
    alignItems: 'flex-end',
    justifyContent: 'center',
  },
  skipHit: {
    paddingHorizontal: 4,
    paddingVertical: 8,
  },
  skipText: {
    fontFamily: fonts.medium,
    fontSize: 15,
    color: 'rgba(60,60,67,0.55)',
  },
  footer: {
    paddingHorizontal: 24,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
  },
  footerCta: { flexShrink: 0 },
  footerSpacer: { width: 120 },
  heroPage: {
    flex: 1,
    paddingHorizontal: 28,
  },
  heroVisual: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingTop: 8,
    paddingBottom: 12,
  },
  copyBlock: {
    alignItems: 'center',
    gap: 10,
    paddingBottom: 8,
  },
  title: {
    textAlign: 'center',
    fontFamily: fonts.bold,
    fontSize: 28,
    lineHeight: 34,
    letterSpacing: -0.4,
    color: '#000000',
  },
  subtitle: {
    textAlign: 'center',
    fontFamily: fonts.regular,
    fontSize: 16,
    lineHeight: 22,
    color: 'rgba(60,60,67,0.72)',
    maxWidth: 320,
  },
  inlineActions: {
    width: '100%',
    gap: 14,
    paddingTop: 8,
    paddingBottom: 4,
  },
  laterHit: { alignSelf: 'center', paddingVertical: 4 },
  later: {
    fontFamily: fonts.medium,
    fontSize: 16,
    color: 'rgba(60,60,67,0.55)',
  },
  regionPage: { flex: 1 },
  regionHeader: {
    alignItems: 'center',
    paddingHorizontal: 24,
    gap: 10,
    paddingBottom: 8,
  },
  regionIcon: {
    width: 56,
    height: 56,
    borderRadius: 28,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#FFFFFF',
    shadowColor: '#000000',
    shadowOpacity: 0.06,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 2,
  },
  regionList: { flex: 1 },
  regionListContent: {
    paddingHorizontal: 20,
    paddingTop: 8,
    paddingBottom: 12,
    gap: 8,
  },
  regionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 16,
    paddingHorizontal: 18,
    borderRadius: 18,
    backgroundColor: '#FFFFFF',
    shadowColor: '#000000',
    shadowOpacity: 0.04,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
    elevation: 1,
  },
  regionRowOn: {
    backgroundColor: '#FFFFFF',
  },
  regionName: {
    flex: 1,
    fontSize: 16,
    fontFamily: fonts.medium,
    color: 'rgba(60,60,67,0.82)',
  },
  regionNameOn: {
    fontFamily: fonts.semiBold,
    color: '#000000',
  },
  regionCta: {
    paddingHorizontal: 20,
    paddingBottom: 8,
  },
});

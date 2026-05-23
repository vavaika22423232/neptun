import * as Linking from 'expo-linking';
import { useRouter, useSegments } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { AppState } from 'react-native';
import { BatteryOptModal } from './BatteryOptModal';
import { ChangelogModal } from './ChangelogModal';
import { useAppEngagementModals } from '../hooks/useAppEngagementModals';
import { resolveAppRedirectExpoHref } from '../core/navigation/appRedirect';
import { navigateToHref } from '../core/navigation/navigate';
import { expoHrefFromWidgetUri } from '../core/navigation/pushDeepLink';
import { consumePendingBallisticAlert } from '../features/notifications/services/fcmBallisticPending';
import { fcmMessagingService } from '../features/notifications/services/fcmMessagingService';
import { useAnalyticsScreenTracking } from '../hooks/useAnalyticsScreenTracking';
import { useAppShellBootstrap } from '../hooks/useAppShellBootstrap';
import { analyticsService } from '../services/analyticsService';
import {
  isPushNotificationsSupported,
  notificationService,
} from '../services/notificationService';
import { persistentStorage } from '../services/persistentStorage';
import { storage } from '../services/storage';
import { PrefsKeys } from '../config/prefsKeys';
import { remoteConfigService } from '../config/remoteConfig';
import { otaUpdateService } from '../services/otaUpdateService';
import { widgetService } from '../features/widgets/services/widgetService';

/**
 * Mirrors Flutter `resolveAppRedirect` + push deep-link wiring at app boot.
 */
export function AppBootstrapGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const segments = useSegments();
  const booted = useRef(false);
  const initialNavHandled = useRef(false);
  const [engagementEnabled, setEngagementEnabled] = useState(false);
  const engagement = useAppEngagementModals(engagementEnabled);

  useAppShellBootstrap();
  useAnalyticsScreenTracking();

  useEffect(() => {
    if (persistentStorage.getBoolean(PrefsKeys.firstLaunch, true)) return;
    if (segments[0] === 'onboarding') return;
    setEngagementEnabled(true);
  }, [segments]);

  useEffect(() => {
    if (!isPushNotificationsSupported()) return;
    notificationService.scheduleMorningBriefingIfNeeded();
    const sub = AppState.addEventListener('change', (state) => {
      if (state === 'active') notificationService.scheduleMorningBriefingIfNeeded();
    });
    return () => sub.remove();
  }, []);

  useEffect(() => {
    if (!isPushNotificationsSupported()) return;
    const navigate = (href: string) => navigateToHref(href, { replace: true });
    const navigateInitialOnce = (href: string) => {
      if (initialNavHandled.current) return;
      initialNavHandled.current = true;
      navigate(href);
    };
    notificationService.setNavigationHandler(navigate);
    fcmMessagingService.setNavigationHandler(navigate);
    const unsub = notificationService.subscribe();
    notificationService.handleInitialNotification(navigateInitialOnce);
    void fcmMessagingService.handleInitialNotification(navigateInitialOnce);
    return () => {
      unsub();
      notificationService.setNavigationHandler(null);
      fcmMessagingService.setNavigationHandler(null);
      fcmMessagingService.teardown();
    };
  }, [router]);

  useEffect(() => {
    const sub = Linking.addEventListener('url', ({ url }) => {
      const widgetHref = expoHrefFromWidgetUri(url);
      if (widgetHref) navigateToHref(widgetHref, { replace: true });
    });
    return () => sub.remove();
  }, []);

  useEffect(() => {
    if (booted.current) return;
    booted.current = true;

    void (async () => {
      await persistentStorage.hydrateFromAsyncStorage();
      void analyticsService.initialize();
      void widgetService.initialize();
      consumePendingBallisticAlert();
      void remoteConfigService.fetch();
      void otaUpdateService.checkAndFetchOnStartup();
      let first = persistentStorage.getBoolean(PrefsKeys.firstLaunch, true);
      if (first) {
        const legacy = await storage.getIsFirstLaunch();
        if (!legacy) first = false;
        persistentStorage.setBoolean(PrefsKeys.firstLaunch, first);
      }

      const initialUrl = await Linking.getInitialURL();
      const pathname = '/' + segments.join('/');
      const redirect = resolveAppRedirectExpoHref({
        isFirstLaunch: first,
        pathname,
        deepLinkUri: initialUrl,
      });

      if (redirect) {
        router.replace(redirect as never);
      } else if (initialUrl) {
        const widgetHref = expoHrefFromWidgetUri(initialUrl);
        if (widgetHref) router.replace(widgetHref as never);
      }

      if (isPushNotificationsSupported()) {
        void notificationService.registerForPushNotifications().then(() => {
          notificationService.scheduleMorningBriefingIfNeeded();
        });
      }
    })();
  }, [router, segments]);

  return (
    <>
      {children}
      <ChangelogModal
        visible={engagement.changelogVisible}
        items={engagement.changelogItems}
        onDismiss={engagement.dismissChangelog}
      />
      <BatteryOptModal
        visible={engagement.batteryVisible}
        onLater={engagement.dismissBattery}
        onOpenSettings={engagement.openBatterySettings}
      />
    </>
  );
}

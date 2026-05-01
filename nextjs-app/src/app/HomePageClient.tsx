'use client';

import { useState, useEffect } from 'react';
import type { Alarm, FusionTrajectory } from '@/types';
import { useAlarms } from '@/hooks/useAlarms';
import { useMarkers } from '@/hooks/useMarkers';
import { usePresence } from '@/hooks/usePresence';
import AppShell from '@/components/AppShell';
import DonateModal from '@/components/DonateModal';
import FaqModal from '@/components/FaqModal';
import DeploymentScreen from '@/components/DeploymentScreen';
import SeoInfoSection from '@/components/SeoInfoSection';
import MapErrorBoundary from '@/components/MapErrorBoundary';
import MapHost from '@/components/Map/MapHost';

export default function HomePageInner({
  isEmbed = false,
  initialAlarms = [],
  initialAlarmEtag = null,
}: {
  isEmbed?: boolean;
  initialAlarms?: Alarm[];
  initialAlarmEtag?: string | null;
}) {
  const { alarms } = useAlarms({ initialAlarms, initialEtag: initialAlarmEtag });
  const { markers, ballisticThreat, forceRefreshMarkers } = useMarkers();
  const presence = usePresence();

  const [donateOpen, setDonateOpen] = useState(false);
  const [faqOpen, setFaqOpen] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const [ukraineOnly, setUkraineOnly] = useState(false);

  useEffect(() => {
    if (!isEmbed) {
      let cancelled = false;
      const run = () => {
        if (cancelled) return;
        fetch('/api/admin/auth/check')
          .then((r) => r.json())
          .then((d) => {
            if (!cancelled && d.authenticated) setIsAdmin(true);
          })
          .catch(() => {});
      };
      const idleId =
        typeof requestIdleCallback !== 'undefined'
          ? requestIdleCallback(() => run(), { timeout: 3000 })
          : null;
      const timeoutId =
        idleId == null ? window.setTimeout(run, 1) : null;
      return () => {
        cancelled = true;
        if (idleId != null && typeof cancelIdleCallback !== 'undefined') {
          cancelIdleCallback(idleId);
        }
        if (timeoutId != null) window.clearTimeout(timeoutId);
      };
    }

    // Embed: session cookies often missing in app WebView. URL ?admin_secret= is one path;
    // Flutter MapTab injects window.__ADMIN_SECRET on page load — poll until it appears.
    let cancelled = false;
    const trySecret = (secret: string | null | undefined) => {
      if (!secret || cancelled) return;
      fetch('/api/admin/auth/check', {
        headers: { 'X-Auth-Secret': secret },
      })
        .then(r => r.json())
        .then(d => {
          if (!cancelled && d.authenticated) setIsAdmin(true);
        })
        .catch(() => {});
    };

    const params = new URLSearchParams(typeof window !== 'undefined' ? window.location.search : '');
    trySecret(params.get('admin_secret'));
    trySecret(
      typeof window !== 'undefined'
        ? (window as unknown as { __ADMIN_SECRET?: string }).__ADMIN_SECRET
        : undefined,
    );

    let attempts = 0;
    const intervalId = window.setInterval(() => {
      attempts += 1;
      const injected = (window as unknown as { __ADMIN_SECRET?: string }).__ADMIN_SECRET;
      if (injected) {
        trySecret(injected);
        window.clearInterval(intervalId);
      } else if (attempts >= 60) {
        window.clearInterval(intervalId);
      }
    }, 250);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [isEmbed]);

  const mapProps = {
    markers,
    alarms,
    fusionTrajectories: [] as FusionTrajectory[],
    isAdmin,
    onMarkerAction: isAdmin ? forceRefreshMarkers : undefined,
    ukraineOnly,
  };

  if (isEmbed) {
    return (
      <main className="relative h-screen h-[100dvh] w-full overflow-hidden">
        <div id="map-container" className="isolate h-full w-full">
          <MapErrorBoundary>
            <MapHost {...mapProps} isEmbed={isEmbed} />
          </MapErrorBoundary>
        </div>
      </main>
    );
  }

  return (
    <>
      <DeploymentScreen />

      <AppShell
        markers={markers}
        alarms={alarms}
        presence={presence}
        ballisticThreat={ballisticThreat}
        onDonate={() => setDonateOpen(true)}
        onFaq={() => setFaqOpen(true)}
        onToggleUkraineOnly={() => setUkraineOnly((value) => !value)}
        ukraineOnly={ukraineOnly}
      >
        <div id="map-container" className="isolate h-full w-full">
          <MapErrorBoundary>
            <MapHost {...mapProps} />
          </MapErrorBoundary>
        </div>
      </AppShell>

      <DonateModal isOpen={donateOpen} onClose={() => setDonateOpen(false)} />
      <FaqModal isOpen={faqOpen} onClose={() => setFaqOpen(false)} />

      <h1 className="seo-page-title hidden">
        Карта тривог і шахедів України онлайн — повітряна тривога, мапа тривог
      </h1>
      <SeoInfoSection />
    </>
  );
}

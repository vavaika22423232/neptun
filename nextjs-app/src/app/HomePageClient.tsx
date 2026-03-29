'use client';

import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import type { FusionTrajectory } from '@/types';
import { useAlarms } from '@/hooks/useAlarms';
import { useMarkers } from '@/hooks/useMarkers';
import { usePresence } from '@/hooks/usePresence';
import AppShell from '@/components/AppShell';
import DonateModal from '@/components/DonateModal';
import FaqModal from '@/components/FaqModal';
import DeploymentScreen from '@/components/DeploymentScreen';
import SeoInfoSection from '@/components/SeoInfoSection';
import MapErrorBoundary from '@/components/MapErrorBoundary';

const MapContainer = dynamic(() => import('@/components/Map/MapContainer'), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center">
      <div className="animate-pulse text-[10px] tracking-widest uppercase text-white/30">Завантаження радару…</div>
    </div>
  ),
});

export default function HomePageInner({ isEmbed = false }: { isEmbed?: boolean }) {
  const { alarms } = useAlarms();
  const { markers, ballisticThreat, forceRefreshMarkers } = useMarkers();
  const presence = usePresence();

  const [donateOpen, setDonateOpen] = useState(false);
  const [faqOpen, setFaqOpen] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    if (isEmbed) {
      const params = new URLSearchParams(typeof window !== 'undefined' ? window.location.search : '');
      const secret = params.get('admin_secret');
      if (secret) {
        fetch('/api/admin/auth/check', {
          headers: { 'X-Auth-Secret': secret },
        })
          .then(r => r.json())
          .then(d => {
            if (d.authenticated) setIsAdmin(true);
          })
          .catch(() => {});
      }
      return;
    }
    fetch('/api/admin/auth/check').then(r => r.json())
      .then(d => { if (d.authenticated) setIsAdmin(true); })
      .catch(() => {});
  }, [isEmbed]);

  const mapProps = {
    markers,
    alarms,
    fusionTrajectories: [] as FusionTrajectory[],
    isAdmin,
    onMarkerAction: isAdmin ? forceRefreshMarkers : undefined,
  };

  if (isEmbed) {
    return (
      <main className="relative h-screen h-[100dvh] w-full overflow-hidden">
        <div id="map-container" className="isolate h-full w-full">
          <MapErrorBoundary>
            <MapContainer {...mapProps} />
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
      >
        <div id="map-container" className="isolate h-full w-full">
          <MapErrorBoundary>
            <MapContainer {...mapProps} />
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

'use client';

import { useState, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { useAlarms } from '@/hooks/useAlarms';
import { useMarkers } from '@/hooks/useMarkers';
import { useFusionTrajectories } from '@/hooks/useFusionTrajectories';
import { usePresence } from '@/hooks/usePresence';
import Navbar from '@/components/Navbar';
import StatusPanel from '@/components/StatusPanel';
import BallisticBanner from '@/components/BallisticBanner';
import DonateModal from '@/components/DonateModal';
import FaqModal from '@/components/FaqModal';
import TelegramBanner from '@/components/TelegramBanner';
import BottomBar from '@/components/BottomBar';
import DeploymentScreen from '@/components/DeploymentScreen';
import ZoomControls from '@/components/Map/ZoomControls';

// Dynamically import map (no SSR - Leaflet needs window)
const MapContainer = dynamic(() => import('@/components/Map/MapContainer'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center bg-[#0a0e17]">
      <div className="text-white/30 text-sm animate-pulse">Завантаження карти...</div>
    </div>
  ),
});

export default function HomePage() {
  const { alarms, alarmCount, lastUpdate, error } = useAlarms();
  const { markers, ballisticThreat } = useMarkers();
  const { trajectories } = useFusionTrajectories();
  const presence = usePresence();

  const [donateOpen, setDonateOpen] = useState(false);
  const [faqOpen, setFaqOpen] = useState(false);

  // Map zoom controls - access Leaflet map at runtime (not at import time)
  const getLeafletMap = useCallback(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const w = window as any;
    if (w.L && w.L.Map) {
      for (const key of Object.keys(w)) {
        if (w[key] instanceof w.L.Map) return w[key];
      }
    }
    // Fallback: find map from DOM
    const mapEl = document.getElementById('leaflet-map');
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    if (mapEl && (mapEl as any)._leaflet_id != null) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      return (mapEl as any)._leaflet;
    }
    return null;
  }, []);

  const handleZoomIn = useCallback(() => {
    getLeafletMap()?.zoomIn();
  }, [getLeafletMap]);

  const handleZoomOut = useCallback(() => {
    getLeafletMap()?.zoomOut();
  }, [getLeafletMap]);

  const handleResetZoom = useCallback(() => {
    const map = getLeafletMap();
    if (map) {
      map.fitBounds([[44.2, 22.0], [52.4, 40.2]]);
    }
  }, [getLeafletMap]);

  return (
    <main className="w-full h-screen overflow-hidden relative">
      {/* Deployment health check screen */}
      <DeploymentScreen />

      {/* SEO H1 - visible to Google, compact for users */}
      <h1 className="absolute top-2.5 left-1/2 -translate-x-1/2 z-[5] text-white/50 text-[11px] font-normal text-center whitespace-nowrap pointer-events-none tracking-wide max-md:text-[10px] max-md:whitespace-normal max-md:leading-snug max-md:max-w-[90%]">
        Карта шахедів і тривог України онлайн — повітряна тривога, мапа тривог
      </h1>

      {/* Navbar */}
      <Navbar
        presence={presence}
        onDonate={() => setDonateOpen(true)}
        onFaq={() => setFaqOpen(true)}
      />

      {/* Status Panel */}
      <StatusPanel alarmCount={alarmCount} lastUpdate={lastUpdate} error={error} />

      {/* Ballistic threat banner */}
      <BallisticBanner threat={ballisticThreat} />

      {/* Map */}
      <div id="map-container" className="w-full h-full">
        <MapContainer
          markers={markers}
          alarms={alarms}
          fusionTrajectories={trajectories}
        />
      </div>

      {/* Zoom controls */}
      <ZoomControls
        onZoomIn={handleZoomIn}
        onZoomOut={handleZoomOut}
        onReset={handleResetZoom}
      />

      {/* Telegram banner */}
      <TelegramBanner />

      {/* Bottom bar */}
      <BottomBar
        onDonate={() => setDonateOpen(true)}
        onFaq={() => setFaqOpen(true)}
      />

      {/* Modals */}
      <DonateModal isOpen={donateOpen} onClose={() => setDonateOpen(false)} />
      <FaqModal isOpen={faqOpen} onClose={() => setFaqOpen(false)} />

      {/* SEO content - hidden but crawlable */}
      <article className="sr-only">
        <h2>Карта тривог та шахедів України онлайн — повітряна тривога в реальному часі</h2>
        <p>
          NEPTUN — найшвидша карта тривог України онлайн. Відстежуйте повітряні тривоги, шахеди,
          дрони та ракети в реальному часі на інтерактивній карті. Оновлення кожні 5 секунд,
          push-сповіщення, траєкторія польоту шахедів 24/7.
        </p>
      </article>
    </main>
  );
}

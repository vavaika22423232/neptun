import { Suspense } from 'react';
import HomePageClient from './HomePageClient';
import { getInitialAlarmsSnapshot } from '@/lib/alarms-data';
import { getInitialPublicMarkersPayload } from '@/lib/markers-page-data';

export const dynamic = 'force-dynamic';

// Server Component — reads searchParams at request time
// so ?embed=1 is resolved during SSR, not after hydration
export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const params = await searchParams;
  const isEmbed = params.embed === '1';

  const [{ alarms: initialAlarms, etag: initialAlarmEtag }, initialMarkersPayload] = await Promise.all([
    getInitialAlarmsSnapshot(),
    getInitialPublicMarkersPayload(),
  ]);

  return (
    <Suspense fallback={<div className="h-full w-full bg-[var(--surface-dim)]" />}>
      <HomePageClient
        isEmbed={isEmbed}
        initialAlarms={initialAlarms}
        initialAlarmEtag={initialAlarmEtag}
        initialMarkers={initialMarkersPayload.markers}
        initialMarkersVersion={initialMarkersPayload.markersVersion}
        initialMarkersServerTime={initialMarkersPayload.serverTime}
        initialBallisticThreat={initialMarkersPayload.ballisticThreat}
      />
    </Suspense>
  );
}

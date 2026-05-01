import { Suspense } from 'react';
import HomePageClient from './HomePageClient';
import { getInitialAlarmsSnapshot } from '@/lib/alarms-data';

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

  const { alarms: initialAlarms, etag: initialAlarmEtag } = await getInitialAlarmsSnapshot();

  return (
    <Suspense fallback={<div className="h-full w-full bg-[var(--surface-dim)]" />}>
      <HomePageClient
        isEmbed={isEmbed}
        initialAlarms={initialAlarms}
        initialAlarmEtag={initialAlarmEtag}
      />
    </Suspense>
  );
}

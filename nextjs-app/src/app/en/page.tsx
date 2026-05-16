import { Suspense } from 'react';
import type { Metadata } from 'next';
import HomePageClient from '../HomePageClient';
import { getInitialAlarmsSnapshot } from '@/lib/alarms-data';
import { getInitialPublicMarkersPayload } from '@/lib/markers-page-data';
// English version of the homepage — same map, English metadata

export const dynamic = 'force-dynamic';

export const metadata: Metadata = {
  title: 'Ukraine Air Raid Alert Map — Live Shahed & Missile Tracker | NEPTUN',
  description:
    'Live air raid alert map of Ukraine. Track shaheds, cruise missiles, ballistic rockets & drones in real time. Push notifications, 5-second updates, 24/7. Free app.',
  keywords:
    'ukraine air raid map, ukraine alarm map, shahed tracker, ukraine missile map, air raid alert ukraine, ukraine drone map, NEPTUN',
  alternates: {
    canonical: 'https://neptun.in.ua/en',
    languages: {
      uk: 'https://neptun.in.ua/',
      en: 'https://neptun.in.ua/en',
    },
  },
  openGraph: {
    type: 'website',
    url: 'https://neptun.in.ua/en',
    title: 'NEPTUN — Ukraine Air Raid Alert Map',
    description:
      'Live air raid alerts, shahed drone tracking & missile radar across all 25 regions of Ukraine. Updated every 5 seconds.',
    images: [{ url: 'https://neptun.in.ua/api/og', width: 1200, height: 630, alt: 'NEPTUN — Ukraine Air Raid Map' }],
    siteName: 'NEPTUN Air Raid Map',
    locale: 'en_US',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'NEPTUN — Ukraine Air Raid Alert Map',
    description: 'Live air raids, shaheds, missiles & drones on an interactive map of Ukraine. Free.',
    images: [{ url: 'https://neptun.in.ua/api/og', width: 1200, height: 630, alt: 'NEPTUN — Ukraine Air Raid Map' }],
  },
  other: {
    'geo.region': 'UA',
    'geo.placename': 'Ukraine',
    language: 'English',
  },
};

export default async function EnglishPage({
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

  // JSON-LD for English version
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'WebApplication',
    name: 'NEPTUN — Ukraine Air Raid Alert Map',
    alternateName: ['Ukraine Alarm Map', 'Shahed Tracker', 'Ukraine Drone Map'],
    description:
      'Live air raid alert map of Ukraine. Track shaheds, cruise missiles, ballistic rockets and drones in real time across all 25 regions.',
    url: 'https://neptun.in.ua/en',
    applicationCategory: 'UtilitiesApplication',
    operatingSystem: 'Web, Android, iOS',
    offers: { '@type': 'Offer', price: '0', priceCurrency: 'USD' },
    author: { '@type': 'Organization', name: 'NEPTUN', url: 'https://neptun.in.ua' },
    inLanguage: 'en',
    isAccessibleForFree: true,
    featureList: [
      'Live air raid alerts for all 25 regions of Ukraine',
      'Shahed drone tracking with flight trajectories',
      'Push notifications for alerts in your region',
      'Cruise & ballistic missile threat warnings',
      'Updates every 5 seconds, 24/7',
    ],
  };

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
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
    </>
  );
}

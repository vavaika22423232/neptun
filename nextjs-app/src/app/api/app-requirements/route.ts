import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

/**
 * Мінімальна версія нативних клієнтів (Flutter iOS/Android).
 * Піднімайте min_version / min_build лише коли потрібно примусово відрізати старі збірки.
 */
export async function GET() {
  const body = {
    min_version: '1.0.0',
    min_build: 0,
    title: 'Потрібне оновлення',
    message:
      'Встановіть останню версію додатку з Google Play або App Store, щоб продовжити користування.',
    android_store_url:
      'https://play.google.com/store/apps/details?id=com.neptunalarm.neptun_alarm_app',
    ios_store_url: 'https://apps.apple.com/app/id6743895428',
  };

  return NextResponse.json(body, {
    status: 200,
    headers: {
      'Cache-Control': 'no-store, max-age=0',
    },
  });
}

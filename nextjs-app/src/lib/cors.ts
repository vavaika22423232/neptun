import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/** Продакшен-домени та стейджинг (за потреби додайте через CORS_EXTRA_ORIGINS). */
const BASE_ALLOWED_ORIGINS = new Set([
  'https://neptun.in.ua',
  'https://www.neptun.in.ua',
]);

/** Додаткові дозволені Origin через кому, наприклад: https://staging.example.com */
const EXTRA_ALLOWED_ORIGINS = new Set(
  (process.env.CORS_EXTRA_ORIGINS ?? '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean),
);

/**
 * Flutter Web / локальна розробка: http://localhost:*, http://127.0.0.1:*, http://[::1]:*
 * (будь-який порт). Не використовуємо * разом із Allow-Credentials.
 */
function isLocalDevOrigin(origin: string): boolean {
  try {
    const u = new URL(origin);
    if (u.protocol !== 'http:') return false;
    const h = u.hostname.toLowerCase();
    return h === 'localhost' || h === '127.0.0.1' || h === '::1';
  } catch {
    return false;
  }
}

function isOriginAllowed(origin: string | null): boolean {
  if (!origin) return true;
  if (BASE_ALLOWED_ORIGINS.has(origin)) return true;
  if (isLocalDevOrigin(origin)) return true;
  if (EXTRA_ALLOWED_ORIGINS.has(origin)) return true;
  return false;
}

export function handleCors(request: NextRequest, response: NextResponse): NextResponse {
  const origin = request.headers.get('origin');

  if (origin && isOriginAllowed(origin)) {
    response.headers.set('Access-Control-Allow-Origin', origin);
  }

  response.headers.set('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  response.headers.set('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Auth-Secret, X-Device-Id');
  response.headers.set('Access-Control-Allow-Credentials', 'true');
  response.headers.set('Access-Control-Max-Age', '86400');

  return response;
}

export function handlePreflight(request: NextRequest): NextResponse | null {
  if (request.method !== 'OPTIONS') return null;

  const origin = request.headers.get('origin');
  if (!isOriginAllowed(origin)) {
    return new NextResponse(null, { status: 403 });
  }

  const response = new NextResponse(null, { status: 204 });
  if (origin) {
    response.headers.set('Access-Control-Allow-Origin', origin);
  }
  response.headers.set('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  response.headers.set('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Auth-Secret, X-Device-Id');
  response.headers.set('Access-Control-Allow-Credentials', 'true');
  response.headers.set('Access-Control-Max-Age', '86400');

  return response;
}

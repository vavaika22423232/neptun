import { APP_STORE_URL, GOOGLE_PLAY_URL } from '@/lib/constants';

/** Where the click originated — forwarded into Play referrer & custom props for dashboards. */
export type AppInstallAttributionSlot =
  | 'bottom_strip_mobile'
  | 'bottom_strip_desktop'
  | 'bottom_icons'
  | 'floating'
  | 'shell_menu'
  | 'dashboard_sidebar'
  | 'vision_dock';

/**
 * Google Play "referrer" (install attribution). Visible in Play Console > traffic sources.
 */
function playReferrerParam(slot: AppInstallAttributionSlot): string {
  const qs = [
    `utm_source=neptun_site`,
    `utm_medium=web`,
    `utm_campaign=app_download`,
    `utm_content=${encodeURIComponent(slot)}`,
  ].join('&');
  return encodeURIComponent(qs);
}

/** Tracked Play URL — preserves existing query and appends referrer. */
export function trackedGooglePlayUrl(slot: AppInstallAttributionSlot): string {
  const sep = GOOGLE_PLAY_URL.includes('?') ? '&' : '?';
  return `${GOOGLE_PLAY_URL}${sep}referrer=${playReferrerParam(slot)}`;
}

/**
 * App Store: add campaign-style parameters (harmless when unused; improves link hygiene).
 */
export function trackedAppStoreUrl(slot: AppInstallAttributionSlot): string {
  const sep = APP_STORE_URL.includes('?') ? '&' : '?';
  return `${APP_STORE_URL}${sep}ct=site_${encodeURIComponent(slot)}&mt=8`;
}

export type ClientStoreFlavor = 'ios' | 'android' | 'unknown';

/** Best-effort client detection (WebView-aware). SSR / first paint → `unknown`. */
export function detectClientStoreFlavor(): ClientStoreFlavor {
  if (typeof navigator === 'undefined') return 'unknown';
  const ua = navigator.userAgent || '';
  if (/iPad|iPhone|iPod/i.test(ua)) return 'ios';
  /** iPadOS 13+ desktop UA can say Macintosh */
  const maxTp = navigator.maxTouchPoints ?? 0;
  if (/Macintosh/i.test(ua) && maxTp > 2) return 'ios';
  if (/Android/i.test(ua)) return 'android';
  return 'unknown';
}

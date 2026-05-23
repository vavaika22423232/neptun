/**
 * Flutter MapTab only shows the error UI for main-frame failures (`isForMainFrame`).
 * Tile/CDN/API 404s inside the embed page must not trigger the full-screen error.
 */
export function isMapMainFrameUrl(url: string | undefined | null): boolean {
  if (!url) return false;
  try {
    const u = new URL(url);
    if (u.hostname !== 'neptun.in.ua' && !u.hostname.endsWith('.neptun.in.ua')) return false;
    const path = u.pathname || '/';
    if (path.startsWith('/api/admin/auth/embed')) return true;
    if (path === '/' || path === '') return true;
    return false;
  } catch {
    return /^https:\/\/neptun\.in\.ua\/?(\?|$)/i.test(url);
  }
}

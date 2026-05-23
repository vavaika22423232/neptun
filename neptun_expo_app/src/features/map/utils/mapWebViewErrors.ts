/**
 * Flutter MapTab ignores sub-resource errors (tiles 404, CDN, analytics).
 * @see map_tab.dart `onWebResourceError` + `isForMainFrame`
 */
export function isMapMainFrameUrl(url: string | undefined | null): boolean {
  if (!url) return false;
  try {
    const u = new URL(url);
    const host = u.hostname.replace(/^www\./, '');
    if (host !== 'neptun.in.ua') return false;
    const path = u.pathname || '/';
    if (path.startsWith('/api/admin/auth/embed')) return true;
    if (path === '/' || path === '') return true;
    return false;
  } catch {
    return /^https:\/\/(www\.)?neptun\.in\.ua\/?(\?|$)/i.test(url);
  }
}

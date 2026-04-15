/**
 * Route-based asset hints for root layout (Leaflet CSS, Material Icons, JSON-LD depth).
 * Shared by middleware (sets pathname header) and any tests.
 */
export function pathnameAssetHints(pathname: string) {
  const isAdminApp = pathname.startsWith('/admin') && pathname !== '/admin/login';
  const leaflet = pathname === '/' || pathname === '/en' || isAdminApp;
  const material = leaflet || pathname === '/dashboard';
  const jsonLdFull = pathname === '/' || pathname === '/en';
  return { leaflet, material, jsonLdFull };
}

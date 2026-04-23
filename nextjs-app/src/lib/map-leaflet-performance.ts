/**
 * Basemap and interaction mode for Leaflet. Full map (Google Hybrid + SVG) is the default
 * everywhere so WebView/ mobile match the public site: same tiles, oblast/district names, and districts layer.
 * (A lighter OpenFreeMap + skipped SVG was tried for perf; users expect “full” map in the app.)
 */

export type MapBasemapKind = 'googleHybrid' | 'rasterVectorDark';

const OPENFREEMAP_DARK =
  'https://tiles.openfreemap.org/styles/dark/{z}/{x}/{y}.png' as const;

const GOOGLE_HYBRID =
  'https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}&hl=uk' as const;

export function isMobileUserAgent(ua: string | undefined): boolean {
  if (!ua) return false;
  return /Android|iPhone|iPad|iPod|Mobile/i.test(ua);
}

/**
 * Use Google satellite/labels for all clients (in-app WebView, mobile, desktop) so the map
 * looks the same and all SVG overlays load; OpenFreeMap remains available for experiments.
 */
export function pickBasemapKind(_isEmbed: boolean, _ua: string | undefined): MapBasemapKind {
  return 'googleHybrid';
}

export function isLowInteractionMode(_isEmbed: boolean, _ua: string | undefined): boolean {
  return false;
}

export function getBasemapUrl(kind: MapBasemapKind): string {
  return kind === 'rasterVectorDark' ? OPENFREEMAP_DARK : GOOGLE_HYBRID;
}

export function getBasemapClassName(kind: MapBasemapKind): string {
  return kind === 'rasterVectorDark' ? 'low-perf-basemap' : 'dark-satellite-layer';
}

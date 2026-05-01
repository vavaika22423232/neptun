/**
 * Basemap helpers for Leaflet/MapLibre.
 * Runtime profile decisions live in `map/map-render-profile.ts`.
 */

import {
  isMobileMapProfile as resolveIsMobileMapProfile,
  isMobileUserAgent as resolveIsMobileUserAgent,
  resolveMapRenderProfile,
} from '@/lib/map/map-render-profile';

export type MapBasemapKind =
  | 'googleHybrid'
  | 'rasterVectorDark'
  | 'cartoDark'
  | 'osmStandard'
  | 'deepStateUkraine';

const OPENFREEMAP_DARK =
  'https://tiles.openfreemap.org/styles/dark/{z}/{x}/{y}.png' as const;

const GOOGLE_HYBRID =
  'https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}&hl=uk' as const;

const CARTO_DARK =
  'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png' as const;

const OSM_STANDARD =
  'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png' as const;

const DEEPSTATE_UKRAINE =
  'https://st1.deepstatemap.live/styles/DSUkraineUkDark/{z}/{x}/{y}@2x.webp' as const;
const DEEPSTATE_UKRAINE_LIGHT =
  'https://st1.deepstatemap.live/styles/DSUkraineUk/{z}/{x}/{y}@2x.webp' as const;

export function isMobileUserAgent(ua: string | undefined): boolean {
  return resolveIsMobileUserAgent(ua);
}

/**
 * Профіль «телефон/планшет» для карти: кроссфейд SVG↔тайли, кіки `invalidateSize`.
 * iPadOS часто шле desktop UA (`Macintosh` без iPhone) — `isMobileUserAgent` === false, а Leaflet
 * з десктопною кривою триманить `--map-opacity: 0` при zoom 5–6 (країна цілком), тож видно лише SVG.
 */
export function isMobileMapProfile(ua: string | undefined, maxTouchPoints: number | undefined): boolean {
  return resolveIsMobileMapProfile(ua, maxTouchPoints);
}

/**
 * Базовий шар: Google Hybrid (стабільні тайли до z19).
 * OpenFreeMap (`rasterVectorDark`) — резерв у `getBasemapUrl` (раніше вмикався на моб. сайті й давав «порожню» мапу після зуму).
 */
export function pickBasemapKind(isEmbed: boolean, ua: string | undefined): MapBasemapKind {
  return resolveMapRenderProfile({ isEmbed, userAgent: ua }).basemap;
}

/** Менше анімацій Leaflet, рідші оновлення SVG-opacity під час pinch; embed теж у «легкому» режимі. */
export function isLowInteractionMode(
  isEmbed: boolean,
  ua: string | undefined,
  maxTouchPoints: number | undefined = undefined,
): boolean {
  return resolveMapRenderProfile({ isEmbed, userAgent: ua, maxTouchPoints }).lowInteraction;
}

export function getBasemapUrl(kind: MapBasemapKind): string {
  if (kind === 'rasterVectorDark') return OPENFREEMAP_DARK;
  if (kind === 'cartoDark') return CARTO_DARK;
  if (kind === 'osmStandard') return OSM_STANDARD;
  if (kind === 'deepStateUkraine') return DEEPSTATE_UKRAINE;
  return GOOGLE_HYBRID;
}

export function getLightBasemapUrl(kind: MapBasemapKind): string {
  if (kind === 'deepStateUkraine') return DEEPSTATE_UKRAINE_LIGHT;
  if (kind === 'cartoDark') return OSM_STANDARD;
  return getBasemapUrl(kind);
}

export function getBasemapClassName(kind: MapBasemapKind): string {
  if (kind === 'cartoDark') return 'carto-dark-layer';
  if (kind === 'osmStandard') return 'osm-standard-layer';
  if (kind === 'deepStateUkraine') return 'deepstate-ukraine-layer';
  return kind === 'rasterVectorDark' ? 'low-perf-basemap' : 'dark-satellite-layer';
}

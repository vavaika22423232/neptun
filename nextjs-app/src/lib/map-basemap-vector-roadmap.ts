/**
 * Roadmap: larger, configurable settlement labels on the tactical map.
 *
 * Google Hybrid (`lyrs=y`) bakes labels into raster tiles — CSS cannot increase only label size.
 * Next step when raster tweaks are insufficient:
 * 1. Base layer: satellite only, e.g. `GOOGLE_SATELLITE_TILE_URL` below (`lyrs=s`).
 * 2. Overlay: MapLibre GL (or similar) with a vector style where `place` / `settlement-minor`
 *    layers use higher `text-size` and `text-halo-width` for Ukrainian labels.
 * 3. Sync MapLibre camera with Leaflet (center/zoom/bearing) or migrate the basemap to MapLibre only.
 *
 * Env hook (future): `NEXT_PUBLIC_MAPLIBRE_STYLE_URL` — if set, init could swap to dual-engine mode.
 */
export const GOOGLE_SATELLITE_TILE_URL =
  'https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}&hl=uk' as const;

export const GOOGLE_HYBRID_TILE_URL =
  'https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}&hl=uk' as const;

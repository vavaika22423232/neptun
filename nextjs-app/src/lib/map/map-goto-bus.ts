import type { Map as MapLibreMap } from 'maplibre-gl';
import type { GeoJSONSource } from 'maplibre-gl';

/** Direct map navigation — works even when React context / isReady races. */

export const NEPTUN_MAP_GOTO = 'neptun:map-goto';

export type NeptunMapGotoDetail = {
  lat: number;
  lng: number;
  zoom?: number;
  duration?: number;
  label?: string;
};

/** Last place the user picked in search — replay after style reload instead of resetting Ukraine view. */
let lastUserGoto: NeptunMapGotoDetail | null = null;

export function getLastNeptunMapGoto(): NeptunMapGotoDetail | null {
  return lastUserGoto;
}

export function rememberNeptunMapGoto(detail: NeptunMapGotoDetail): NeptunMapGotoDetail | null {
  const lat = Number(detail.lat);
  const lng = Number(detail.lng);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
  lastUserGoto = { ...detail, lat, lng };
  return lastUserGoto;
}

export function dispatchNeptunMapGoto(detail: NeptunMapGotoDetail): void {
  if (typeof window === 'undefined') return;
  const saved = rememberNeptunMapGoto(detail);
  if (!saved) return;
  window.dispatchEvent(
    new CustomEvent<NeptunMapGotoDetail>(NEPTUN_MAP_GOTO, {
      detail: saved,
    }),
  );
}

export function parseNeptunMapGotoEvent(ev: Event): NeptunMapGotoDetail | null {
  const detail = (ev as CustomEvent<NeptunMapGotoDetail>).detail;
  if (!detail) return null;
  return rememberNeptunMapGoto(detail);
}

export function setSearchPinOnMap(map: MapLibreMap, lat: number, lng: number, label?: string): void {
  const src = map.getSource('place-search-pin') as GeoJSONSource | undefined;
  if (!src) return;
  src.setData({
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [lng, lat] },
        properties: { label: label ?? '' },
      },
    ],
  });
}

/** Fly/zoom to a place; falls back to jumpTo if flyTo throws. */
export function applyNeptunMapGoto(map: MapLibreMap, detail: NeptunMapGotoDetail): void {
  const lat = Number(detail.lat);
  const lng = Number(detail.lng);
  const zoom = detail.zoom ?? 12;
  const duration = detail.duration ?? 1400;

  try {
    map.stop();
    setSearchPinOnMap(map, lat, lng, detail.label);
    map.flyTo({
      center: [lng, lat],
      zoom,
      duration,
      essential: true,
    });
  } catch (err) {
    console.warn('[neptun:map-goto] flyTo failed, jumpTo:', err);
    try {
      map.jumpTo({ center: [lng, lat], zoom });
      setSearchPinOnMap(map, lat, lng, detail.label);
    } catch {
      /* ignore */
    }
  }
}

function mapOverlaysReady(map: MapLibreMap): boolean {
  try {
    return (map.getStyle()?.layers?.length ?? 0) > 0 && Boolean(map.isStyleLoaded());
  } catch {
    return false;
  }
}

/** Apply goto when overlays exist; wait for style.load if the basemap is still swapping. */
export function runNeptunMapGotoOnMap(map: MapLibreMap, detail: NeptunMapGotoDetail): void {
  const normalized = rememberNeptunMapGoto(detail);
  if (!normalized) return;

  const attempt = (): boolean => {
    try {
      if (!mapOverlaysReady(map)) return false;
      applyNeptunMapGoto(map, normalized);
      return true;
    } catch {
      return false;
    }
  };

  if (attempt()) return;

  const onStyleLoad = () => {
    if (attempt()) map.off('style.load', onStyleLoad);
  };
  map.on('style.load', onStyleLoad);

  window.setTimeout(() => {
    attempt();
    map.off('style.load', onStyleLoad);
  }, 3000);
}

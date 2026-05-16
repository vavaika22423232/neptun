import type { MapBasemapKind } from '@/lib/map-leaflet-performance';

export type MapRuntimeProfileKind = 'desktop' | 'mobile' | 'webview';

export type MapRenderProfile = {
  kind: MapRuntimeProfileKind;
  isMobileLike: boolean;
  lowInteraction: boolean;
  basemap: MapBasemapKind;
  lowTileMode: boolean;
  maxZoom: number;
  tile: {
    updateWhenIdle: boolean;
    keepBuffer: number;
    detectRetina: boolean;
  };
  leaflet: {
    transform3DLimit: number;
    zoomSnap: number;
    inertia: boolean;
    inertiaMaxSpeed: number;
  };
  svg: {
    loadOblastStates: true;
    loadDetailedDistricts: true;
    loadOblastNames: true;
    hideDuringInteraction: true;
    allowDistrictGeoJson: false;
  };
};

export function isMobileUserAgent(ua: string | undefined): boolean {
  if (!ua) return false;
  return /Android|iPhone|iPad|iPod|Mobile/i.test(ua);
}

export function isMobileMapProfile(ua: string | undefined, maxTouchPoints: number | undefined): boolean {
  if (isMobileUserAgent(ua)) return true;
  return maxTouchPoints != null && maxTouchPoints > 0;
}

/**
 * Single runtime contract for alarm map rendering.
 *
 * District alarms require exact raion shapes, so all profiles use
 * `ukraine_districts_detailed.svg`. The broken `ukraine_districts.geojson`
 * is intentionally excluded from every runtime profile because it can render
 * long line artifacts on mobile/WebView.
 */
export function resolveMapRenderProfile(input: {
  isEmbed: boolean;
  userAgent?: string;
  maxTouchPoints?: number;
}): MapRenderProfile {
  const isTouch = isMobileMapProfile(input.userAgent, input.maxTouchPoints);
  const kind: MapRuntimeProfileKind = input.isEmbed ? 'webview' : isTouch ? 'mobile' : 'desktop';
  const lowInteraction = kind !== 'desktop';

  /** Десктоп, мобільний браузер і WebView (`?embed=1`) — один векторний темний базовий шар (OFM / OpenFreeMap). */
  const basemap: MapBasemapKind = 'rasterVectorDark';
  const lowTileMode = false;

  return {
    kind,
    isMobileLike: kind !== 'desktop',
    lowInteraction,
    basemap,
    lowTileMode,
    maxZoom: 19,
    tile: {
      updateWhenIdle: false,
      keepBuffer: 2,
      detectRetina: true,
    },
    leaflet: {
      transform3DLimit: lowInteraction ? 1 : 2,
      zoomSnap: lowInteraction ? 1 : 0.5,
      inertia: !lowInteraction,
      inertiaMaxSpeed: lowInteraction ? 1500 : 3000,
    },
    svg: {
      loadOblastStates: true,
      loadDetailedDistricts: true,
      loadOblastNames: true,
      hideDuringInteraction: true,
      allowDistrictGeoJson: false,
    },
  };
}

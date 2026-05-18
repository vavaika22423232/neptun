'use client';

import { useCallback, useEffect, useRef, useState, memo } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import type { StyleSpecification } from 'maplibre-gl';
import type { FeatureCollection } from 'geojson';
import type { Alarm, FusionTrajectory, Marker } from '@/types';
import { THREAT_NAMES } from '@/types';
import { CACHE_VERSION } from '@/lib/constants';
import { formatKyivTime, buildMarkerPopup } from '@/lib/map/marker-popup-html';
import { fetchOccupiedTerritoriesMerged } from '@/lib/map/fetch-occupied-territories';
import {
  districtRegionNamesForAlarms,
  hascListForStateAlarms,
  normalizeAlarmRegionName,
  type OblastFeatureCollection,
} from '@/lib/map/alarm-hasc-filter';
import { resolveMapRenderProfile } from '@/lib/map/map-render-profile';
import { markersToGeoJSON, markersToSwarmGeoJSON, maplibreIconId, markerIconUrl } from '@/lib/map/markers-to-geojson';
import type { ThreatMarkerFeatureCollection } from '@/lib/map/markers-to-geojson';
import { markersToTrailsGeoJSON } from '@/lib/map/markers-to-trails-geojson';
import { markersToLaunchGeoJSON } from '@/lib/map/markers-to-launch-geojson';
import { notifyFlutterThreatMarkerTap } from '@/lib/map/flutter-app-bridge';
import { resolveThreatBearingDeg } from '@/lib/threat-bearing';
import { MAP_DAY, MAP_NIGHT } from '@/lib/map/map-visual-tokens';
import {
  applyThreatMarkerFocus,
} from '@/lib/map/map-threat-focus';
import { buildUaRasterBasemapStyle, buildGenericRasterBasemapStyle } from '@/lib/map/ua-raster-maplibre-style';
import { getBasemapUrl } from '@/lib/map-leaflet-performance';

const MAP_BOUNDS = { minLat: 44.2, maxLat: 52.4, minLng: 22.0, maxLng: 40.2 } as const;
const UKRAINE_ONLY_VIEW_BOUNDS = { minLat: 42.7, maxLat: 53.7, minLng: 19.8, maxLng: 42.4 } as const;
const MOBILE_FULL_UKRAINE_VIEW_BOUNDS = UKRAINE_ONLY_VIEW_BOUNDS;

/** Нормалізована текстура іконки (px) — `icon-size` = icon_px / NORM_ICON_PX */
const NORM_ICON_PX = 48;

/** 🇺🇦 маркери територіальної цілісності (lng, lat з settlements / існуюча точка для Криму). */
const UKRAINE_CLAIM_FLAG_MARKERS: ReadonlyArray<{ lngLat: [number, number]; label: string }> = [
  { lngLat: [34.1024, 44.9521], label: 'Крим - це Україна!' },
  { lngLat: [37.80134, 48.01588], label: 'Донецьк - це Україна!' },
  { lngLat: [39.29732, 48.57171], label: 'Луганськ - це Україна!' },
];

const CLAIM_FLAG_POPUP_INNER_STYLE =
  'font-weight: 600; color: #1a1d21; font-size: 14px; padding: 4px; font-family: sans-serif;';

type MutableStyleLayer = {
  id: string;
  source?: string;
  'source-layer'?: string;
  type?: string;
  filter?: unknown;
  paint?: Record<string, unknown>;
  layout?: Record<string, unknown>;
};
type MutableMapStyle = Omit<StyleSpecification, 'layers'> & { layers: MutableStyleLayer[] };

/** Фільтр по HASC: `in` + `literal` на MapLibre v5 інколи дає порожню вибірку — `match` стабільніший. */
function oblastHascInAlarmSetExpr(hascs: string[]): unknown {
  if (hascs.length === 1) return ['==', ['get', 'HASC_1'], hascs[0]];
  const expr: unknown[] = ['match', ['get', 'HASC_1']];
  for (const h of hascs) {
    expr.push(h, true);
  }
  expr.push(false);
  return expr;
}

function oblastAlarmFillFilter(hascs: string[]): unknown {
  if (hascs.length === 0) return ['==', ['get', 'HASC_1'], '__none__'];
  return oblastHascInAlarmSetExpr(hascs);
}

function oblastCalmDimFilter(hascs: string[]): unknown {
  if (hascs.length === 0) return ['==', ['get', 'HASC_1'], '__none__'];
  return ['all', ['!=', ['get', 'HASC_1'], '?'], ['!', oblastHascInAlarmSetExpr(hascs)]];
}

function getFirstSymbolLayerId(map: maplibregl.Map): string | undefined {
  const layers = map.getStyle()?.layers;
  if (!layers) return undefined;
  for (const layer of layers) {
    if (layer.type === 'symbol') {
      return layer.id;
    }
  }
  return undefined;
}

function withFilter(baseFilter: unknown, extraFilter: unknown): unknown {
  if (!baseFilter) return extraFilter;
  return ['all', baseFilter, extraFilter];
}

function districtKeyInSetExpr(keys: string[]): unknown {
  if (keys.length === 1) return ['==', ['get', 'regionKey'], keys[0]];
  const expr: unknown[] = ['match', ['get', 'regionKey']];
  for (const k of keys) {
    expr.push(k, true);
  }
  expr.push(false);
  return expr;
}

function districtAlarmFillFilter(keys: string[]): unknown {
  if (keys.length === 0) return ['==', ['get', 'regionKey'], '__none__'];
  return districtKeyInSetExpr(keys);
}

let tooltipSingleton: HTMLDivElement | null = null;

function showMarkerTooltip(event: MouseEvent, marker: Marker, threatType: string) {
  if (!tooltipSingleton) {
    tooltipSingleton = document.createElement('div');
    tooltipSingleton.className = 'marker-tooltip';
    tooltipSingleton.id = 'active-tooltip';
    document.body.appendChild(tooltipSingleton);
  }
  const tooltip = tooltipSingleton;
  const typeName = THREAT_NAMES[threatType] || threatType;
  const trustRaw = (marker.display_trust_hint_uk || '').replace(/</g, '&lt;');
  const trustLine = trustRaw
    ? `<div class="tooltip-trust">${trustRaw}</div>`
    : '';

  const tipBrg = resolveThreatBearingDeg(marker);
  const confLabel = marker.heading_confidence === 'track' ? '' :
    marker.heading_confidence === 'explicit' ? ' (явний)' :
    marker.heading_confidence === 'regional' ? ' (~регіон)' : '';
  const tipCourse = tipBrg != null
    ? `<div class="tooltip-course">↗ Курс ~${Math.round(tipBrg)}°${confLabel}</div>`
    : '';

  // ETA badge
  let etaLine = '';

  // Loitering badge
  const loiterLine = marker.is_loitering
    ? `<div class="tooltip-loitering">⟳ Барражує</div>`
    : '';

  tooltip.innerHTML = `
    ${trustLine}
    <div class="tooltip-type">${typeName}</div>
    <div class="tooltip-place">${marker.place || 'Невідомо'}</div>
    ${tipCourse}
    ${etaLine}${loiterLine}
    ${marker.date ? `<div class="tooltip-time">${formatKyivTime(marker.date)}</div>` : ''}
  `;

  tooltip.style.opacity = '1';
  // Reset animation
  tooltip.style.animation = 'none';
  requestAnimationFrame(() => {
    if (tooltip) tooltip.style.animation = '';
  });

  const rect = tooltip.getBoundingClientRect();
  let x = event.clientX + 16;
  let y = event.clientY + 16;
  if (x + rect.width > window.innerWidth - 8) x = event.clientX - rect.width - 16;
  if (y + rect.height > window.innerHeight - 8) y = event.clientY - rect.height - 16;
  tooltip.style.transform = `translate3d(${x}px, ${y}px, 0)`;
}

function hideMarkerTooltip() {
  if (tooltipSingleton) tooltipSingleton.style.opacity = '0';
}

/** Світла/темна тема застосунку (окремо від палітри базової карти OFM). */
function isLightAppTheme(): boolean {
  return typeof document !== 'undefined' && document.documentElement.classList.contains('theme-light');
}

function collectIconJobs(markers: Marker[]): { id: string; url: string }[] {
  const seen = new Set<string>();
  const jobs: { id: string; url: string }[] = [];
  const origin = typeof window !== 'undefined' ? window.location.origin : '';
  for (const m of markers) {
    const id = maplibreIconId(m);
    if (seen.has(id)) continue;
    seen.add(id);
    const path = markerIconUrl(m);
    jobs.push({ id, url: `${origin}${path}` });
  }
  return jobs;
}

/**
 * Растеризує іконку до квадрата NORM_ICON_PX — передбачуваний `icon-size` на шарі.
 */
function ensureThreatImages(map: maplibregl.Map, jobs: { id: string; url: string }[]): Promise<void> {
  const origin = typeof window !== 'undefined' ? window.location.origin : '';
  const fallbackRaster = `${origin}/shahed3.webp?${CACHE_VERSION}`;
  const IMAGE_LOAD_TIMEOUT_MS = 2200;

  return Promise.all(
    jobs.map(
      ({ id, url }) =>
        new Promise<void>((resolve) => {
          let settled = false;
          let timeoutId: ReturnType<typeof setTimeout> | null = null;
          const done = () => {
            if (settled) return;
            settled = true;
            if (timeoutId) clearTimeout(timeoutId);
            resolve();
          };
          if (map.hasImage(id)) {
            done();
            return;
          }
          timeoutId = setTimeout(done, IMAGE_LOAD_TIMEOUT_MS);
          const img = new Image();
          img.crossOrigin = 'anonymous';
          img.onload = () => {
            void (async () => {
              if (settled) return;
              try {
                const c = document.createElement('canvas');
                c.width = NORM_ICON_PX;
                c.height = NORM_ICON_PX;
                const ctx = c.getContext('2d');
                if (!ctx) {
                  done();
                  return;
                }
                ctx.clearRect(0, 0, NORM_ICON_PX, NORM_ICON_PX);
                ctx.drawImage(img, 0, 0, NORM_ICON_PX, NORM_ICON_PX);
                const data = ctx.getImageData(0, 0, NORM_ICON_PX, NORM_ICON_PX);
                const isBallistic =
                  url.includes('icon_balistic') &&
                  typeof document !== 'undefined' &&
                  !document.documentElement.classList.contains('theme-light');
                if (isBallistic) {
                  const px = data.data;
                  for (let i = 0; i < px.length; i += 4) {
                    if (px[i + 3] > 8) {
                      px[i] = 255;
                      px[i + 1] = 255;
                      px[i + 2] = 255;
                    }
                  }
                }
                if (!map.hasImage(id)) map.addImage(id, data);
              } catch {
                try {
                  const { data } = await map.loadImage(url);
                  if (!map.hasImage(id)) map.addImage(id, data);
                } catch {
                  /* ignore */
                }
              } finally {
                done();
              }
            })();
          };
          img.onerror = () => {
            // Mobile / flaky networks: primary icon failed → still register bitmap so symbol layer shows something.
            if (img.src.includes('shahed3.webp')) {
              done();
              return;
            }
            img.onerror = done;
            img.src = fallbackRaster;
          };
          img.src = url;
        }),
    ),
  ).then(() => undefined);
}

function emptyThreats(): ThreatMarkerFeatureCollection {
  return { type: 'FeatureCollection', features: [] };
}

type DistrictFeatureCollection = FeatureCollection & {
  features: Array<FeatureCollection['features'][number] & {
    properties: Record<string, unknown> & { regionKey?: string };
  }>;
};

function prepareDistrictGeoJson(raw: FeatureCollection): DistrictFeatureCollection {
  const features = raw.features.map((feature) => {
    const props = { ...(feature.properties || {}) } as Record<string, unknown> & { regionKey?: string };
    props.regionKey = normalizeAlarmRegionName(String(props.rayon || ''));
    return { ...feature, properties: props };
  });
  return { ...raw, features } as DistrictFeatureCollection;
}

interface MapLibreContainerProps {
  markers: Marker[];
  alarms: Alarm[];
  fusionTrajectories: FusionTrajectory[];
  isAdmin?: boolean;
  onMarkerAction?: () => void;
  isEmbed?: boolean;
  ukraineOnly?: boolean;
  basemapOverride?: import('@/lib/map-leaflet-performance').MapBasemapKind;
  autoTrack?: boolean;
  focusedTargetId?: string | null;
  onFocusedTargetIdChange?: (id: string | null) => void;
}

function MapLibreContainer({
  markers,
  alarms,
  fusionTrajectories,
  isAdmin,
  onMarkerAction,
  isEmbed = false,
  ukraineOnly = false,
  basemapOverride,
  autoTrack = false,
  focusedTargetId = null,
  onFocusedTargetIdChange,
}: MapLibreContainerProps) {
  const mapElRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const oblastFcRef = useRef<OblastFeatureCollection | null>(null);
  const ukraineOnlyRef = useRef(ukraineOnly);
  const markerFocusMidRef = useRef<string | null>(null);
  const latestHascsRef = useRef<string[]>([]);
  const latestDistrictKeysRef = useRef<string[]>([]);
  const isAdminRef = useRef(!!isAdmin);
  const latestAlarmsRef = useRef(alarms);
  const latestMarkersRef = useRef<Marker[]>([]);
  const markerSyncGenRef = useRef(0);
  const applyAlarmPaintRef = useRef<(alarmsData: Alarm[]) => void>(() => {});
  const applyBaseStyleRef = useRef<() => void>(() => {});
  const rafIdRef = useRef<number | null>(null);
  const [mapReady, setMapReady] = useState(false);

  useEffect(() => {
    latestAlarmsRef.current = alarms;
  }, [alarms]);

  useEffect(() => {
    latestMarkersRef.current = markers;
  }, [markers]);

  useEffect(() => {
    isAdminRef.current = !!isAdmin;
  }, [isAdmin]);

  useEffect(() => {
    ukraineOnlyRef.current = ukraineOnly;
    const map = mapRef.current;
    if (!map) return;
    if (ukraineOnly) {
      map.setMinZoom(4);
      map.setMaxBounds([
        [UKRAINE_ONLY_VIEW_BOUNDS.minLng, UKRAINE_ONLY_VIEW_BOUNDS.minLat],
        [UKRAINE_ONLY_VIEW_BOUNDS.maxLng, UKRAINE_ONLY_VIEW_BOUNDS.maxLat],
      ]);
      map.fitBounds(
        [
          [UKRAINE_ONLY_VIEW_BOUNDS.minLng, UKRAINE_ONLY_VIEW_BOUNDS.minLat],
          [UKRAINE_ONLY_VIEW_BOUNDS.maxLng, UKRAINE_ONLY_VIEW_BOUNDS.maxLat],
        ],
        { animate: false, padding: 18 },
      );
    } else {
      map.setMinZoom(5);
      map.setMaxBounds([
        [18, 40],
        [44, 56],
      ]);
    }
    applyBaseStyleRef.current();
  }, [ukraineOnly]);

  useEffect(() => {
    if (!isAdmin) return;
    const w = window as unknown as {
      __ADMIN_SECRET?: string;
      __adminDeleteMarker?: (id: string, lat: number, lng: number, text: string) => void;
      __adminHideMarker?: (lat: number, lng: number, text: string) => void;
    };

    const adminJsonHeaders = (): Record<string, string> => {
      const secret =
        new URLSearchParams(window.location.search).get('admin_secret') ||
        w.__ADMIN_SECRET;
      return {
        'Content-Type': 'application/json',
        ...(secret ? { 'X-Auth-Secret': secret } : {}),
      };
    };

    w.__adminDeleteMarker = async (id: string, lat: number, lng: number, text: string) => {
      try {
        const res = await fetch('/api/admin/markers/delete', {
          method: 'POST',
          headers: adminJsonHeaders(),
          body: JSON.stringify({ id: id || undefined, lat, lng, text }),
        });
        if (res.ok) {
          popupRef.current?.remove();
          onMarkerAction?.();
        } else {
          const err = await res.json().catch(() => ({}));
          alert('Помилка видалення: ' + (err.error || res.status));
        }
      } catch {
        alert('Помилка мережі');
      }
    };

    w.__adminHideMarker = async (lat: number, lng: number, text: string) => {
      try {
        const res = await fetch('/api/admin/hidden/hide', {
          method: 'POST',
          headers: adminJsonHeaders(),
          body: JSON.stringify({ lat, lng, text, source: 'auto' }),
        });
        if (res.ok) {
          popupRef.current?.remove();
          onMarkerAction?.();
        } else {
          alert('Помилка приховування');
        }
      } catch {
        alert('Помилка мережі');
      }
    };

    return () => {
      delete w.__adminDeleteMarker;
      delete w.__adminHideMarker;
    };
  }, [isAdmin, onMarkerAction]);

  useEffect(() => {
    if (!mapElRef.current || mapRef.current) return;

    const ua = typeof navigator !== 'undefined' ? navigator.userAgent : undefined;
    const mtp = typeof navigator !== 'undefined' ? navigator.maxTouchPoints : undefined;
    const profile = resolveMapRenderProfile({ isEmbed, userAgent: ua, maxTouchPoints: mtp });
    const initialBasemapKind = profile.basemap;
    const mapMaxZoom = profile.maxZoom;
    const isMobile = profile.isMobileLike;

    const mapResize = () => {
      try {
        mapRef.current?.resize();
      } catch {
        /* ignore */
      }
    };
    const onViewportResize = () => {
      mapResize();
    };
    window.addEventListener('resize', onViewportResize);
    window.addEventListener('orientationchange', onViewportResize);
    const libreVisualViewport = typeof window !== 'undefined' ? window.visualViewport : null;
    if (libreVisualViewport) {
      libreVisualViewport.addEventListener('resize', onViewportResize);
    }
    let mobileLibreKick1: number | null = null;
    let mobileLibreKick2: number | null = null;
    if (isMobile && !isEmbed) {
      mobileLibreKick1 = window.setTimeout(mapResize, 300);
      mobileLibreKick2 = window.setTimeout(mapResize, 900);
    }

    /**
     * Local Premium 3D Map Styles
     */
    const LOCAL_STYLE_LIGHT = `/map-style-light.json?${CACHE_VERSION}`;
    const LOCAL_STYLE_DARK = `/map-style-dark.json?${CACHE_VERSION}`;

    // Cached GeoJSON - loaded once, replayed on every style swap
    let cachedGeoData: {
      oblastData: OblastFeatureCollection;
      districtData: FeatureCollection;
      occupiedTerritories: FeatureCollection;
    } | null = null;
    // Keep track of the current request sequence to avoid race conditions
    let styleRequestSeq = 0;

    const map = new maplibregl.Map({
      container: mapElRef.current,
      style: { version: 8, sources: {}, layers: [] },
      center: [31.5, 48.5],
      zoom: isMobile ? 4 : 4.85,
      minZoom: isMobile ? 2.75 : 3,
      maxZoom: mapMaxZoom,
      maxBounds: [
        [18, 40],
        [44, 56],
      ],
      attributionControl: false,
      dragRotate: true, // Enable rotation for 3D
      pitchWithRotate: true,
      touchPitch: true,
    });
    
    // Store it on the map object so it persists across re-renders
    (map as any).styleRequestSeq = 0;

    // Add pitch adjustment on zoom
    map.on('zoom', () => {
      const zoom = map.getZoom();
      if (zoom > 13) {
        const targetPitch = Math.min(60, (zoom - 13) * 20);
        if (map.getPitch() < targetPitch) {
          map.setPitch(targetPitch);
        }
      } else if (zoom < 12 && map.getPitch() > 0) {
        map.setPitch(0);
      }
    });

    const originalAddSource = map.addSource.bind(map);
    const originalAddLayer = map.addLayer.bind(map);

    mapRef.current = map;

    map.on('error', (e) => {
      console.error('MapLibre error:', e);
    });

    map.on('styleimagemissing', (event) => {
      if (map.hasImage(event.id)) return;
      const size = 16;
      const canvas = document.createElement('canvas');
      canvas.width = size;
      canvas.height = size;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;
      ctx.clearRect(0, 0, size, size);
      if (event.id.includes('circle')) {
        ctx.beginPath();
        ctx.arc(size / 2, size / 2, 3, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(160, 170, 185, 0.42)';
        ctx.fill();
      }
      try {
        map.addImage(event.id, ctx.getImageData(0, 0, size, size));
      } catch {
        /* ignore duplicate or stale style image requests */
      }
    });

    const buildOFMStyle = async (useLightBasemap: boolean, onlyUkraine: boolean) => {
      const styleUrl = useLightBasemap ? LOCAL_STYLE_LIGHT : LOCAL_STYLE_DARK;
      const [styleRes, ukraineBoundary] = await Promise.all([
        fetch(styleUrl),
        onlyUkraine
          ? fetch(`/geoBoundaries-UKR-ADM0_simplified.geojson?${CACHE_VERSION}`, { cache: 'force-cache' }).then((res) => res.json())
          : Promise.resolve(null),
      ]);
      const styleText = await styleRes.text();
      const style = JSON.parse(styleText) as MutableMapStyle;

      // Layer ID patterns whose labels are too noisy at zoom 5-6 → hide
      const HIDE_LABEL_PATTERNS = ['state', 'country', 'continent', 'region', 'county', 'province'];
      const ukraineWithinFilter = ukraineBoundary ? ['within', ukraineBoundary] : null;

      style.layers.forEach((layer) => {
        if (layer.source === 'openmaptiles') {
          const sourceLayer = layer['source-layer'];

          if (ukraineWithinFilter) {
            if (
              sourceLayer === 'place' ||
              sourceLayer === 'water_name' ||
              sourceLayer === 'poi' ||
              sourceLayer === 'aerodrome_label'
            ) {
              layer.filter = withFilter(layer.filter, ukraineWithinFilter);
            } else if (sourceLayer === 'boundary') {
              if (layer.id.includes('boundary_country') || layer.id === 'boundary_2') {
                layer.filter = withFilter(layer.filter, [
                  'any',
                  ['==', ['get', 'adm0_l'], 'UKR'],
                  ['==', ['get', 'adm0_r'], 'UKR'],
                  ['==', ['get', 'claimed_by'], 'UA'],
                ]);
              } else if (layer.id === 'boundary_state' || layer.id === 'boundary_3') {
                // Do not apply 'within' to region borders, it hides lines touching the national edge
              } else {
                layer.filter = withFilter(layer.filter, ukraineWithinFilter);
              }
            }
          }
        }

        if (layer.type === 'symbol' && layer.layout) {
          const lid: string = layer.id.toLowerCase();

          // Hide oblast/country/continent label layers entirely
          if (HIDE_LABEL_PATTERNS.some(p => lid.includes(p))) {
            layer.layout['visibility'] = 'none';
            return;
          }

          // Use Ukrainian names
          if (layer.layout['text-field']) {
            layer.layout['text-field'] = ['coalesce', ['get', 'name:uk'], ['get', 'name:latin'], ['get', 'name']];
          }

          // Scale text to 0.72× — OFM liberty defaults are too large at zoom 5-6
          const scaleSize = (ts: unknown): unknown => {
            if (typeof ts === 'number') return ts * 0.72;
            if (Array.isArray(ts) && ts[0] === 'interpolate') {
              const r = [...ts];
              for (let i = 3; i < r.length; i += 2) if (typeof r[i] === 'number') r[i] = r[i] * 0.72;
              return r;
            }
            if (Array.isArray(ts) && ts[0] === 'step') {
              const r = [...ts];
              if (typeof r[2] === 'number') r[2] = r[2] * 0.72;
              for (let i = 4; i < r.length; i += 2) if (typeof r[i] === 'number') r[i] = r[i] * 0.72;
              return r;
            }
            return ts;
          };
          if (layer.layout['text-size'] !== undefined) {
            layer.layout['text-size'] = scaleSize(layer.layout['text-size']);
          }

          // Use Regular weight (no bold)
          if (layer.layout['text-font']) {
            layer.layout['text-font'] = (layer.layout['text-font'] as string[]).map((f: string) =>
              f.replace('Bold', 'Regular').replace('bold', 'regular')
            );
          }

          // Improve text contrast for the newly lightened dark theme
          if (!useLightBasemap && layer.paint && layer.paint['text-color']) {
            layer.paint['text-color'] = lid.includes('city') || lid.includes('town') ? '#f1f5f9' : '#cbd5e1';
            if (layer.paint['text-halo-color']) {
              layer.paint['text-halo-color'] = '#181f29';
              layer.paint['text-halo-width'] = 1.25;
            }
          }
        }
      });
      return style as StyleSpecification;
    };

    const loadGeoData = async () => {
      if (cachedGeoData) return cachedGeoData;
      const [oblastRes, districtRes, occupiedTerritories] = await Promise.all([
        fetch(`/ukraine_oblasts.geojson?${CACHE_VERSION}`, { cache: 'force-cache' }),
        fetch(`/ukraine_raions_2020.geojson?${CACHE_VERSION}`, { cache: 'force-cache' }),
        fetchOccupiedTerritoriesMerged(CACHE_VERSION),
      ]);
      const oblastData = (await oblastRes.json()) as OblastFeatureCollection;
      const districtData = prepareDistrictGeoJson((await districtRes.json()) as FeatureCollection);
      oblastFcRef.current = oblastData;
      cachedGeoData = { oblastData, districtData, occupiedTerritories };
      return cachedGeoData;
    };

    const basemapOverrideRef = { current: basemapOverride };

    const applyBaseStyle = async () => {
      const requestSeq = ++(map as any).styleRequestSeq;
      try {
        setMapReady(false);
        const light = isLightAppTheme();
        const currentBasemapKind = basemapOverrideRef.current || initialBasemapKind;
        const [style, geoData] = await Promise.all([
          currentBasemapKind === 'uaRasterBasemap'
            ? Promise.resolve(buildUaRasterBasemapStyle(light))
            : currentBasemapKind === 'rasterVectorDark'
            ? buildOFMStyle(light, ukraineOnlyRef.current)
            : Promise.resolve(buildGenericRasterBasemapStyle([getBasemapUrl(currentBasemapKind)], currentBasemapKind)),
          loadGeoData(),
        ]);
        if (requestSeq !== (map as any).styleRequestSeq) return;
        cachedGeoData = geoData;

        // Preserve dynamic sources and layers for smooth diffing
        const currentStyle = map.getStyle();
        if (currentStyle && currentStyle.sources) {
          const dynamicSourceIds = ['oblasts', 'districts', 'ukraine-border-source', 'threats', 'occupied-territories', 'launch-arcs', 'launch-sites', 'threat-swarms', 'threat-trails'];
          for (const src of dynamicSourceIds) {
            if (currentStyle.sources[src]) {
              style.sources[src] = currentStyle.sources[src];
            }
          }
          const baseLayerIds = new Set(style.layers.map(l => l.id));
          const dynamicLayers = currentStyle.layers.filter(l => !baseLayerIds.has(l.id));
          
          // Insert dynamic layers before the first symbol layer to keep labels on top
          const firstSymbolIdx = style.layers.findIndex(l => l.type === 'symbol');
          if (firstSymbolIdx !== -1) {
            style.layers.splice(firstSymbolIdx, 0, ...dynamicLayers);
          } else {
            style.layers = [...style.layers, ...dynamicLayers];
          }
        }

        console.log('MapLibreContainer: setting style', { requestSeq, styleLayerCount: style.layers.length });
        map.setStyle(style, { diff: true });
        
        // If map is already loaded and style has layers, we might not get a style.load event
        // if the diff is empty or very small. Let's ensure mapReady is set and overlays are applied.
        if (map.isStyleLoaded()) {
           console.log('MapLibreContainer: style already loaded after setStyle, setting mapReady=true and triggering style.load manually');
           setMapReady(true);
           // Manually trigger style.load logic if needed
           setTimeout(() => map.fire('style.load'), 50);
        }
        
        // Ensure map is ready after style is applied if there are no layers
        if (style.layers.length === 0) {
          console.log('MapLibreContainer: style has no layers, setting mapReady=true');
          setMapReady(true);
        }
      } catch (err) {
        console.error('Failed to apply map style', err);
        setMapReady(true);
      }
    };
    applyBaseStyleRef.current = () => {
      void applyBaseStyle();
    };
    // Expose a way for the basemap-override useEffect to update the ref
    (applyBaseStyleRef as { basemapOverrideRef?: typeof basemapOverrideRef }).basemapOverrideRef = basemapOverrideRef;

    // Initial load
    if (map.isStyleLoaded()) {
      console.log('MapLibreContainer: map already loaded, applying style');
      void applyBaseStyle();
    } else {
      console.log('MapLibreContainer: map not loaded yet, waiting for load event');
      map.once('load', () => {
        console.log('MapLibreContainer: map load event fired, applying style');
        void applyBaseStyle();
      });
    }

    const onThemeChange = () => {
      applyBaseStyleRef.current();
    };
    window.addEventListener('theme-change', onThemeChange);

    map.on('style.load', () => {
      // Skip only the empty placeholder style we set during initialization; ukraine-only
      // style intentionally starts with only a background layer before overlays are replayed.
      const styleLayerCount = map.getStyle()?.layers?.length ?? 0;
      if (styleLayerCount === 0) {
        console.warn('MapLibre style.load: styleLayerCount is 0, skipping');
        setMapReady(true);
        return;
      }
      
      // If we only have the background layer (e.g. ukraine-only mode without base map), 
      // we still want to load the geo data and overlays
      
      if (!cachedGeoData) {
        console.warn('MapLibre style.load: geo data not ready yet');
        // We still need to set mapReady=true so that the map can render at least the base style
        setMapReady(true);
        return; // GeoJSON not yet loaded, skip overlays for now
      }
      
      console.log('MapLibre style.load: applying overlays. Layer count:', styleLayerCount);
      
      // Ensure map is ready after overlays are applied
      setMapReady(true);

      const { oblastData, districtData, occupiedTerritories } = cachedGeoData;
      const isLightBasemap = isLightAppTheme();
      const onlyUkraine = ukraineOnlyRef.current;
      const firstSymbolId = getFirstSymbolLayerId(map);

      // Add 3D buildings
      if (!onlyUkraine && map.getSource('openmaptiles') && !map.getLayer('3d-buildings')) {
        originalAddLayer({
          id: '3d-buildings',
          source: 'openmaptiles',
          'source-layer': 'building',
          type: 'fill-extrusion',
          minzoom: 14,
          paint: {
            'fill-extrusion-color': isLightBasemap ? '#e5e0d8' : '#21262d',
            'fill-extrusion-height': ['coalesce', ['get', 'render_height'], ['get', 'height'], 15],
            'fill-extrusion-base': ['coalesce', ['get', 'render_min_height'], ['get', 'min_height'], 0],
            'fill-extrusion-opacity': 0.8,
          },
        }, firstSymbolId);
      }

      // GeoJSON sources
      if (!map.getSource('oblasts')) originalAddSource('oblasts', { type: 'geojson', data: oblastData as unknown as FeatureCollection });
      if (!map.getSource('districts')) originalAddSource('districts', { type: 'geojson', data: districtData });
      if (!map.getSource('ukraine-border-source')) originalAddSource('ukraine-border-source', { type: 'geojson', data: `/geoBoundaries-UKR-ADM0_simplified.geojson?${CACHE_VERSION}` });
      if (!map.getSource('threats')) originalAddSource('threats', { type: 'geojson', data: emptyThreats() as unknown as FeatureCollection, promoteId: 'mid' });

      // Overlay layers
      if (!map.getLayer('oblast-calm-dim')) {
        originalAddLayer(
          {
            id: 'oblast-calm-dim',
            type: 'fill',
            source: 'oblasts',
            filter: ['==', ['get', 'HASC_1'], '__none__'],
            maxzoom: 11,
            paint: isLightBasemap
              ? {
                  'fill-color': MAP_DAY.calmDimFill,
                  'fill-opacity': ['interpolate', ['linear'], ['zoom'], 5, 0.07, 8, 0.05, 11, 0.025],
                }
              : {
                  'fill-color': MAP_NIGHT.calmDimFill,
                  'fill-opacity': ['interpolate', ['linear'], ['zoom'], 5, 0.22, 8, 0.15, 11, 0.05],
                },
          },
          firstSymbolId,
        );
      }
      if (!map.getLayer('ukraine-border-stroke')) {
        originalAddLayer({ id: 'ukraine-border-stroke', type: 'line', source: 'ukraine-border-source', paint: { 'line-color': isLightBasemap ? '#1a1d21' : '#ffffff', 'line-opacity': 0.55, 'line-width': 2.5 } }, firstSymbolId);
      }

      if (!map.getSource('occupied-territories')) {
        originalAddSource('occupied-territories', { type: 'geojson', data: occupiedTerritories });
      }
      if (!map.getLayer('occupied-territories-fill')) {
        originalAddLayer(
          {
            id: 'occupied-territories-fill',
            type: 'fill',
            source: 'occupied-territories',
            paint: isLightBasemap
              ? {
                  'fill-color': '#991b1b',
                  'fill-opacity': ['interpolate', ['linear'], ['zoom'], 5, 0.1, 9, 0.14, 14, 0.11],
                }
              : {
                  'fill-color': '#f87171',
                  'fill-opacity': ['interpolate', ['linear'], ['zoom'], 5, 0.06, 9, 0.1, 14, 0.08],
                },
          },
          firstSymbolId,
        );
      }
      if (!map.getLayer('occupied-territories-outline')) {
        originalAddLayer(
          {
            id: 'occupied-territories-outline',
            type: 'line',
            source: 'occupied-territories',
            paint: {
              'line-color': isLightBasemap ? '#7f1d1d' : '#fecaca',
              'line-opacity': 0.5,
              'line-width': 1.2,
            },
          },
          firstSymbolId,
        );
      }

      if (!map.getLayer('oblast-alarm-fill')) {
        originalAddLayer({ id: 'oblast-alarm-fill', type: 'fill', source: 'oblasts', filter: ['==', ['get', 'HASC_1'], '__none__'], paint: { 'fill-color': '#cc0022', 'fill-opacity': 0.48 } }, firstSymbolId);
      }
      if (!map.getLayer('district-alarm-fill')) {
        originalAddLayer({ id: 'district-alarm-fill', type: 'fill', source: 'districts', filter: ['==', ['get', 'regionKey'], '__none__'], paint: { 'fill-color': '#cc0022', 'fill-opacity': isLightBasemap ? 0.58 : 0.68 } }, firstSymbolId);
      }
      if (!map.getLayer('oblast-context-line')) {
        originalAddLayer({ id: 'oblast-context-line', type: 'line', source: 'oblasts', filter: ['!=', ['get', 'HASC_1'], '?'], paint: { 'line-color': MAP_NIGHT.oblastLine, 'line-opacity': 0.12, 'line-width': 0.6 } });
      }
      // Bright red outline on alarmed oblasts — the most visible alarm indicator
      if (!map.getLayer('oblast-alarm-outline')) {
        originalAddLayer(
          {
            id: 'oblast-alarm-outline',
            type: 'line',
            source: 'oblasts',
            filter: ['==', ['get', 'HASC_1'], '__none__'],
            paint: {
              'line-color': '#ef4444',
              'line-opacity': 0.8,
              'line-width': ['interpolate', ['linear'], ['zoom'], 4, 1.0, 7, 2.2, 10, 3.0],
            },
          },
          firstSymbolId,
        );
      }
      // ── Launch origin arcs (very faint, behind trails) ───────────────────
      if (!map.getSource('launch-arcs')) {
        originalAddSource('launch-arcs', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
      }
      if (!map.getLayer('launch-arc-glow')) {
        originalAddLayer(
          {
            id: 'launch-arc-glow',
            type: 'line',
            source: 'launch-arcs',
            layout: { 'line-join': 'round', 'line-cap': 'round' },
            paint: {
              'line-color': '#f43f5e',
              'line-opacity': ['*', ['get', 'opacity'], 0.12],
              'line-width': 8,
              'line-blur': 5,
            },
          },
          firstSymbolId,
        );
      }
      if (!map.getLayer('launch-arc-line')) {
        originalAddLayer(
          {
            id: 'launch-arc-line',
            type: 'line',
            source: 'launch-arcs',
            layout: { 'line-join': 'round', 'line-cap': 'round' },
            paint: {
              'line-color': '#f43f5e',
              'line-opacity': ['*', ['get', 'opacity'], 0.45],
              'line-width': 1.2,
              'line-dasharray': [4, 5],
            },
          },
          firstSymbolId,
        );
      }
      // Launch site markers (enemy territory origin points)
      if (!map.getSource('launch-sites')) {
        originalAddSource('launch-sites', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
      }
      if (!map.getLayer('launch-site-halo')) {
        originalAddLayer({
          id: 'launch-site-halo',
          type: 'circle',
          source: 'launch-sites',
          paint: {
            'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 10, 8, 18],
            'circle-color': '#f43f5e',
            'circle-opacity': ['*', ['get', 'opacity'], 0.25],
            'circle-blur': 0.7,
          },
        });
      }
      if (!map.getLayer('launch-site-label')) {
        originalAddLayer({
          id: 'launch-site-label',
          type: 'symbol',
          source: 'launch-sites',
          layout: {
            'text-field': ['get', 'shortName'],
            'text-size': ['interpolate', ['linear'], ['zoom'], 4, 9, 8, 11],
            'text-font': ['Noto Sans Bold', 'Arial Unicode MS Bold'],
            'text-offset': [0, 0],
            'text-allow-overlap': true,
            'text-ignore-placement': true,
          },
          paint: {
            'text-color': '#fb7185',
            'text-halo-color': '#0a0d12',
            'text-halo-width': 2.0,
            'text-opacity': ['*', ['get', 'opacity'], 1.2],
          },
        });
      }

      // ── Tactical Swarm Grouping (Convex Hulls) ───────────────────────────
      if (!map.getSource('threat-swarms')) {
        originalAddSource('threat-swarms', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
      }
      if (!map.getLayer('threat-swarm-fill')) {
        originalAddLayer(
          {
            id: 'threat-swarm-fill',
            type: 'fill',
            source: 'threat-swarms',
            paint: {
              'fill-color': '#f43f5e',
              'fill-opacity': 0.08,
            },
          },
          'threat-trail-projection'
        );
      }
      if (!map.getLayer('threat-swarm-line')) {
        originalAddLayer(
          {
            id: 'threat-swarm-line',
            type: 'line',
            source: 'threat-swarms',
            paint: {
              'line-color': '#f43f5e',
              'line-width': 1.5,
              'line-dasharray': [4, 4],
              'line-opacity': 0.3,
            },
          },
          'threat-trail-projection'
        );
      }
      if (!map.getLayer('threat-swarm-label')) {
        originalAddLayer(
          {
            id: 'threat-swarm-label',
            type: 'symbol',
            source: 'threat-swarms',
            minzoom: 6.0,
            layout: {
              'text-field': ['get', 'swarm_label'],
              'text-font': ['Noto Sans Bold', 'Arial Unicode MS Bold'],
              'text-size': 11,
              'text-anchor': 'center',
            },
            paint: {
              'text-color': '#fb7185',
              'text-halo-color': 'rgba(15, 15, 15, 0.85)',
              'text-halo-width': 1.5,
            },
          },
          firstSymbolId
        );
      }
      // ── Threat trail lines (behind markers, zoom ≥ 5.5) ─────────────────
      if (!map.getSource('threat-trails')) {
        originalAddSource('threat-trails', { type: 'geojson', data: { type: 'FeatureCollection', features: [] }, lineMetrics: true });
      }
      // Glow layer — wide semi-transparent duplicate under the trail for depth
      if (!map.getLayer('threat-trail-glow')) {
        originalAddLayer(
          {
            id: 'threat-trail-glow',
            type: 'line',
            source: 'threat-trails',
            filter: ['==', ['get', 'trail_kind'], 'trail'],
            minzoom: 5.5,
            layout: { 'line-join': 'round', 'line-cap': 'round' },
            paint: {
              'line-color': ['get', 'trail_color'],
              'line-opacity': ['*', ['get', 'trail_opacity'], 0.28],
              'line-width': ['*', ['get', 'trail_width'], 4.5],
              'line-blur': 3,
            },
          },
          firstSymbolId,
        );
      }
      // Trail line — crisp solid observed path
      if (!map.getLayer('threat-trail-line')) {
        originalAddLayer(
          {
            id: 'threat-trail-line',
            type: 'line',
            source: 'threat-trails',
            filter: ['==', ['get', 'trail_kind'], 'trail'],
            minzoom: 5.5,
            layout: { 'line-join': 'round', 'line-cap': 'round' },
            paint: {
              'line-color': ['get', 'trail_color'],
              'line-opacity': ['get', 'trail_opacity'],
              'line-width': ['get', 'trail_width'],
            },
          },
          firstSymbolId,
        );
      }
      // Projection line — dashed arrow ahead of drone
      if (!map.getLayer('threat-trail-projection')) {
        originalAddLayer(
          {
            id: 'threat-trail-projection',
            type: 'line',
            source: 'threat-trails',
            filter: ['match', ['get', 'trail_kind'], ['projection', 'uncertainty'], true, false],
            minzoom: 5.5,
            layout: { 'line-join': 'round', 'line-cap': 'round' },
            paint: {
              'line-color': ['get', 'trail_color'],
              'line-opacity': ['get', 'trail_opacity'],
              'line-width': ['get', 'trail_width'],
              'line-dasharray': [3, 3],
            },
          },
          firstSymbolId,
        );
      }

      if (!map.getLayer('threat-trail-checkpoint')) {
        originalAddLayer(
          {
            id: 'threat-trail-checkpoint',
            type: 'symbol',
            source: 'threat-trails',
            filter: ['==', ['get', 'trail_kind'], 'checkpoint'],
            minzoom: 6.5,
            layout: {
              'text-field': ['get', 'checkpoint_label'],
              'text-font': ['Noto Sans Bold', 'Arial Unicode MS Bold'],
              'text-size': 10,
              'text-anchor': 'center',
              'text-allow-overlap': false,
              'text-ignore-placement': false,
            },
            paint: {
              'text-color': ['get', 'trail_color'],
              'text-halo-color': 'rgba(15, 15, 15, 0.85)',
              'text-halo-width': 1.5,
            },
          },
          firstSymbolId,
        );
      }

      if (!map.getLayer('threat-zone-circle')) {
        originalAddLayer(
          {
            id: 'threat-zone-circle',
            type: 'circle',
            source: 'threats',
            filter: ['>', ['get', 'threat_zone_radius_km'], 0],
            paint: {
              'circle-radius': [
                'interpolate', ['exponential', 2], ['zoom'],
                7, ['*', ['get', 'threat_zone_radius_km'], 0.8],
                10, ['*', ['get', 'threat_zone_radius_km'], 6.4],
                14, ['*', ['get', 'threat_zone_radius_km'], 100]
              ],
              'circle-color': ['get', 'halo_color'],
              'circle-opacity': 0.06,
              'circle-stroke-width': 1,
              'circle-stroke-color': ['get', 'halo_color'],
              'circle-stroke-opacity': 0.15,
              'circle-pitch-alignment': 'map',
            },
          },
          'threat-swarm-fill'
        );
      }

      if (!map.getLayer('unclustered-point-halo')) {
        originalAddLayer({
          id: 'unclustered-point-halo',
          type: 'circle',
          source: 'threats',
          filter: ['!', ['has', 'point_count']],
          paint: {
            'circle-radius': ['get', 'halo_radius'],
            'circle-color': ['get', 'halo_color'],
            'circle-opacity': ['get', 'halo_opacity'],
            'circle-blur': 0.8,
            'circle-pitch-alignment': 'map'
          }
        });
      }

      if (!map.getLayer('unclustered-point')) {
        // Threat icon with ETA / Status label
        originalAddLayer({
          id: 'unclustered-point',
          type: 'symbol',
          source: 'threats',
          filter: ['!', ['has', 'point_count']],
          layout: {
            'icon-image': ['get', 'micon'],
            'icon-size': ['/', ['get', 'icon_px'], NORM_ICON_PX],
            'icon-rotate': ['get', 'bearing'],
            'icon-rotation-alignment': 'map',
            'icon-allow-overlap': true,
            'icon-ignore-placement': true,
            'symbol-sort-key': ['get', 'prio'],
            'text-field': ['get', 'status_label'],
            'text-font': ['Noto Sans Bold', 'Arial Unicode MS Bold'],
            'text-size': 11,
            'text-offset': [0, 1.4],
            'text-anchor': 'top',
            'text-optional': true,
          },
          paint: {
            'icon-opacity': ['case', ['boolean', ['feature-state', 'hover'], false], ['min', 1, ['+', ['get', 'opacity'], 0.07]], ['get', 'opacity']],
            'text-color': '#ff4d4d',
            'text-halo-color': 'rgba(15, 15, 15, 0.85)',
            'text-halo-width': 1.5,
            'text-opacity': ['get', 'opacity'],
          }
        });
      }

      // Re-apply alarms
      queueMicrotask(() => applyAlarmPaintRef.current(latestAlarmsRef.current));

      // Re-sync threat markers after full style swap (setStyle wipes sources). Doing this here — after
      // icons exist — avoids a race where React sees mapReady before GeoJSON/image data is applied.
      void (async () => {
        try {
          const mks = latestMarkersRef.current;
          if (mks.length > 0) {
            const fc = markersToGeoJSON(mks) as unknown as FeatureCollection;
            const src = map.getSource('threats') as maplibregl.GeoJSONSource | undefined;
            if (src) src.setData(fc);
            applyThreatMarkerFocus(map, markerFocusMidRef.current, NORM_ICON_PX);
            void ensureThreatImages(map, collectIconJobs(mks)).then(() => {
              try {
                const freshSrc = map.getSource('threats') as maplibregl.GeoJSONSource | undefined;
                if (freshSrc && map.isStyleLoaded()) freshSrc.setData(fc);
                applyThreatMarkerFocus(map, markerFocusMidRef.current, NORM_ICON_PX);
              } catch {
                /* map/style was replaced */
              }
            }).catch(() => {});
          }
        } catch (e) {
          console.warn('MapLibre style.load: marker replay failed', e);
        } finally {
          setMapReady(true);
        }
      })();
    });

    map.on('load', () => {
      void (async () => {
        try {
          // Ensure geo data loaded (may already be cached)
          await loadGeoData();

          // 🇺🇦 Маркери Крим / Донецьк / Луганськ — підпис по натисканню
          if (!document.querySelector('.neptun-claim-flag-marker')) {
            for (const { lngLat, label } of UKRAINE_CLAIM_FLAG_MARKERS) {
              const flagEl = document.createElement('div');
              flagEl.className = 'neptun-claim-flag-marker';
              flagEl.innerHTML = '🇺🇦';
              flagEl.style.fontSize = '24px';
              flagEl.style.cursor = 'pointer';
              flagEl.style.pointerEvents = 'auto';
              const inner = label.replace(/</g, '&lt;').replace(/>/g, '&gt;');
              const flagPopup = new maplibregl.Popup({ closeButton: false, closeOnClick: true, offset: 15 }).setHTML(
                `<div style="${CLAIM_FLAG_POPUP_INNER_STYLE}">${inner}</div>`,
              );
              new maplibregl.Marker({ element: flagEl }).setLngLat(lngLat).setPopup(flagPopup).addTo(map);
            }
          }

          applyThreatMarkerFocus(map, null, NORM_ICON_PX);

          map.on('click', (e) => {
            const feats = map.queryRenderedFeatures(e.point, { layers: ['unclustered-point'] });
            if (feats.length) return;
            popupRef.current?.remove();
            markerFocusMidRef.current = null;
            applyThreatMarkerFocus(map, null, NORM_ICON_PX);
          });

          map.on('click', 'unclustered-point', (e) => {
            const f = e.features?.[0];
            if (!f || f.geometry.type !== 'Point') return;
            const coords = f.geometry.coordinates as [number, number];
            const rawJson = f.properties?._m;
            const mid = f.properties?.mid as string | undefined;
            if (typeof rawJson !== 'string') return;
            let m: Marker;
            try {
              m = JSON.parse(rawJson) as Marker;
            } catch {
              return;
            }
            const tt = m.threat_type || 'default';
            hideMarkerTooltip();
            popupRef.current?.remove();
            if (mid) {
              markerFocusMidRef.current = mid;
              applyThreatMarkerFocus(map, mid, NORM_ICON_PX);
              if (onFocusedTargetIdChange) onFocusedTargetIdChange(m.id || null);
            }
            if (isEmbed && !isAdminRef.current && notifyFlutterThreatMarkerTap(m)) {
              return;
            }
            const popup = new maplibregl.Popup({
              maxWidth: 'min(268px, calc(100vw - 24px))',
              closeButton: true,
              closeOnClick: true,
              offset: 14,
              className: 'neptun-maplibre-popup admin-marker-popup',
            })
              .setLngLat(coords)
              .setHTML(buildMarkerPopup(m, tt, isAdminRef.current))
              .addTo(map);
            popup.on('close', () => {
              markerFocusMidRef.current = null;
              applyThreatMarkerFocus(map, null, NORM_ICON_PX);
            });
            popupRef.current = popup;
          });

          const canHoverFine =
            typeof window !== 'undefined' &&
            window.matchMedia('(hover: hover) and (pointer: fine)').matches;
          let hoveredMarkerId: string | number | null = null;
          const clearMarkerHover = () => {
            if (hoveredMarkerId == null) return;
            try {
              map.removeFeatureState({ source: 'threats', id: hoveredMarkerId }, 'hover');
            } catch {
              /* ignore */
            }
            hoveredMarkerId = null;
          };

          map.on('mouseenter', 'unclustered-point', (e) => {
            map.getCanvas().style.cursor = 'pointer';
            const f = e.features?.[0];
            const rawJson = f?.properties?._m;
            if (canHoverFine && f?.properties?.mid != null) {
              clearMarkerHover();
              const mid = f.properties.mid as string;
              hoveredMarkerId = mid;
              try {
                map.setFeatureState({ source: 'threats', id: mid }, { hover: true });
              } catch {
                /* ignore */
              }
            }
            if (typeof rawJson !== 'string') return;
            try {
              const m = JSON.parse(rawJson) as Marker;
              const te = e.originalEvent;
              if (te && 'clientX' in te) showMarkerTooltip(te as MouseEvent, m, m.threat_type || 'default');
            } catch {
              /* ignore */
            }
          });
          map.on('mousemove', 'unclustered-point', (e) => {
            const f = e.features?.[0];
            const rawJson = f?.properties?._m;
            if (typeof rawJson !== 'string') return;
            try {
              const m = JSON.parse(rawJson) as Marker;
              const te = e.originalEvent;
              if (te && 'clientX' in te) showMarkerTooltip(te as MouseEvent, m, m.threat_type || 'default');
            } catch {
              /* ignore */
            }
          });
          map.on('mouseleave', 'unclustered-point', () => {
            map.getCanvas().style.cursor = '';
            clearMarkerHover();
            hideMarkerTooltip();
          });

          const initialBounds = isMobile ? MOBILE_FULL_UKRAINE_VIEW_BOUNDS : MAP_BOUNDS;
          const inset = isMobile ? 54 : 24;
          map.fitBounds(
            [
              [initialBounds.minLng, initialBounds.minLat],
              [initialBounds.maxLng, initialBounds.maxLat],
            ],
            {
              animate: false,
              padding: { top: inset, bottom: inset, left: inset, right: inset },
              maxZoom: isMobile ? 5.25 : 6,
            },
          );

          /* WebView (Flutter): після layout інколи 0×0 canvas — один resize після першого idle. */
          const resizeOnce = () => {
            try {
              map.resize();
            } catch {
              /* ignore */
            }
          };
          if (isEmbed) {
            map.once('idle', () => requestAnimationFrame(resizeOnce));
            window.setTimeout(resizeOnce, 320);
          }

          // setMapReady is called from style.load (after geo data + style both ready)
        } catch (err) {
          console.warn('MapLibre overlay init error:', err);
        }
      })();
    });

    return () => {
      window.removeEventListener('theme-change', onThemeChange);
      window.removeEventListener('resize', onViewportResize);
      window.removeEventListener('orientationchange', onViewportResize);
      if (libreVisualViewport) {
        libreVisualViewport.removeEventListener('resize', onViewportResize);
      }
      if (mobileLibreKick1) window.clearTimeout(mobileLibreKick1);
      if (mobileLibreKick2) window.clearTimeout(mobileLibreKick2);
      setMapReady(false);
      popupRef.current?.remove();
      popupRef.current = null;
      map.remove();
      mapRef.current = null;
      oblastFcRef.current = null;
    };
  }, [isEmbed]);

  // Re-apply base style when user changes the basemap
  useEffect(() => {
    const ref = applyBaseStyleRef as { basemapOverrideRef?: { current: typeof basemapOverride } };
    if (ref.basemapOverrideRef) {
      ref.basemapOverrideRef.current = basemapOverride;
    }
    applyBaseStyleRef.current();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [basemapOverride]);

  // ── Cinematic Lock-on Mode (Continuous Follow) ────────────────────────────────
  const trackingTargetIdRef = useRef<string | null>(null);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;

    if (!autoTrack) {
      trackingTargetIdRef.current = null;
      map.easeTo({ pitch: 0, bearing: 0, duration: 1000 });
      return;
    }

    const tick = () => {
      if (!autoTrack || !mapReady) return;
      const markers = latestMarkersRef.current;
      const active = markers.filter(
        m => m.track_state !== 'lost' && m.track_state !== 'stale' && m.lat && m.lng,
      );
      if (active.length === 0) return;

      const priority = (m: Marker) => {
        const t = (m.threat_type || '').toLowerCase();
        if (t === 'ballistic') return 3;
        if (t === 'missile' || t === 'raketa') return 2;
        return 1;
      };

      // 1. Try specifically focused target
      let target = focusedTargetId ? active.find(m => m.id === focusedTargetId) : null;
      
      // 2. Fallback to existing tracking ref
      if (!target && trackingTargetIdRef.current) {
        target = active.find(m => m.id === trackingTargetIdRef.current);
      }

      // 3. Pick best new one
      if (!target) {
        target = active.reduce((best, m) => priority(m) > priority(best) ? m : best, active[0]);
      }

      if (target) {
        trackingTargetIdRef.current = target.id ?? null;

        // Smoothly move camera towards target
        map.easeTo({
          center: [target.lng, target.lat],
          zoom: Math.max(map.getZoom(), 8.5),
          pitch: 62,
          bearing: (target.course_bearing ?? map.getBearing()) % 360,
          duration: 2000,
          easing: (t) => t,
        });
      }
    };

    // Initial jump
    tick();
    
    // Continuous follow every 2 seconds (matches easeTo duration for seamless flow)
    const iv = window.setInterval(tick, 2000);
    return () => window.clearInterval(iv);
  }, [autoTrack, mapReady, focusedTargetId]);

  const applyAlarmPaint = useCallback((alarmsData: Alarm[]) => {
    const map = mapRef.current;
    if (!map) return;
    const oblastFc = oblastFcRef.current;
    if (!oblastFc) return;

    const hascs = hascListForStateAlarms(alarmsData, oblastFc);
    const districtKeys = districtRegionNamesForAlarms(alarmsData);
    latestHascsRef.current = hascs;
    latestDistrictKeysRef.current = districtKeys;

    try {
      if (map.getLayer('oblast-calm-dim')) {
        map.setFilter('oblast-calm-dim', oblastCalmDimFilter(hascs) as never);
      }

      if (map.getLayer('oblast-alarm-fill')) {
        map.setFilter('oblast-alarm-fill', oblastAlarmFillFilter(hascs) as never);
        map.setPaintProperty('oblast-alarm-fill', 'fill-opacity', hascs.length > 0 ? 0.48 : 0);
      }

      // Red outline on alarmed oblasts
      if (map.getLayer('oblast-alarm-outline')) {
        map.setFilter('oblast-alarm-outline', oblastAlarmFillFilter(hascs) as never);
      }

      if (map.getLayer('district-alarm-fill')) {
        map.setFilter('district-alarm-fill', districtAlarmFillFilter(districtKeys) as never);
        map.setPaintProperty('district-alarm-fill', 'fill-opacity', isLightAppTheme() ? 0.58 : 0.68);
      }
    } catch (err) {
      console.warn('applyAlarmPaint:', err);
    }
  }, []);

  useEffect(() => {
    applyAlarmPaintRef.current = applyAlarmPaint;
  }, [applyAlarmPaint]);

  useEffect(() => {
    if (!mapReady) return;
    applyAlarmPaint(alarms);
  }, [alarms, mapReady, applyAlarmPaint]);

  /** Легкий пульс opacity активних тривог (~2 Гц), без RAF кожного кадру. */
  useEffect(() => {
    if (!mapReady) return;
    const map = mapRef.current;
    if (!map?.isStyleLoaded()) return;
    const reducedMotion =
      typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reducedMotion) return;

    const tick = () => {
      if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return;
      const hascs = latestHascsRef.current;
      const districtKeys = latestDistrictKeysRef.current;
      if (!map.getLayer('oblast-alarm-fill') || !map.getLayer('district-alarm-fill')) return;
      if (hascs.length === 0 && districtKeys.length === 0) return;
      const w = 0.5 + 0.5 * Math.sin(Date.now() / 550);
      if (hascs.length > 0) {
        const alpha = 0.38 + 0.20 * w;
        map.setPaintProperty('oblast-alarm-fill', 'fill-opacity', alpha);
      }
      if (districtKeys.length > 0) {
        const alpha = (isLightAppTheme() ? 0.50 : 0.60) + 0.12 * w;
        map.setPaintProperty('district-alarm-fill', 'fill-opacity', alpha);
      }
    };

    const iv = window.setInterval(tick, 520);
    return () => window.clearInterval(iv);
  }, [mapReady, alarms]);


  // ── Animation Loop for Smooth Movement (Interpolation) ─────────────────────
  useEffect(() => {
    if (!mapReady) return;
    const map = mapRef.current;
    if (!map) return;

    const tick = () => {
      const currentMarkers = latestMarkersRef.current;
      if (!currentMarkers || !currentMarkers.length) {
        rafIdRef.current = requestAnimationFrame(tick);
        return;
      }

      const now = Date.now();
      const VISUAL_SPEED_MULTIPLIER = 0.35;
      
      const interpolatedMarkers = currentMarkers.map(m => {
        const speed = (m.speed_kmh || m.computed_speed_kmh || 0) * VISUAL_SPEED_MULTIPLIER;
        let bearing = m.course_bearing ?? m.ticker_bearing;

        if (bearing == null && m.positions && m.positions.length >= 2) {
          bearing = resolveThreatBearingDeg(m);
        }

        if (speed > 0 && bearing != null && m.last_update_epoch) {
          const dtHours = (now - m.last_update_epoch) / 3600000;
          const distKm = speed * dtHours;
          // Cap at 50km to prevent runaway markers on long background tabs
          if (distKm > 0 && distKm < 50) {
            const R = 6371;
            const toRad = Math.PI / 180;
            const lat1 = m.lat * toRad;
            const lng1 = m.lng * toRad;
            const brg = bearing * toRad;
            const d = distKm / R;

            const lat2 = Math.asin(
              Math.sin(lat1) * Math.cos(d) +
              Math.cos(lat1) * Math.sin(d) * Math.cos(brg)
            );
            const lng2 = lng1 + Math.atan2(
              Math.sin(brg) * Math.sin(d) * Math.cos(lat1),
              Math.cos(d) - Math.sin(lat1) * Math.sin(lat2)
            );
            return { ...m, lat: lat2 / toRad, lng: lng2 / toRad };
          }
        }
        return m;
      });

      try {
        const fc = markersToGeoJSON(interpolatedMarkers);
        const src = map.getSource('threats') as maplibregl.GeoJSONSource | undefined;
        if (src && map.isStyleLoaded()) {
          src.setData(fc as any);
          if (map.getLayer('unclustered-point-halo')) {
            const pulse = 1.0 + 0.15 * Math.sin(now / 150);
            map.setPaintProperty('unclustered-point-halo', 'circle-radius', ['*', ['get', 'halo_radius'], pulse]);
            map.setPaintProperty('unclustered-point-halo', 'circle-opacity', ['*', ['get', 'halo_opacity'], 1.1 - (0.1 * pulse)]);
          }
        }

        const trailFc = markersToTrailsGeoJSON(interpolatedMarkers);
        const trailSrc = map.getSource('threat-trails') as maplibregl.GeoJSONSource | undefined;
        if (trailSrc && map.isStyleLoaded()) {
          trailSrc.setData(trailFc as any);
        }

        const swarmFc = markersToSwarmGeoJSON(interpolatedMarkers);
        const swarmSrc = map.getSource('threat-swarms') as maplibregl.GeoJSONSource | undefined;
        if (swarmSrc && map.isStyleLoaded()) {
          swarmSrc.setData(swarmFc as any);
        }
      } catch (err) {
        /* ignore */
      }
      
      rafIdRef.current = requestAnimationFrame(tick);
    };

    rafIdRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafIdRef.current) cancelAnimationFrame(rafIdRef.current);
    };
  }, [mapReady]);

  useEffect(() => {
    if (!mapReady) return;
    const map = mapRef.current;
    if (!map?.isStyleLoaded()) return;

    // Static assets update (trails, arcs, icons) — still handled on marker change
    const trailSrc = map.getSource('threat-trails') as maplibregl.GeoJSONSource | undefined;
    if (trailSrc) trailSrc.setData(markersToTrailsGeoJSON(markers) as any);

    const launchData = markersToLaunchGeoJSON(markers);
    const arcSrc = map.getSource('launch-arcs') as maplibregl.GeoJSONSource | undefined;
    if (arcSrc) arcSrc.setData(launchData.arcs as any);
    const siteSrc = map.getSource('launch-sites') as maplibregl.GeoJSONSource | undefined;
    if (siteSrc) siteSrc.setData(launchData.sites as any);

    const jobs = collectIconJobs(markers);
    ensureThreatImages(map, jobs).then(() => {
      applyThreatMarkerFocus(map, markerFocusMidRef.current, NORM_ICON_PX);
    });
  }, [markers, mapReady]);

  return (
    <div
      className={`w-full h-full relative bg-[var(--neptun-map-canvas)]${ukraineOnly ? ' ukraine-only-map-mode' : ''}`}
    >
      <div ref={mapElRef} id="maplibre-map" data-basemap={basemapOverride} className="absolute inset-0 z-[1]" />
    </div>
  );
}

export default memo(MapLibreContainer);

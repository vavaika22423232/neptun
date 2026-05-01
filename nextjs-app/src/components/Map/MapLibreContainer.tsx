'use client';

import { useCallback, useDeferredValue, useEffect, useRef, useState, memo } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import type { StyleSpecification } from 'maplibre-gl';
import type { FeatureCollection } from 'geojson';
import type { Alarm, FusionTrajectory, Marker } from '@/types';
import { THREAT_NAMES } from '@/types';
import { CACHE_VERSION } from '@/lib/constants';
import { formatKyivTime, buildMarkerPopup } from '@/lib/map/marker-popup-html';
import {
  districtRegionNamesForAlarms,
  hascListForStateAlarms,
  normalizeAlarmRegionName,
  type OblastFeatureCollection,
} from '@/lib/map/alarm-hasc-filter';
import { resolveMapRenderProfile } from '@/lib/map/map-render-profile';
import { markersToGeoJSON, maplibreIconId, markerIconUrl } from '@/lib/map/markers-to-geojson';
import type { ThreatMarkerFeatureCollection } from '@/lib/map/markers-to-geojson';
import { resolveThreatBearingDeg } from '@/lib/threat-bearing';
import { MAP_NIGHT } from '@/lib/map/map-visual-tokens';
import {
  applyThreatMarkerFocus,
} from '@/lib/map/map-threat-focus';

const MAP_BOUNDS = { minLat: 44.2, maxLat: 52.4, minLng: 22.0, maxLng: 40.2 } as const;
const UKRAINE_ONLY_VIEW_BOUNDS = { minLat: 42.7, maxLat: 53.7, minLng: 19.8, maxLng: 42.4 } as const;

/** Нормалізована текстура іконки (px) — `icon-size` = icon_px / NORM_ICON_PX */
const NORM_ICON_PX = 48;

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
    ? `<div class="tooltip-trust" style="font-size:11px;color:rgba(255,171,64,0.95);margin-bottom:6px;line-height:1.35;">${trustRaw}</div>`
    : '';
  const tipBrg = resolveThreatBearingDeg(marker);
  const tipCourse =
    tipBrg != null ? `<div class="tooltip-course">Курс ~${Math.round(tipBrg)}°</div>` : '';

  tooltip.innerHTML = `
    ${trustLine}
    <div class="tooltip-type" style="font-weight:600;font-size:13px;margin-bottom:4px;color:#ff2a5f;">${typeName}</div>
    <div class="tooltip-place" style="color:rgba(255,255,255,0.7);margin-bottom:2px;">${marker.place || 'Невідомо'}</div>
    ${tipCourse}
    ${marker.date ? `<div class="tooltip-time" style="color:rgba(255,255,255,0.4);font-size:11px;">${formatKyivTime(marker.date)}</div>` : ''}
  `;

  tooltip.style.opacity = '1';
  const rect = tooltip.getBoundingClientRect();
  let x = event.clientX + 15;
  let y = event.clientY + 15;
  if (x + rect.width > window.innerWidth) x = event.clientX - rect.width - 15;
  if (y + rect.height > window.innerHeight) y = event.clientY - rect.height - 15;
  tooltip.style.transform = `translate3d(${x}px, ${y}px, 0)`;
}

function hideMarkerTooltip() {
  if (tooltipSingleton) tooltipSingleton.style.opacity = '0';
}

function isLightMapTheme(): boolean {
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
  return Promise.all(
    jobs.map(
      ({ id, url }) =>
        new Promise<void>((resolve) => {
          if (map.hasImage(id)) {
            resolve();
            return;
          }
          const img = new Image();
          img.crossOrigin = 'anonymous';
          img.onload = () => {
            void (async () => {
              try {
                const c = document.createElement('canvas');
                c.width = NORM_ICON_PX;
                c.height = NORM_ICON_PX;
                const ctx = c.getContext('2d');
                if (!ctx) {
                  resolve();
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
                resolve();
              }
            })();
          };
          img.onerror = () => resolve();
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
}

function MapLibreContainer({
  markers,
  alarms,
  isAdmin,
  onMarkerAction,
  isEmbed = false,
  ukraineOnly = false,
}: MapLibreContainerProps) {
  const deferredMarkers = useDeferredValue(markers);
  /** Тривоги без `useDeferredValue`: відкладений стан після SSR лишав порожній масив — зони з’являлись із затримкою. */
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
  const applyAlarmPaintRef = useRef<(alarmsData: Alarm[]) => void>(() => {});
  const applyBaseStyleRef = useRef<(isLight: boolean, onlyUkraine: boolean) => void>(() => {});

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
    applyBaseStyleRef.current(isLightMapTheme(), ukraineOnly);
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

        const OFM_LIGHT = 'https://tiles.openfreemap.org/styles/liberty';
    const OFM_DARK = 'https://tiles.openfreemap.org/styles/dark';

    // Cached GeoJSON - loaded once, replayed on every style swap
    let cachedGeoData: {
      oblastData: OblastFeatureCollection;
      districtData: FeatureCollection;
    } | null = null;
    let styleRequestSeq = 0;

    const map = new maplibregl.Map({
      container: mapElRef.current,
      style: { version: 8, sources: {}, layers: [] },
      center: [31.5, 48.5],
      zoom: 5,
      minZoom: 5,
      maxZoom: mapMaxZoom,
      maxBounds: [
        [18, 40],
        [44, 56],
      ],
      attributionControl: false,
      dragRotate: false,
      pitchWithRotate: false,
      touchPitch: false,
    });

    const originalAddSource = map.addSource.bind(map);
    const originalAddLayer = map.addLayer.bind(map);

    mapRef.current = map;

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

    const buildOFMStyle = async (isLight: boolean, onlyUkraine: boolean) => {
      const url = isLight ? OFM_LIGHT : OFM_DARK;
      const [styleRes, ukraineBoundary] = await Promise.all([
        fetch(url),
        onlyUkraine
          ? fetch(`/geoBoundaries-UKR-ADM0_simplified.geojson?${CACHE_VERSION}`, { cache: 'force-cache' }).then((res) => res.json())
          : Promise.resolve(null),
      ]);
      const style = (await styleRes.json()) as MutableMapStyle;

      // Layer ID patterns whose labels are too noisy at zoom 5-6 → hide
      const HIDE_LABEL_PATTERNS = ['state', 'country', 'continent', 'region', 'county', 'province'];
      const ukraineWithinFilter = ukraineBoundary ? ['within', ukraineBoundary] : null;

      style.layers.forEach((layer) => {
        if (ukraineWithinFilter && layer.source === 'openmaptiles') {
          const sourceLayer = layer['source-layer'];
          if (
            sourceLayer === 'place' ||
            sourceLayer === 'water_name' ||
            sourceLayer === 'poi' ||
            sourceLayer === 'aerodrome_label'
          ) {
            layer.filter = withFilter(layer.filter, ukraineWithinFilter);
          } else if (sourceLayer === 'boundary') {
            if (layer.id.includes('boundary_country')) {
              layer.filter = withFilter(layer.filter, [
                'any',
                ['==', ['get', 'adm0_l'], 'UKR'],
                ['==', ['get', 'adm0_r'], 'UKR'],
                ['==', ['get', 'claimed_by'], 'UA'],
              ]);
            } else {
              layer.filter = withFilter(layer.filter, ukraineWithinFilter);
            }
          }
        }

        if (!isLight) {
          if (layer.id === 'background' && layer.paint) layer.paint['background-color'] = '#161a23';
          if (layer.id === 'water' && layer.paint) layer.paint['fill-color'] = '#0b0f14';
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
        }
      });
      return style as StyleSpecification;
    };

    const loadGeoData = async () => {
      if (cachedGeoData) return cachedGeoData;
      const [oblastRes, districtRes] = await Promise.all([
        fetch(`/ukraine_oblasts.geojson?${CACHE_VERSION}`, { cache: 'force-cache' }),
        fetch(`/ukraine_raions_2020.geojson?${CACHE_VERSION}`, { cache: 'force-cache' }),
      ]);
      const oblastData = (await oblastRes.json()) as OblastFeatureCollection;
      const districtData = prepareDistrictGeoJson((await districtRes.json()) as FeatureCollection);
      oblastFcRef.current = oblastData;
      cachedGeoData = { oblastData, districtData };
      return cachedGeoData;
    };

    const applyBaseStyle = async (isLight: boolean) => {
      const requestSeq = ++styleRequestSeq;
      try {
        setMapReady(false);
        const [style, geoData] = await Promise.all([buildOFMStyle(isLight, ukraineOnlyRef.current), loadGeoData()]);
        if (requestSeq !== styleRequestSeq) return;
        // Store geo data so style.load handler can use it
        cachedGeoData = geoData;
        map.setStyle(style, { diff: false });
      } catch (err) {
        console.error('Failed to apply map style', err);
      }
    };
    applyBaseStyleRef.current = (isLight) => {
      void applyBaseStyle(isLight);
    };

    void applyBaseStyle(isLightMapTheme());

    const onThemeChange = () => {
      void applyBaseStyle(isLightMapTheme());
    };
    window.addEventListener('theme-change', onThemeChange);

    map.on('style.load', () => {
      // Skip only the empty placeholder style we set during initialization; ukraine-only
      // style intentionally starts with only a background layer before overlays are replayed.
      const styleLayerCount = map.getStyle()?.layers?.length ?? 0;
      if (styleLayerCount === 0) return;
      if (!cachedGeoData) return; // GeoJSON not yet loaded, skip

      const { oblastData, districtData } = cachedGeoData;
      const isLight = isLightMapTheme();
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
            'fill-extrusion-color': isLight ? '#e5e0d8' : '#21262d',
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
        originalAddLayer({ id: 'oblast-calm-dim', type: 'fill', source: 'oblasts', filter: ['==', ['get', 'HASC_1'], '__none__'], maxzoom: 11, paint: { 'fill-color': MAP_NIGHT.calmDimFill, 'fill-opacity': ['interpolate', ['linear'], ['zoom'], 5, 0.22, 8, 0.15, 11, 0.05] } }, firstSymbolId);
      }
      if (!map.getLayer('ukraine-border-stroke')) {
        originalAddLayer({ id: 'ukraine-border-stroke', type: 'line', source: 'ukraine-border-source', paint: { 'line-color': isLight ? '#1a1d21' : '#ffffff', 'line-opacity': 0.55, 'line-width': 2.5 } }, firstSymbolId);
      }
      if (!map.getLayer('oblast-alarm-fill')) {
        originalAddLayer({ id: 'oblast-alarm-fill', type: 'fill', source: 'oblasts', filter: ['==', ['get', 'HASC_1'], '__none__'], paint: { 'fill-color': MAP_NIGHT.alarmFillHex, 'fill-opacity': 0.36 } }, firstSymbolId);
      }
      if (!map.getLayer('district-alarm-fill')) {
        originalAddLayer({ id: 'district-alarm-fill', type: 'fill', source: 'districts', filter: ['==', ['get', 'regionKey'], '__none__'], paint: { 'fill-color': '#8f0000', 'fill-opacity': isLight ? 0.5 : 0.6 } }, firstSymbolId);
      }
      if (!map.getLayer('oblast-context-line')) {
        originalAddLayer({ id: 'oblast-context-line', type: 'line', source: 'oblasts', filter: ['!=', ['get', 'HASC_1'], '?'], paint: { 'line-color': MAP_NIGHT.oblastLine, 'line-opacity': 0.12, 'line-width': 0.6 } });
      }
      if (!map.getLayer('unclustered-point')) {
        originalAddLayer({ id: 'unclustered-point', type: 'symbol', source: 'threats', filter: ['!', ['has', 'point_count']], layout: { 'icon-image': ['get', 'micon'], 'icon-size': ['/', ['get', 'icon_px'], NORM_ICON_PX], 'icon-rotate': ['get', 'bearing'], 'icon-rotation-alignment': 'map', 'icon-allow-overlap': true, 'icon-ignore-placement': true, 'symbol-sort-key': ['get', 'prio'] }, paint: { 'icon-opacity': ['case', ['boolean', ['feature-state', 'hover'], false], ['min', 1, ['+', ['get', 'opacity'], 0.07]], ['get', 'opacity']] } });
      }

      // Re-apply alarms
      queueMicrotask(() => applyAlarmPaintRef.current(latestAlarmsRef.current));

      // Re-upload threat marker images
      if (latestMarkersRef.current.length > 0) {
        void ensureThreatImages(map, collectIconJobs(latestMarkersRef.current));
      }

      setMapReady(true);
    });

    map.on('load', () => {
      void (async () => {
        try {
          // Ensure geo data loaded (may already be cached)
          await loadGeoData();

          // Flag marker (Crimea)
          if (!document.querySelector('.crimea-flag-marker')) {
            const flagEl = document.createElement('div');
            flagEl.className = 'crimea-flag-marker';
            flagEl.innerHTML = '🇺🇦';
            flagEl.style.fontSize = '24px';
            flagEl.style.cursor = 'pointer';
            flagEl.style.pointerEvents = 'auto';
            const flagPopup = new maplibregl.Popup({ closeButton: false, closeOnClick: true, offset: 15 })
              .setHTML('<div style="font-weight: 600; color: #1a1d21; font-size: 14px; padding: 4px; font-family: sans-serif;">Крим - це Україна!</div>');
            new maplibregl.Marker({ element: flagEl }).setLngLat([34.1024, 44.9521]).setPopup(flagPopup).addTo(map);
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
            }
            const popup = new maplibregl.Popup({
              maxWidth: 'min(280px, calc(100vw - 24px))',
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

          map.fitBounds(
            [
              [MAP_BOUNDS.minLng, MAP_BOUNDS.minLat],
              [MAP_BOUNDS.maxLng, MAP_BOUNDS.maxLat],
            ],
            { animate: false, padding: 8 },
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
        const calmFilter =
          ukraineOnlyRef.current && hascs.length === 0
            ? ['!=', ['get', 'HASC_1'], '?']
            : oblastCalmDimFilter(hascs);
        map.setFilter('oblast-calm-dim', calmFilter as never);
      }

      if (map.getLayer('oblast-alarm-fill')) {
        map.setFilter('oblast-alarm-fill', oblastAlarmFillFilter(hascs) as never);
        map.setPaintProperty('oblast-alarm-fill', 'fill-opacity', 0.36);
      }

      if (map.getLayer('district-alarm-fill')) {
        map.setFilter('district-alarm-fill', districtAlarmFillFilter(districtKeys) as never);
        map.setPaintProperty('district-alarm-fill', 'fill-opacity', isLightMapTheme() ? 0.5 : 0.6);
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
      const w = 0.5 + 0.5 * Math.sin(Date.now() / 700);
      if (hascs.length > 0) {
        const alpha = 0.26 + 0.14 * w;
        map.setPaintProperty('oblast-alarm-fill', 'fill-opacity', alpha);
      }
      if (districtKeys.length > 0) {
        const alpha = (isLightMapTheme() ? 0.42 : 0.52) + 0.08 * w;
        map.setPaintProperty('district-alarm-fill', 'fill-opacity', alpha);
      }
    };

    const iv = window.setInterval(tick, 520);
    return () => window.clearInterval(iv);
  }, [mapReady, alarms]);

  useEffect(() => {
    if (!mapReady) return;
    const map = mapRef.current;
    if (!map?.isStyleLoaded()) return;

    let cancelled = false;
    const run = async () => {
      const fc = markersToGeoJSON(deferredMarkers);
      const jobs = collectIconJobs(deferredMarkers);
      await ensureThreatImages(map, jobs);
      if (cancelled) return;
      const src = map.getSource('threats') as maplibregl.GeoJSONSource | undefined;
      if (src) src.setData(fc as unknown as FeatureCollection);
      applyThreatMarkerFocus(map, markerFocusMidRef.current, NORM_ICON_PX);
    };

    const raf = requestAnimationFrame(() => {
      void run();
    });
    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
    };
  }, [deferredMarkers, mapReady]);

  return (
    <div
      className={`w-full h-full relative bg-[var(--neptun-map-canvas)]${ukraineOnly ? ' ukraine-only-map-mode' : ''}`}
    >
      <div ref={mapElRef} id="maplibre-map" className="absolute inset-0 z-[1]" />
    </div>
  );
}

export default memo(MapLibreContainer);

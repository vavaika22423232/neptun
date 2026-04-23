'use client';

import { useEffect, useRef, useState, useCallback, useDeferredValue, type MutableRefObject } from 'react';
import L from 'leaflet';
import type { Marker, Alarm, FusionTrajectory } from '@/types';
import { THREAT_ICONS, THREAT_NAMES } from '@/types';
import { CACHE_VERSION, SVG_FADE_START_ZOOM, SVG_FADE_END_ZOOM } from '@/lib/constants';
import { bearingToWebIconRotationCssDeg, resolveThreatBearingDeg } from '@/lib/threat-bearing';
import {
  getBasemapClassName,
  getBasemapUrl,
  isLowInteractionMode,
  pickBasemapKind,
  type MapBasemapKind,
} from '@/lib/map-leaflet-performance';

// Re-export MAP_BOUNDS locally to avoid circular deps
const MAP_BOUNDS = { minLat: 44.2, maxLat: 52.4, minLng: 22.0, maxLng: 40.2 } as const;

// Global state for Phase 2 optimizations (persists across Navigations)
const SVG_DOM_CACHE: Record<string, SVGElement> = {};
let TOOLTIP_SINGLETON: HTMLDivElement | null = null;

const MOVE_MIN_DIST_KM = 0.004;

function stableMarkerKey(m: Marker): string {
  const tid = m.track_id != null && String(m.track_id).trim().length > 0 ? String(m.track_id).trim() : '';
  if (tid) return `t:${tid}`;
  const id = m.id != null && String(m.id).trim().length > 0 ? String(m.id).trim() : '';
  if (id) return `i:${id}`;
  const lat = Number(m.lat);
  const lng = Number(m.lng);
  if (Number.isFinite(lat) && Number.isFinite(lng)) {
    return `p:${lat.toFixed(3)}_${lng.toFixed(3)}_${m.threat_type || 'x'}`;
  }
  return `u:${Math.random().toString(36).slice(2)}`;
}



function quickDistKm(aLat: number, aLng: number, bLat: number, bLng: number): number {
  const R = 6371;
  const dLat = ((bLat - aLat) * Math.PI) / 180;
  const dLng = ((bLng - aLng) * Math.PI) / 180;
  const x = dLat * R;
  const y = dLng * R * Math.cos((aLat * Math.PI) / 180);
  return Math.sqrt(x * x + y * y);
}

/** Compute marker opacity based on age: 1.0 (fresh) → 0.3 (20+ min old) */
function computeMarkerOpacity(marker: Marker): number {
  let epochMs = 0;
  if (marker.last_update_epoch) {
    epochMs = marker.last_update_epoch > 10000000000 ? marker.last_update_epoch : marker.last_update_epoch * 1000;
  } else if (marker.created_at_epoch) {
    epochMs = marker.created_at_epoch > 10000000000 ? marker.created_at_epoch : marker.created_at_epoch * 1000;
  } else if (marker.date) {
    epochMs = new Date(marker.date).getTime();
  }
  if (!epochMs) return 1;
  const ageMs = Date.now() - epochMs;
  if (ageMs <= 0) return 1;
  const MAX_AGE_MS = 20 * 60 * 1000; // 20 minutes
  const MIN_OPACITY = 0.3;
  const t = Math.min(ageMs / MAX_AGE_MS, 1);
  return 1 - t * (1 - MIN_OPACITY); // 1.0 → 0.3
}

/**
 * Dim approximate / predictive placements and low-confidence marks (aligned with Flutter `mapVisualOpacity`).
 */
function computeMapVisualOpacity(marker: Marker): number {
  const dc = marker.display_class;
  let base = 1;
  if (dc === 'region_signal') {
    base = 0.62;
  } else if (dc === 'corridor_or_bearing') {
    base = 0.52;
  } else if (!dc) {
    const pm = (marker.placement_mode || '').toLowerCase();
    if (pm === 'approximate') base = 0.62;
    else if (pm === 'predictive') base = 0.5;
  }

  const c100 = marker.confidence_0_100;
  if (c100 != null && Number.isFinite(c100)) {
    const c = Math.max(0, Math.min(100, c100)) / 100;
    if (c < 0.78) base *= 0.55 + 0.45 * c;
  } else if (marker.confidence != null && Number.isFinite(marker.confidence) && marker.confidence < 0.78) {
    const c = Math.max(0, Math.min(1, marker.confidence));
    base *= 0.55 + 0.45 * c;
  }
  return Math.max(0.32, Math.min(1, base));
}

function combinedMarkerOpacity(marker: Marker): number {
  return Math.max(0.12, Math.min(1, computeMarkerOpacity(marker) * computeMapVisualOpacity(marker)));
}

/** Stale / cached API payloads without display policy — default to legacy precise pin. */
function normalizeMarkerDisplay(marker: Marker): Marker {
  if (
    marker.display_class &&
    typeof marker.show_precise_pin === 'boolean' &&
    typeof marker.display_uncertainty_km === 'number'
  ) {
    return marker;
  }
  return {
    ...marker,
    display_class: 'corroborated_point',
    show_precise_pin: true,
    display_uncertainty_km: 0,
    display_trust_hint_uk: marker.display_trust_hint_uk ?? '',
  };
}

function destinationLatLng(lat: number, lng: number, bearingDeg: number, distKm: number): [number, number] {
  const R = 6371;
  const brng = (bearingDeg * Math.PI) / 180;
  const lat1 = (lat * Math.PI) / 180;
  const lng1 = (lng * Math.PI) / 180;
  const lat2 = Math.asin(
    Math.sin(lat1) * Math.cos(distKm / R) + Math.cos(lat1) * Math.sin(distKm / R) * Math.cos(brng),
  );
  const lng2 =
    lng1 +
    Math.atan2(
      Math.sin(brng) * Math.sin(distKm / R) * Math.cos(lat1),
      Math.cos(distKm / R) - Math.sin(lat1) * Math.sin(lat2),
    );
  return [(lat2 * 180) / Math.PI, (lng2 * 180) / Math.PI];
}

function corridorPolylineLatLngs(marker: Marker): L.LatLngExpression[] | null {
  if (marker.display_class !== 'corridor_or_bearing') return null;
  const t = marker.trajectory;
  if (t?.start && t?.end) return [t.start, t.end];
  if (t?.waypoints && t.waypoints.length >= 2) return t.waypoints;
  const brg = resolveThreatBearingDeg(marker);
  if (brg == null) return null;
  const end = destinationLatLng(marker.lat, marker.lng, brg, 32);
  return [[marker.lat, marker.lng], end];
}

function displayLayersSyncKey(marker: Marker, lat: number, lng: number): string {
  const pts = corridorPolylineLatLngs(marker);
  const pSig = pts ? JSON.stringify(pts) : '';
  return `${marker.display_class ?? ''}|${pSig}|${lat.toFixed(4)}_${lng.toFixed(4)}`;
}

function syncDisplayUncertaintyLayers(
  entry: MapMarkerEntry,
  marker: Marker,
  lat: number,
  lng: number,
  group: L.LayerGroup,
  trajGroup: L.LayerGroup,
) {
  const key = displayLayersSyncKey(marker, lat, lng);
  if (entry.lastDisplaySyncKey === key) return;
  entry.lastDisplaySyncKey = key;

  if (entry.uncertaintyCircle) {
    group.removeLayer(entry.uncertaintyCircle);
    entry.uncertaintyCircle = null;
  }
  if (entry.corridorLine) {
    trajGroup.removeLayer(entry.corridorLine);
    entry.corridorLine = null;
  }

  if (marker.display_class === 'corridor_or_bearing') {
    const pts = corridorPolylineLatLngs(marker);
    if (pts && pts.length >= 2) {
      entry.corridorLine = L.polyline(pts, {
        color: '#ffab40',
        weight: 2,
        opacity: 0.88,
      }).addTo(trajGroup);
    }
  }

  // Uncertainty rings (L.circle) intentionally not drawn — pins only; trust hints remain in popup/tooltip.
}

function mapHashCode(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = (Math.imul(hash, 31) + str.charCodeAt(i)) | 0;
  }
  return hash;
}

function jitterCoords(lat: number, lng: number, index: number, seedStr: string, radiusKm = 12): [number, number] {
  if (index === 0) return [lat, lng];
  let seed = mapHashCode(`${seedStr}_${index}`);
  const rand = () => {
    seed = (seed + 0x6D2B79F5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };

  const angle = rand() * 2 * Math.PI;
  const r = Math.sqrt(rand()) * radiusKm;
  const KM_TO_DEG_LAT = 1 / 111.32;
  const dLat = Math.cos(angle) * r * KM_TO_DEG_LAT;
  const dLng = Math.sin(angle) * r * (KM_TO_DEG_LAT / Math.cos(lat * Math.PI / 180));
  return [lat + dLat, lng + dLng];
}

/** CSS rotation for threat raster/SVG icons (see bearingToWebIconRotationCssDeg). */
function computeIconRotationCssDeg(marker: Marker): number {
  const brg = resolveThreatBearingDeg(marker);
  if (brg == null) return 0;
  return bearingToWebIconRotationCssDeg(brg);
}

/** Icon DOM (file, type) — full `setIcon` when this changes. */
function threatIconLayoutKey(marker: Marker): string {
  const tt = marker.threat_type || 'default';
  const icon = marker.marker_icon || THREAT_ICONS[tt] || 'shahed3.webp';
  return `${icon}|${tt}`;
}

/** Rounded bearing — cheap `img.style.transform` updates only. */
function threatIconBearingKey(marker: Marker): string {
  const brg = resolveThreatBearingDeg(marker);
  const r = brg != null ? Math.round(brg * 2) / 2 : 0;
  return String(r);
}

/** LRU cache for DivIcon instances — avoids recreating identical DOM trees */
const _iconCache = new Map<string, L.DivIcon>();
const ICON_CACHE_MAX = 120;

function buildThreatDivIcon(marker: Marker): L.DivIcon {
  const threatType = marker.threat_type || 'default';
  const iconFile = marker.marker_icon || THREAT_ICONS[threatType] || 'shahed3.webp';
  const isShahed =
    threatType === 'shahed' ||
    threatType === 'drone' ||
    threatType === 'uav' ||
    threatType === 'default';
  let size = isShahed ? 44 : 32;
  if (/fpvdrone/i.test(iconFile)) size = Math.round(size / 2);
  if (iconFile === 'shahed3.webp' || iconFile === 'icon_missile.svg') {
    size = Math.max(16, Math.round(size / 1.5));
    size = Math.round(size * 1.2);
  }
  const rotationAngle = computeIconRotationCssDeg(marker);

  // Cache key based solely on visual appearance (no per-count badge on map)
  const cacheKey = `${threatType}|${iconFile}|${size}|${Math.round(rotationAngle)}`;
  const cached = _iconCache.get(cacheKey);
  if (cached) return cached;

  const fetchPriority =
    threatType === 'shahed' ||
    threatType === 'drone' ||
    threatType === 'uav' ||
    threatType === 'default'
      ? 'high'
      : 'low';
  const shahedTheme =
    iconFile === 'shahed3.webp' &&
    (threatType === 'shahed' || threatType === 'drone' || threatType === 'uav' || threatType === 'default');
  const shahedRasterAttr = shahedTheme ? ' data-icon="shahed3"' : '';
  const html = `<div class="threat-marker" data-type="${threatType}"${shahedRasterAttr} style="position:relative;width:${size}px;height:${size}px;">
    <img src="/${iconFile}?${CACHE_VERSION}" alt="${threatType}" decoding="async" fetchpriority="${fetchPriority}"
         style="transform:rotate(${rotationAngle}deg);width:100%;height:100%;"
         onerror="this.src='/shahed3.webp?${CACHE_VERSION}'"></div>`;

  const icon = L.divIcon({
    className: 'threat-marker-icon',
    html,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });

  // Evict oldest when cache is full
  if (_iconCache.size >= ICON_CACHE_MAX) {
    const first = _iconCache.keys().next().value;
    if (first !== undefined) _iconCache.delete(first);
  }
  _iconCache.set(cacheKey, icon);
  return icon;
}

type MapMarkerEntry = {
  leafletMarker: L.Marker;
  polyline: L.Polyline | null;
  /** Tip dot at stem end (CircleMarker); kept as Layer for removeLayer. */
  arrowMarker: L.Layer | null;
  /** Public-map uncertainty ring (region_signal / corroborated_point). */
  uncertaintyCircle: L.Circle | null;
  corridorLine: L.Polyline | null;
  lastDisplaySyncKey?: string;
  fromLat: number;
  fromLng: number;
  toLat: number;
  toLng: number;
  animStart: number;
  animating: boolean;
  lastData: Marker;
  lastIconLayoutKey: string;
  lastIconBearingKey: string;
};

/** Re-bind touchend after Leaflet replaces the icon DOM (setIcon / rotation update). */
const markerTouchPopupRebind = new WeakMap<L.Marker, () => void>();

/**
 * WebView / mobile browsers often do not fire a synthetic `click` on divIcon markers.
 * Leaflet's map `click` also does not fire when the target is a marker. We listen for
 * `touchend` on the icon DOM and use preventDefault to suppress the duplicate click.
 */
function attachThreatMarkerPopupHandlers(
  leafletMarker: L.Marker,
  mapEntry: MapMarkerEntry,
  isAdminRef: MutableRefObject<boolean | undefined>,
) {
  let lastOpenAt = 0;
  const openPopup = () => {
    const now = Date.now();
    if (now - lastOpenAt < 320) return;
    lastOpenAt = now;
    hideTooltip();
    const m = mapEntry.lastData;
    const tt = m.threat_type || 'default';
    const popupHtml = buildMarkerPopup(m, tt, !!isAdminRef.current);
    leafletMarker.bindPopup(popupHtml, {
      className: 'admin-marker-popup',
      maxWidth: 260,
      closeButton: true,
    }).openPopup();
  };

  leafletMarker.on('click', openPopup);

  const touchHandler = (ev: Event) => {
    const te = ev as TouchEvent;
    if (te.touches?.length) return;
    if (!te.changedTouches || te.changedTouches.length !== 1) return;
    L.DomEvent.preventDefault(ev);
    openPopup();
  };

  const bindTouchToIcon = () => {
    const el = leafletMarker.getElement();
    if (!el) return;
    L.DomEvent.off(el, 'touchend', touchHandler);
    L.DomEvent.on(el, 'touchend', touchHandler);
  };

  markerTouchPopupRebind.set(leafletMarker, bindTouchToIcon);
  leafletMarker.on('add', bindTouchToIcon);
}

/** Clear any legacy trajectory layers (direction stems disabled). */
function updateEntryTrajectory(
  entry: MapMarkerEntry,
  _currentLat: number,
  _currentLng: number,
  trajGroup: L.LayerGroup,
) {
  if (entry.polyline) {
    trajGroup.removeLayer(entry.polyline);
    entry.polyline = null;
  }
  if (entry.arrowMarker) {
    trajGroup.removeLayer(entry.arrowMarker);
    entry.arrowMarker = null;
  }
}

interface MapContainerProps {
  markers: Marker[];
  alarms: Alarm[];
  fusionTrajectories: FusionTrajectory[];
  isAdmin?: boolean;
  onMarkerAction?: () => void;
  /** WebView in app (`?embed=1`) — same map + SVG as desktop */
  isEmbed?: boolean;
}

export default function MapContainer({ markers, alarms, fusionTrajectories, isAdmin, onMarkerAction, isEmbed = false }: MapContainerProps) {
  const deferredMarkers = useDeferredValue(markers);
  const deferredAlarms = useDeferredValue(alarms);

  const mapRef = useRef<L.Map | null>(null);
  const mapElRef = useRef<HTMLDivElement>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);
  const trajLayerRef = useRef<L.LayerGroup | null>(null);
  const fusionLayerRef = useRef<L.LayerGroup | null>(null);
  const statesSvgRef = useRef<SVGElement | null>(null);
  const districtsSvgRef = useRef<SVGElement | null>(null);
  const markerRegistryRef = useRef<Map<string, MapMarkerEntry>>(new Map());
  const animRafRef = useRef<number | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const isAdminRef = useRef(isAdmin);
  isAdminRef.current = isAdmin;
  const isInteractingRef = useRef(false);
  const lowInteractionRef = useRef(false);
  lowInteractionRef.current = isLowInteractionMode(isEmbed, typeof navigator !== 'undefined' ? navigator.userAgent : undefined);

  // Initialize map (must match original init order: tiles -> layers -> SVG -> events -> fitBounds)
  useEffect(() => {
    if (!mapElRef.current || mapRef.current) return;

    // Abort flag for React StrictMode (effect runs twice in dev)
    let aborted = false;

    const ukraineCenter: L.LatLngExpression = [48.5, 31.5];
    const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
    const basemap = pickBasemapKind(isEmbed, typeof navigator !== 'undefined' ? navigator.userAgent : undefined);
    const lowTileMode = basemap === 'rasterVectorDark';
    const lowInteraction = isLowInteractionMode(
      isEmbed,
      typeof navigator !== 'undefined' ? navigator.userAgent : undefined,
    );
    lowInteractionRef.current = lowInteraction;

    const map = L.map(mapElRef.current, {
      center: ukraineCenter,
      zoom: 6,
      minZoom: 5,
      // Hybrid labels need high zoom; OpenFreeMap is cheaper — cap zoom on low mode = fewer tile fetches
      maxZoom: lowTileMode ? 16 : 19,
      zoomControl: false,
      attributionControl: false,
      dragging: true,
      scrollWheelZoom: true,
      doubleClickZoom: true,
      touchZoom: true,
      preferCanvas: true, // Use Canvas for vectors (Fusion tracks)
      zoomAnimation: !lowInteraction,
      fadeAnimation: !lowInteraction,
      markerZoomAnimation: !lowInteraction,
      transform3DLimit: lowInteraction ? 1 : 2,
      zoomSnap: lowInteraction ? 1 : 0.5,
      zoomDelta: 1,
      wheelPxPerZoomLevel: 60,
      wheelDebounceTime: 60,
      inertia: !lowInteraction,
      inertiaDuration: lowInteraction ? 0.75 : 1.5,
      inertiaMaxSpeed: lowInteraction ? 1500 : 3000,
      easeLinearity: 0.1,
      keepBuffer: lowTileMode ? 1 : 2,
      maxBounds: [[40, 18], [56, 44]],
      maxBoundsViscosity: 0.8,
    } as any);

    mapRef.current = map;

    // Sequential init matching the original: tiles first, then layers, then SVG overlays
    (async () => {
      try {
        // 1. Load base map tiles (await like original)
        await loadMapTiles(map, { isMobile, basemap, lowTileMode });
      } catch (e) {
        console.warn('Map tiles load error:', e);
      }

      // Bail out if the effect was cleaned up during async loading
      if (aborted) return;

      // 2. Create layer groups AFTER tiles (matching original order)
      const trajGroup = L.layerGroup().addTo(map);
      const fusionGroup = L.layerGroup().addTo(map);
      const markersGroup = L.layerGroup().addTo(map);
      trajLayerRef.current = trajGroup;
      fusionLayerRef.current = fusionGroup;
      markersLayerRef.current = markersGroup;

      // 3. Load SVG overlays (await like original)
      try {
        const svgRefs = await loadSvgOverlays(map, {
          skipOblastNames: false,
          skipDetailedDistricts: false,
        });
        if (aborted) return;
        if (svgRefs) {
          statesSvgRef.current = svgRefs.statesSvg;
          districtsSvgRef.current = svgRefs.districtsSvg;
        }
      } catch (e) {
        console.warn('SVG overlay load error:', e);
      }

      if (aborted) return;

      // 4. Handle zoom changes - fade SVG at high zoom (rAF-throttle: `zoom` fires very often; INP)
      let opacityRaf: number | null = null;
      const scheduleOpacityUpdate = () => {
        if (opacityRaf != null) return;
        opacityRaf = requestAnimationFrame(() => {
          opacityRaf = null;
          updateSvgOpacity(map);
        });
      };

      map.on('movestart', () => { isInteractingRef.current = true; });
      map.on('moveend', () => { 
        // Delay resetting slightly to allow Leaflet's internal states to settle
        setTimeout(() => { isInteractingRef.current = false; }, 100);
      });
      map.on('zoomstart', () => { isInteractingRef.current = true; });
      map.on('zoomend', () => {
        setTimeout(() => { isInteractingRef.current = false; }, 100);
        if (opacityRaf != null) {
          cancelAnimationFrame(opacityRaf);
          opacityRaf = null;
        }
        updateSvgOpacity(map);
      });
      map.on('zoom', scheduleOpacityUpdate);

      // 5. Initial opacity update
      updateSvgOpacity(map);

      // 6. Fit to Ukraine bounds
      const bounds = L.latLngBounds(
        [MAP_BOUNDS.minLat, MAP_BOUNDS.minLng],
        [MAP_BOUNDS.maxLat, MAP_BOUNDS.maxLng]
      );
      map.fitBounds(bounds, { animate: false });

      setIsLoaded(true);
    })();

    return () => {
      aborted = true;
      if (animRafRef.current != null) {
        cancelAnimationFrame(animRafRef.current);
        animRafRef.current = null;
      }
      markerRegistryRef.current.clear();
      map.remove();
      mapRef.current = null;
    };
  }, [isEmbed]);

  // Register admin action handlers on window (for popup button onclick)
  useEffect(() => {
    if (!isAdmin) return;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const w = window as any;

    const adminJsonHeaders = (): Record<string, string> => {
      const h: Record<string, string> = { 'Content-Type': 'application/json' };
      const secret = w.__ADMIN_SECRET;
      if (secret) h['X-Auth-Secret'] = String(secret);
      return h;
    };

    w.__adminDeleteMarker = async (id: string, lat: number, lng: number, text: string) => {
      try {
        const res = await fetch('/api/admin/markers/delete', {
          method: 'POST',
          headers: adminJsonHeaders(),
          body: JSON.stringify({ id: id || undefined, lat, lng, text }),
        });
        if (res.ok) {
          mapRef.current?.closePopup();
          onMarkerAction?.();
        } else {
          const err = await res.json().catch(() => ({}));
          alert('Помилка видалення: ' + (err.error || res.status));
        }
      } catch { alert('Помилка мережі'); }
    };

    w.__adminHideMarker = async (lat: number, lng: number, text: string) => {
      try {
        const res = await fetch('/api/admin/hidden/hide', {
          method: 'POST',
          headers: adminJsonHeaders(),
          body: JSON.stringify({ lat, lng, text, source: 'auto' }),
        });
        if (res.ok) {
          mapRef.current?.closePopup();
          onMarkerAction?.();
        } else {
          alert('Помилка приховування');
        }
      } catch { alert('Помилка мережі'); }
    };

    return () => {
      delete w.__adminDeleteMarker;
      delete w.__adminHideMarker;
    };
  }, [isAdmin, onMarkerAction]);

  const scheduleAnimFrame = useCallback(() => {
    // Phase 2: JS loop for markers removed. Movement is now 100% CSS-driven.
    // If we need custom layers that don't support CSS transitions (like Canvas lines),
    // we would add them here.
  }, []);

  const syncMarkers = useCallback(
    (markersData: Marker[]) => {
      const group = markersLayerRef.current;
      const trajGroup = trajLayerRef.current;
      if (!group || !trajGroup) return;

      const registry = markerRegistryRef.current;

      // Iterate markers directly — avoid expensive sort on each update
      const seen = new Set<string>();

      for (const raw of markersData) {
        const marker = normalizeMarkerDisplay(raw);
        const lat = parseFloat(String(marker.lat));
        const lng = parseFloat(String(marker.lng));
        if (isNaN(lat) || isNaN(lng)) continue;
        if (
          lat < MAP_BOUNDS.minLat ||
          lat > MAP_BOUNDS.maxLat ||
          lng < MAP_BOUNDS.minLng ||
          lng > MAP_BOUNDS.maxLng
        ) {
          continue;
        }

        const key = stableMarkerKey(marker);
        seen.add(key);
        const layoutKey = threatIconLayoutKey(marker);
        const bearingKey = threatIconBearingKey(marker);

        let entry = registry.get(key);
        if (!entry) {
          const icon = buildThreatDivIcon(marker);
          const leafletMarker = L.marker([lat, lng], { icon });
          const mapEntry: MapMarkerEntry = {
            leafletMarker,
            polyline: null,
            arrowMarker: null,
            uncertaintyCircle: null,
            corridorLine: null,
            fromLat: lat,
            fromLng: lng,
            toLat: lat,
            toLng: lng,
            animStart: 0,
            animating: false,
            lastData: marker,
            lastIconLayoutKey: layoutKey,
            lastIconBearingKey: bearingKey,
          };

          leafletMarker.on('mouseover', (e: L.LeafletMouseEvent) => {
            showTooltip(e.originalEvent, mapEntry.lastData, mapEntry.lastData.threat_type || 'default');
          });
          leafletMarker.on('mouseout', hideTooltip);

          // Tap/click + touchend (WebView): show popup for everyone.
          attachThreatMarkerPopupHandlers(leafletMarker, mapEntry, isAdminRef);

          group.addLayer(leafletMarker);
          registry.set(key, mapEntry);
          entry = mapEntry;
          updateEntryTrajectory(entry, lat, lng, trajGroup);

          // Age × placement/confidence (use event since DOM may not be ready yet)
          const opacity = combinedMarkerOpacity(marker);
          leafletMarker.once('add', () => {
            const el = leafletMarker.getElement();
            if (el) (el as HTMLElement).style.opacity = String(opacity);
          });
          // If already added, apply directly
          const el = leafletMarker.getElement();
          if (el) (el as HTMLElement).style.opacity = String(opacity);
          syncDisplayUncertaintyLayers(mapEntry, marker, lat, lng, group, trajGroup);
        } else {
          entry.lastData = marker;
          const layout = threatIconLayoutKey(marker);
          const bearing = threatIconBearingKey(marker);
          const rot = computeIconRotationCssDeg(marker);
          if (layout !== entry.lastIconLayoutKey) {
            entry.lastIconLayoutKey = layout;
            entry.lastIconBearingKey = bearing;
            entry.leafletMarker.setIcon(buildThreatDivIcon(marker));
            markerTouchPopupRebind.get(entry.leafletMarker)?.();
          } else if (bearing !== entry.lastIconBearingKey) {
            entry.lastIconBearingKey = bearing;
            const markerEl = entry.leafletMarker.getElement();
            const img = markerEl?.querySelector('img') as HTMLElement;
            if (img) {
              img.style.transform = `rotate(${rot}deg)`;
            } else {
              entry.leafletMarker.setIcon(buildThreatDivIcon(marker));
              markerTouchPopupRebind.get(entry.leafletMarker)?.();
            }
          }

          const cur = entry.leafletMarker.getLatLng();
          const dist = quickDistKm(cur.lat, cur.lng, lat, lng);

          if (dist >= MOVE_MIN_DIST_KM) {
            const map = mapRef.current;
            const el = entry.leafletMarker.getElement();
            const inner = el?.querySelector('.threat-marker') as HTMLElement;

            // Skip visual glide if map is busy zooming or being dragged to prevent coordinate conflicts
            const isMapStatic = !isInteractingRef.current;

            if (map && isMapStatic && inner && !lowInteractionRef.current) {
              // Relative Offset Glide Strategy (Prevents jitter during map pan)
              const oldPoint = map.latLngToLayerPoint(cur);
              const newPoint = map.latLngToLayerPoint([lat, lng]);
              const dx = oldPoint.x - newPoint.x;
              const dy = oldPoint.y - newPoint.y;

              const rot = computeIconRotationCssDeg(marker);
              
              // 1. Immediately move container to new coordinate
              entry.leafletMarker.setLatLng([lat, lng]);

              // 2. Shift inner element back to visually match old coordinate
              inner.classList.remove('gliding');
              inner.style.transform = `translate3d(${dx}px, ${dy}px, 0) rotate(${rot}deg)`;
              
              // 3. Glide inner element to center (0,0) relative to its container
              requestAnimationFrame(() => {
                inner.classList.add('gliding');
                inner.style.transform = `translate3d(0,0,0) rotate(${rot}deg)`;
              });

              // Clean up gliding class after it completes to save engine resources
              setTimeout(() => inner.classList.remove('gliding'), 1300);
            } else {
              entry.leafletMarker.setLatLng([lat, lng]);
            }

            entry.fromLat = lat;
            entry.fromLng = lng;
            entry.toLat = lat;
            entry.toLng = lng;
          }

          // Update age × placement/confidence
          const el = entry.leafletMarker.getElement();
          if (el) (el as HTMLElement).style.opacity = String(combinedMarkerOpacity(marker));
          syncDisplayUncertaintyLayers(entry, marker, lat, lng, group, trajGroup);
        }
      }

      for (const [key, entry] of registry) {
        if (seen.has(key)) continue;
        group.removeLayer(entry.leafletMarker);
        if (entry.uncertaintyCircle) group.removeLayer(entry.uncertaintyCircle);
        if (entry.corridorLine) trajGroup.removeLayer(entry.corridorLine);
        if (entry.polyline) trajGroup.removeLayer(entry.polyline);
        if (entry.arrowMarker) trajGroup.removeLayer(entry.arrowMarker);
        registry.delete(key);
      }
    },
    [],
  );

  useEffect(() => {
    if (!isLoaded || !markersLayerRef.current || !trajLayerRef.current) return;
    syncMarkers(deferredMarkers);
  }, [deferredMarkers, isLoaded, syncMarkers]);

  // Render alarms on SVG overlays
  // Track active alarm IDs to avoid unnecessary DOM churn
  const activeAlarmIdsRef = useRef<Set<string>>(new Set());

  const renderAlarms = useCallback((alarmsData: Alarm[]) => {
    const statesSvg = statesSvgRef.current;
    const districtsSvg = districtsSvgRef.current;

    // Build new alarm set
    const newAlarmIds = new Set<string>();
    for (const region of alarmsData) {
      if (region.activeAlerts?.length) {
        newAlarmIds.add(`${region.regionType}:${region.regionId}`);
      }
    }

    const prevAlarmIds = activeAlarmIdsRef.current;

    // Remove alarms that are no longer active (diff-based, not clear-all)
    for (const key of prevAlarmIds) {
      if (!newAlarmIds.has(key)) {
        const [type, id] = key.split(':');
        const svg = type === 'State' ? statesSvg : districtsSvg;
        if (svg) svg.querySelectorAll(`[id="${id}"]`).forEach((el) => el.classList.remove('alarm'));
      }
    }

    // Add new alarms
    for (const key of newAlarmIds) {
      if (!prevAlarmIds.has(key)) {
        const [type, id] = key.split(':');
        const svg = type === 'State' ? statesSvg : districtsSvg;
        if (svg) svg.querySelectorAll(`[id="${id}"]`).forEach((el) => el.classList.add('alarm'));
      }
    }

    activeAlarmIdsRef.current = newAlarmIds;
  }, []);

  // Render fusion trajectories
  const renderFusionTrajectories = useCallback((trajs: FusionTrajectory[]) => {
    const group = fusionLayerRef.current;
    if (!group) return;
    group.clearLayers();
    // DISABLED: Lines removed as requested
  }, []);

  useEffect(() => {
    if (!isLoaded) return;
    renderAlarms(deferredAlarms);
  }, [deferredAlarms, isLoaded, renderAlarms]);

  useEffect(() => {
    if (!isLoaded || !fusionLayerRef.current) return;
    renderFusionTrajectories(fusionTrajectories);
  }, [fusionTrajectories, isLoaded, renderFusionTrajectories]);

  return (
    <div className="w-full h-full relative">
      <div ref={mapElRef} id="leaflet-map" className="absolute inset-0 z-[1]" />
    </div>
  );
}

// ============================================
// Helper functions
// ============================================

type LoadTilesOpts = {
  isMobile: boolean;
  basemap: MapBasemapKind;
  lowTileMode: boolean;
};

async function loadMapTiles(map: L.Map, opts: LoadTilesOpts) {
  const { isMobile, basemap, lowTileMode } = opts;
  const url = getBasemapUrl(basemap);
  L.tileLayer(url, {
    attribution: '',
    maxZoom: lowTileMode ? 16 : 19,
    className: getBasemapClassName(basemap),
    updateWhenIdle: isMobile,
    updateWhenZooming: false,
    keepBuffer: lowTileMode ? 1 : 2,
    detectRetina: !isMobile,
  } as L.TileLayerOptions).addTo(map);
}

async function loadSvgOverlays(
  map: L.Map,
  opts: { skipOblastNames: boolean; skipDetailedDistricts: boolean },
): Promise<{ statesSvg: SVGElement; districtsSvg: SVGElement | null } | null> {
  try {
    const bounds = L.latLngBounds(
      [MAP_BOUNDS.minLat, MAP_BOUNDS.minLng],
      [MAP_BOUNDS.maxLat, MAP_BOUNDS.maxLng]
    );

    const svgUrls: string[] = [`/ukraine_states.svg?${CACHE_VERSION}`];
    if (!opts.skipDetailedDistricts) {
      svgUrls.push(`/ukraine_districts_detailed.svg?${CACHE_VERSION}`);
    }
    if (!opts.skipOblastNames) {
      svgUrls.push(`/ukraine_names.svg?${CACHE_VERSION}`);
    }

    const results: SVGElement[] = [];
    const parser = new DOMParser();

    for (const url of svgUrls) {
      if (SVG_DOM_CACHE[url]) {
        results.push(SVG_DOM_CACHE[url].cloneNode(true) as SVGElement);
        continue;
      }
      const res = await fetch(url, { cache: 'force-cache' });
      const text = await res.text();
      const svg = parser.parseFromString(text, 'image/svg+xml').documentElement as unknown as SVGElement;
      SVG_DOM_CACHE[url] = svg; // Cache the original template
      results.push(svg.cloneNode(true) as SVGElement);
    }

    let i = 0;
    const statesSvg = results[i++] as SVGElement;
    statesSvg.classList.add('svg-states-layer');
    L.svgOverlay(statesSvg, bounds, { interactive: true, zIndex: 100 }).addTo(map);

    let districtsSvg: SVGElement | null = null;
    if (!opts.skipDetailedDistricts) {
      districtsSvg = results[i++] as SVGElement;
      districtsSvg.classList.add('svg-districts-layer');
      L.svgOverlay(districtsSvg, bounds, { interactive: true, zIndex: 101 }).addTo(map);
    }

    if (!opts.skipOblastNames) {
      const namesSvg = results[i] as SVGElement;
      namesSvg.classList.add('svg-names-layer');
      L.svgOverlay(namesSvg, bounds, { interactive: false, zIndex: 102 }).addTo(map);
    }

    return { statesSvg, districtsSvg };
  } catch (error) {
    console.error('Error loading SVG overlays:', error);
    return null;
  }
}

function updateSvgOpacity(map: L.Map) {
  const zoom = map.getZoom();
  const container = document.getElementById('leaflet-map');

  let fadeOpacity: number;

  if (zoom < SVG_FADE_START_ZOOM) {
    fadeOpacity = 1;
  } else if (zoom >= SVG_FADE_END_ZOOM) {
    fadeOpacity = 0;
  } else {
    const progress = (zoom - SVG_FADE_START_ZOOM) / (SVG_FADE_END_ZOOM - SVG_FADE_START_ZOOM);
    fadeOpacity = 1 - progress;
  }

  if (container) {
    container.style.setProperty('--bg-opacity', String(fadeOpacity));
    container.style.setProperty('--map-opacity', String(1 - fadeOpacity));
  }

  // Apply to SVG overlays
  const svgOpacity = fadeOpacity * 0.82;
  document.querySelectorAll('.svg-states-layer, .svg-districts-layer').forEach((el) => {
    (el as HTMLElement).style.opacity = String(svgOpacity);
  });
  document.querySelectorAll('.svg-names-layer').forEach((el) => {
    (el as HTMLElement).style.opacity = String(fadeOpacity);
  });
}

/** Format ISO timestamp to Kyiv time (HH:MM DD.MM.YYYY) */
function formatKyivTime(isoStr: string): string {
  try {
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return isoStr;
    return d.toLocaleString('uk-UA', {
      timeZone: 'Europe/Kyiv',
      hour: '2-digit',
      minute: '2-digit',
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  } catch {
    return isoStr;
  }
}

function showTooltip(event: MouseEvent, marker: Marker, threatType: string) {
  if (!TOOLTIP_SINGLETON) {
    TOOLTIP_SINGLETON = document.createElement('div');
    TOOLTIP_SINGLETON.className = 'marker-tooltip';
    TOOLTIP_SINGLETON.id = 'active-tooltip';
    document.body.appendChild(TOOLTIP_SINGLETON);
  }

  const tooltip = TOOLTIP_SINGLETON;
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

function hideTooltip() {
  if (TOOLTIP_SINGLETON) {
    TOOLTIP_SINGLETON.style.opacity = '0';
  }
}

function buildMarkerPopup(marker: Marker, threatType: string, isAdminUser: boolean): string {
  const typeName = THREAT_NAMES[threatType] || threatType;
  const trustEsc = (marker.display_trust_hint_uk || '').replace(/</g, '&lt;');
  const trustBlock = trustEsc
    ? `<div style="font-size:10px;color:rgba(255,171,64,0.95);margin-bottom:8px;line-height:1.35;">${trustEsc}</div>`
    : '';
  const placeEsc = (marker.place || 'Невідомо').replace(/</g, '&lt;');
  const brg = resolveThreatBearingDeg(marker);
  const courseBlock =
    brg != null
      ? `<div style="font-size:10px;color:rgba(255,171,64,0.95);margin-top:4px;">Курс ~${Math.round(brg)}° (за даними карти)</div>`
      : '';
  const dateBlock = marker.date
    ? `<div style="font-size:10px;color:rgba(255,255,255,0.4);margin-bottom:${isAdminUser ? '8px' : '0'};">${formatKyivTime(marker.date)}</div>`
    : '';

  let actions = '';
  if (isAdminUser) {
    const markerId = (marker.id || '').replace(/'/g, "\\'");
    const markerLat = marker.lat;
    const markerLng = marker.lng;
    const markerText = (marker.text || '').replace(/'/g, "\\'").replace(/\n/g, ' ').substring(0, 80);
    actions = `
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:6px;">
        <button onclick="window.__adminDeleteMarker('${markerId}',${markerLat},${markerLng},'${markerText}')"
          style="background:rgba(255,82,82,0.2);color:#ff5252;border:1px solid rgba(255,82,82,0.3);border-radius:8px;padding:5px 12px;font-size:11px;cursor:pointer;display:flex;align-items:center;gap:4px;">
          <span class="material-icons" style="font-size:14px;">delete</span>Видалити
        </button>
        <button onclick="window.__adminHideMarker(${markerLat},${markerLng},'${markerText}')"
          style="background:rgba(255,171,64,0.2);color:#ffab40;border:1px solid rgba(255,171,64,0.3);border-radius:8px;padding:5px 12px;font-size:11px;cursor:pointer;display:flex;align-items:center;gap:4px;">
          <span class="material-icons" style="font-size:14px;">visibility_off</span>Сховати
        </button>
      </div>`;
  }

  return `
    <div style="font-family:-apple-system,sans-serif;color:#fff;min-width:200px;">
      ${trustBlock}
      <div style="font-size:13px;font-weight:600;margin-bottom:6px;">${typeName}</div>
      <div style="font-size:11px;color:rgba(255,255,255,0.7);margin-bottom:2px;">${placeEsc}</div>
      ${courseBlock}
      ${dateBlock}
      ${actions}
    </div>
  `;
}

'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import L from 'leaflet';
import type { Marker, Alarm, FusionTrajectory } from '@/types';
import { THREAT_ICONS, THREAT_NAMES } from '@/types';
import { CACHE_VERSION, SVG_FADE_START_ZOOM, SVG_FADE_END_ZOOM } from '@/lib/constants';

// Re-export MAP_BOUNDS locally to avoid circular deps
const MAP_BOUNDS = { minLat: 44.2, maxLat: 52.4, minLng: 22.0, maxLng: 40.2 } as const;

/** Smooth glide between server positions (SSE / poll), not instant jumps */
const MOVE_ANIM_MS = 5000;
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

function easeOutCubic(t: number): number {
  return 1 - (1 - t) ** 3;
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

function computeRotationDeg(marker: Marker): number {
  const traj = marker.trajectory;
  let rotationAngle = 0;
  if (traj?.start && traj?.end) {
    const dLng = traj.end[1] - traj.start[1];
    const dLat = traj.end[0] - traj.start[0];
    if (Math.abs(dLat) > 0.001 || Math.abs(dLng) > 0.001) {
      rotationAngle = Math.atan2(dLng, dLat) * (180 / Math.PI) + 180;
    }
  } else if (marker.course_bearing != null) {
    rotationAngle = marker.course_bearing + 180;
  }
  return rotationAngle;
}

function rotationVisualKey(marker: Marker): string {
  const r = Math.round(computeRotationDeg(marker) * 2) / 2;
  const tt = marker.threat_type || 'default';
  const icon = marker.marker_icon || THREAT_ICONS[tt] || 'shahed3.webp';
  const c = marker.count ?? 1;
  return `${r}|${icon}|${tt}|${c}`;
}

function buildThreatDivIcon(marker: Marker): L.DivIcon {
  const threatType = marker.threat_type || 'default';
  const iconFile = marker.marker_icon || THREAT_ICONS[threatType] || 'shahed3.webp';
  const isShahed = threatType === 'shahed' || threatType === 'drone';
  const size = isShahed ? 44 : 32;
  const rotationAngle = computeRotationDeg(marker);
  const count = Number(marker.count) || 1;

  let badge = '';
  if (count > 1) {
    badge = `<span style="position:absolute;top:-6px;right:-6px;background:#ff2a5f;color:#fff;font-size:11px;font-weight:700;min-width:18px;height:18px;line-height:18px;text-align:center;border-radius:9px;padding:0 4px;pointer-events:none;box-shadow:0 0 6px rgba(255,42,95,0.6);">${count}</span>`;
  }

  const html = `<div class="threat-marker" data-type="${threatType}" style="position:relative;width:${size}px;height:${size}px;">
    <img src="/${iconFile}?${CACHE_VERSION}" alt="${threatType}" loading="lazy" decoding="async"
         style="transform:rotate(${rotationAngle}deg);width:100%;height:100%;"
         onerror="this.src='/shahed3.webp'">${badge}</div>`;

  return L.divIcon({
    className: 'threat-marker-icon',
    html,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

type MapMarkerEntry = {
  leafletMarker: L.Marker;
  polyline: L.Polyline | null;
  arrowMarker: L.Marker | null;
  fromLat: number;
  fromLng: number;
  toLat: number;
  toLng: number;
  animStart: number;
  animating: boolean;
  lastData: Marker;
  lastRotationKey: string;
};

function updateEntryTrajectory(
  entry: MapMarkerEntry,
  startLat: number,
  startLng: number,
  trajGroup: L.LayerGroup,
) {
  // COMPLETELY DISABLED: Remove any existing lines/arrows and return
  if (entry.polyline) {
    trajGroup.removeLayer(entry.polyline);
    entry.polyline = null;
  }
  if (entry.arrowMarker) {
    trajGroup.removeLayer(entry.arrowMarker);
    entry.arrowMarker = null;
  }
  return;
}

interface MapContainerProps {
  markers: Marker[];
  alarms: Alarm[];
  fusionTrajectories: FusionTrajectory[];
  isAdmin?: boolean;
  onMarkerAction?: () => void;
}

export default function MapContainer({ markers, alarms, fusionTrajectories, isAdmin, onMarkerAction }: MapContainerProps) {
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

  // Initialize map (must match original init order: tiles -> layers -> SVG -> events -> fitBounds)
  useEffect(() => {
    if (!mapElRef.current || mapRef.current) return;

    // Abort flag for React StrictMode (effect runs twice in dev)
    let aborted = false;

    const ukraineCenter: L.LatLngExpression = [48.5, 31.5];
    const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);

    const map = L.map(mapElRef.current, {
      center: ukraineCenter,
      zoom: 6,
      minZoom: 5,
      maxZoom: 18,
      zoomControl: false,
      attributionControl: false,
      dragging: true,
      scrollWheelZoom: true,
      doubleClickZoom: true,
      touchZoom: true,
      zoomAnimation: true,
      fadeAnimation: true,
      markerZoomAnimation: true,
      transform3DLimit: 2, // Helps with some Android rendering issues
      zoomSnap: 0.1, // Small snap for better trackpad feel
      zoomDelta: 2,
      wheelPxPerZoomLevel: 10, // Ultra-sensitive for Mac trackpad/pinch
      wheelDebounceTime: 40,
      inertia: true,
      inertiaDuration: 1.5,
      inertiaMaxSpeed: 3000,
      easeLinearity: 0.1,
      keepBuffer: 3,
      tap: false, // Performance & double-tap fix for Android/mobile
      maxBounds: [[40, 18], [56, 44]],
      maxBoundsViscosity: 0.8,
    } as any);

    mapRef.current = map;

    // Sequential init matching the original: tiles first, then layers, then SVG overlays
    (async () => {
      try {
        // 1. Load base map tiles (await like original)
        await loadMapTiles(map, isMobile);
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
        const svgRefs = await loadSvgOverlays(map);
        if (aborted) return;
        if (svgRefs) {
          statesSvgRef.current = svgRefs.statesSvg;
          districtsSvgRef.current = svgRefs.districtsSvg;
        }
      } catch (e) {
        console.warn('SVG overlay load error:', e);
      }

      if (aborted) return;

      // 4. Handle zoom changes - fade SVG at high zoom
      map.on('zoomend', () => updateSvgOpacity(map));
      map.on('zoom', () => updateSvgOpacity(map));

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
  }, []);

  // Register admin action handlers on window (for popup button onclick)
  useEffect(() => {
    if (!isAdmin) return;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const w = window as any;

    w.__adminDeleteMarker = async (id: string, lat: number, lng: number, text: string) => {
      try {
        const res = await fetch('/api/admin/markers/delete', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
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
          headers: { 'Content-Type': 'application/json' },
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
    if (animRafRef.current != null) return;
    const step = () => {
      animRafRef.current = null;
      const registry = markerRegistryRef.current;
      const trajGroup = trajLayerRef.current;
      if (!trajGroup) return;

      const now = performance.now();
      let needsNext = false;

      for (const entry of registry.values()) {
        if (!entry.animating) continue;

        const elapsed = now - entry.animStart;
        const t = Math.min(1, elapsed / MOVE_ANIM_MS);

        if (t >= 1) {
          entry.leafletMarker.setLatLng([entry.toLat, entry.toLng]);
          entry.fromLat = entry.toLat;
          entry.fromLng = entry.toLng;
          entry.animating = false;
          updateEntryTrajectory(entry, entry.toLat, entry.toLng, trajGroup);
        } else {
          const e = easeOutCubic(t);
          const lat = entry.fromLat + (entry.toLat - entry.fromLat) * e;
          const lng = entry.fromLng + (entry.toLng - entry.fromLng) * e;
          entry.leafletMarker.setLatLng([lat, lng]);
          updateEntryTrajectory(entry, lat, lng, trajGroup);
          needsNext = true;
        }
      }

      if (needsNext) {
        animRafRef.current = requestAnimationFrame(step);
      }
    };
    animRafRef.current = requestAnimationFrame(step);
  }, []);

  const syncMarkers = useCallback(
    (markersData: Marker[], requestAnim: () => void) => {
      const group = markersLayerRef.current;
      const trajGroup = trajLayerRef.current;
      if (!group || !trajGroup) return;

      const registry = markerRegistryRef.current;

      // Use markers as-is — count badge handles groups visually
      const explodedData = markersData;

      const sorted = [...explodedData].sort((a, b) => (b.date || '').localeCompare(a.date || ''));
      const seen = new Set<string>();

      for (const marker of sorted) {
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
        const rotKey = rotationVisualKey(marker);

        let entry = registry.get(key);
        if (!entry) {
          const icon = buildThreatDivIcon(marker);
          const leafletMarker = L.marker([lat, lng], { icon });
          const mapEntry: MapMarkerEntry = {
            leafletMarker,
            polyline: null,
            arrowMarker: null,
            fromLat: lat,
            fromLng: lng,
            toLat: lat,
            toLng: lng,
            animStart: 0,
            animating: false,
            lastData: marker,
            lastRotationKey: rotKey,
          };

          leafletMarker.on('mouseover', (e: L.LeafletMouseEvent) => {
            showTooltip(e.originalEvent, mapEntry.lastData, mapEntry.lastData.threat_type || 'default');
          });
          leafletMarker.on('mouseout', hideTooltip);

          if (isAdmin) {
            leafletMarker.on('click', () => {
              hideTooltip();
              const m = mapEntry.lastData;
              const tt = m.threat_type || 'default';
              const popupHtml = buildAdminPopup(m, tt);
              leafletMarker.bindPopup(popupHtml, {
                className: 'admin-marker-popup',
                maxWidth: 260,
                closeButton: true,
              }).openPopup();
            });
          }

          group.addLayer(leafletMarker);
          registry.set(key, mapEntry);
          entry = mapEntry;
          updateEntryTrajectory(entry, lat, lng, trajGroup);

          // Apply age-based opacity (use event since DOM may not be ready yet)
          const opacity = computeMarkerOpacity(marker);
          leafletMarker.once('add', () => {
            const el = leafletMarker.getElement();
            if (el) (el as HTMLElement).style.opacity = String(opacity);
          });
          // If already added, apply directly
          const el = leafletMarker.getElement();
          if (el) (el as HTMLElement).style.opacity = String(opacity);
        } else {
          entry.lastData = marker;
          if (rotKey !== entry.lastRotationKey) {
            entry.lastRotationKey = rotKey;
            entry.leafletMarker.setIcon(buildThreatDivIcon(marker));
          }

          const cur = entry.leafletMarker.getLatLng();
          const dist = quickDistKm(cur.lat, cur.lng, lat, lng);

          if (dist < MOVE_MIN_DIST_KM) {
            entry.leafletMarker.setLatLng([lat, lng]);
            entry.fromLat = lat;
            entry.fromLng = lng;
            entry.toLat = lat;
            entry.toLng = lng;
            entry.animating = false;
            updateEntryTrajectory(entry, lat, lng, trajGroup);
          } else {
            entry.fromLat = cur.lat;
            entry.fromLng = cur.lng;
            entry.toLat = lat;
            entry.toLng = lng;
            entry.animStart = performance.now();
            entry.animating = true;
            requestAnim();
          }

          // Update age-based opacity
          const el = entry.leafletMarker.getElement();
          if (el) (el as HTMLElement).style.opacity = String(computeMarkerOpacity(marker));
        }
      }

      for (const [key, entry] of registry) {
        if (seen.has(key)) continue;
        group.removeLayer(entry.leafletMarker);
        if (entry.polyline) trajGroup.removeLayer(entry.polyline);
        if (entry.arrowMarker) trajGroup.removeLayer(entry.arrowMarker);
        registry.delete(key);
      }
    },
    [isAdmin],
  );

  useEffect(() => {
    if (!isLoaded || !markersLayerRef.current || !trajLayerRef.current) return;
    syncMarkers(markers, scheduleAnimFrame);
  }, [markers, isLoaded, scheduleAnimFrame, syncMarkers]);

  // Render alarms on SVG overlays
  const renderAlarms = useCallback((alarmsData: Alarm[]) => {
    const statesSvg = statesSvgRef.current;
    const districtsSvg = districtsSvgRef.current;

    // Clear all existing alarms
    if (statesSvg) statesSvg.querySelectorAll('.alarm').forEach((el) => el.classList.remove('alarm'));
    if (districtsSvg) districtsSvg.querySelectorAll('.alarm').forEach((el) => el.classList.remove('alarm'));

    alarmsData.forEach((region) => {
      if (!region.activeAlerts?.length) return;

      if (region.regionType === 'State' && statesSvg) {
        statesSvg.querySelectorAll(`[id="${region.regionId}"]`).forEach((el) => el.classList.add('alarm'));
      } else if (region.regionType === 'District' && districtsSvg) {
        districtsSvg.querySelectorAll(`[id="${region.regionId}"]`).forEach((el) => el.classList.add('alarm'));
      }
    });
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
    renderAlarms(alarms);
  }, [alarms, isLoaded, renderAlarms]);

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

async function loadMapTiles(map: L.Map, isMobile: boolean) {
  // Base Satellite + Labels (Google Maps Hybrid, Ukrainian Language)
  L.tileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}&hl=uk', {
    attribution: '',
    maxZoom: 19,
    className: 'dark-satellite-layer',
  }).addTo(map);

  // Clean Light Map (CartoDB Positron without labels, since we have our SVG labels)
  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png', {
    attribution: '',
    subdomains: 'abcd',
    maxZoom: 19,
    className: 'light-streets-layer',
  }).addTo(map);
}

async function loadSvgOverlays(map: L.Map): Promise<{ statesSvg: SVGElement; districtsSvg: SVGElement } | null> {
  try {
    const bounds = L.latLngBounds(
      [MAP_BOUNDS.minLat, MAP_BOUNDS.minLng],
      [MAP_BOUNDS.maxLat, MAP_BOUNDS.maxLng]
    );

    const [statesRes, districtsRes, namesRes] = await Promise.all([
      fetch(`/ukraine_states.svg?${CACHE_VERSION}`, { cache: 'force-cache' }),
      fetch(`/ukraine_districts_detailed.svg?${CACHE_VERSION}`, { cache: 'force-cache' }),
      fetch(`/ukraine_names.svg?${CACHE_VERSION}`, { cache: 'force-cache' }),
    ]);

    const [statesText, districtsText, namesText] = await Promise.all([
      statesRes.text(),
      districtsRes.text(),
      namesRes.text(),
    ]);

    const parser = new DOMParser();
    const statesSvg = parser.parseFromString(statesText, 'image/svg+xml').documentElement as unknown as SVGElement;
    const districtsSvg = parser.parseFromString(districtsText, 'image/svg+xml').documentElement as unknown as SVGElement;
    const namesSvg = parser.parseFromString(namesText, 'image/svg+xml').documentElement as unknown as SVGElement;

    statesSvg.classList.add('svg-states-layer');
    districtsSvg.classList.add('svg-districts-layer');
    namesSvg.classList.add('svg-names-layer');

    // Add overlays to map in correct order (states -> districts -> names)
    L.svgOverlay(statesSvg, bounds, { interactive: true, zIndex: 100 }).addTo(map);
    L.svgOverlay(districtsSvg, bounds, { interactive: true, zIndex: 101 }).addTo(map);
    L.svgOverlay(namesSvg, bounds, { interactive: false, zIndex: 102 }).addTo(map);

    console.log('SVG overlays loaded and positioned');
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
  const svgOpacity = fadeOpacity * 0.7;
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
  hideTooltip();
  const tooltip = document.createElement('div');
  tooltip.className = 'marker-tooltip';
  tooltip.id = 'active-tooltip';

  const typeName = THREAT_NAMES[threatType] || threatType;
  tooltip.innerHTML = `
    <div class="tooltip-type">${typeName}</div>
    <div class="tooltip-place">${marker.place || 'Невідомо'}</div>
    ${marker.date ? `<div class="tooltip-time">${formatKyivTime(marker.date)}</div>` : ''}
  `;

  document.body.appendChild(tooltip);
  const rect = tooltip.getBoundingClientRect();
  let x = event.clientX + 15;
  let y = event.clientY + 15;
  if (x + rect.width > window.innerWidth) x = event.clientX - rect.width - 15;
  if (y + rect.height > window.innerHeight) y = event.clientY - rect.height - 15;
  tooltip.style.left = `${x}px`;
  tooltip.style.top = `${y}px`;
}

function hideTooltip() {
  document.getElementById('active-tooltip')?.remove();
}

function buildAdminPopup(marker: Marker, threatType: string): string {
  const typeName = THREAT_NAMES[threatType] || threatType;
  const markerId = (marker.id || '').replace(/'/g, "\\'");
  const markerLat = marker.lat;
  const markerLng = marker.lng;
  const markerText = (marker.text || '').replace(/'/g, "\\'").replace(/\n/g, ' ').substring(0, 80);

  return `
    <div style="font-family:-apple-system,sans-serif;color:#fff;min-width:200px;">
      <div style="font-size:13px;font-weight:600;margin-bottom:6px;">${typeName}</div>
      <div style="font-size:11px;color:rgba(255,255,255,0.7);margin-bottom:2px;">${(marker.place || 'Невідомо').replace(/</g, '&lt;')}</div>
      ${marker.date ? `<div style="font-size:10px;color:rgba(255,255,255,0.4);margin-bottom:8px;">${formatKyivTime(marker.date)}</div>` : ''}
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:6px;">
        <button onclick="window.__adminDeleteMarker('${markerId}',${markerLat},${markerLng},'${markerText}')"
          style="background:rgba(255,82,82,0.2);color:#ff5252;border:1px solid rgba(255,82,82,0.3);border-radius:8px;padding:5px 12px;font-size:11px;cursor:pointer;display:flex;align-items:center;gap:4px;">
          <span class="material-icons" style="font-size:14px;">delete</span>Видалити
        </button>
        <button onclick="window.__adminHideMarker(${markerLat},${markerLng},'${markerText}')"
          style="background:rgba(255,171,64,0.2);color:#ffab40;border:1px solid rgba(255,171,64,0.3);border-radius:8px;padding:5px 12px;font-size:11px;cursor:pointer;display:flex;align-items:center;gap:4px;">
          <span class="material-icons" style="font-size:14px;">visibility_off</span>Сховати
        </button>
      </div>
    </div>
  `;
}

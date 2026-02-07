'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import L from 'leaflet';
import type { Marker, Alarm, FusionTrajectory } from '@/types';
import { THREAT_ICONS, THREAT_NAMES } from '@/types';
import { CACHE_VERSION, SVG_FADE_START_ZOOM, SVG_FADE_END_ZOOM } from '@/lib/constants';

// Re-export MAP_BOUNDS locally to avoid circular deps
const MAP_BOUNDS = { minLat: 44.2, maxLat: 52.4, minLng: 22.0, maxLng: 40.2 } as const;

interface MapContainerProps {
  markers: Marker[];
  alarms: Alarm[];
  fusionTrajectories: FusionTrajectory[];
}

export default function MapContainer({ markers, alarms, fusionTrajectories }: MapContainerProps) {
  const mapRef = useRef<L.Map | null>(null);
  const mapElRef = useRef<HTMLDivElement>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);
  const trajLayerRef = useRef<L.LayerGroup | null>(null);
  const fusionLayerRef = useRef<L.LayerGroup | null>(null);
  const statesSvgRef = useRef<SVGElement | null>(null);
  const districtsSvgRef = useRef<SVGElement | null>(null);
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
      zoomAnimation: !isMobile,
      fadeAnimation: !isMobile,
      maxBounds: [[40, 18], [56, 44]],
      maxBoundsViscosity: 0.8,
    });

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
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Update markers when data changes
  useEffect(() => {
    if (!isLoaded || !markersLayerRef.current || !trajLayerRef.current) return;
    renderMarkers(markers);
  }, [markers, isLoaded]);

  // Update alarms when data changes
  useEffect(() => {
    if (!isLoaded) return;
    renderAlarms(alarms);
  }, [alarms, isLoaded]);

  // Update fusion trajectories
  useEffect(() => {
    if (!isLoaded || !fusionLayerRef.current) return;
    renderFusionTrajectories(fusionTrajectories);
  }, [fusionTrajectories, isLoaded]);

  // Render markers on the map
  const renderMarkers = useCallback((markersData: Marker[]) => {
    const group = markersLayerRef.current;
    const trajGroup = trajLayerRef.current;
    if (!group || !trajGroup) return;

    group.clearLayers();
    trajGroup.clearLayers();

    const sorted = [...markersData].sort((a, b) => {
      return (b.date || '').localeCompare(a.date || '');
    });

    sorted.forEach((marker) => {
      const lat = parseFloat(String(marker.lat));
      const lng = parseFloat(String(marker.lng));
      if (isNaN(lat) || isNaN(lng)) return;
      if (lat < MAP_BOUNDS.minLat || lat > MAP_BOUNDS.maxLat ||
          lng < MAP_BOUNDS.minLng || lng > MAP_BOUNDS.maxLng) return;

      const threatType = marker.threat_type || 'default';
      const iconFile = marker.marker_icon || THREAT_ICONS[threatType] || 'shahed3.webp';
      const isShahed = threatType === 'shahed' || threatType === 'drone';
      const size = isShahed ? 44 : 32;

      // Calculate rotation
      let rotationAngle = 0;
      const traj = marker.trajectory;
      if (traj?.start && traj?.end) {
        const dLng = traj.end[1] - traj.start[1];
        const dLat = traj.end[0] - traj.start[0];
        if (Math.abs(dLat) > 0.001 || Math.abs(dLng) > 0.001) {
          rotationAngle = Math.atan2(dLng, dLat) * (180 / Math.PI) - 90;
        }
      } else if (marker.course_bearing != null) {
        rotationAngle = marker.course_bearing - 90;
      }
      if (isShahed) rotationAngle -= 90;

      // Build HTML
      let html = `<div class="threat-marker" data-type="${threatType}" style="width:${size}px;height:${size}px;">
        <img src="/${iconFile}?${CACHE_VERSION}" alt="${threatType}" loading="lazy" decoding="async"
             style="transform:rotate(${rotationAngle}deg);width:100%;height:100%;"
             onerror="this.src='/shahed3.webp'">`;
      if (isShahed && marker.count && marker.count > 1) {
        html += `<div class="marker-count-badge">${marker.count}x</div>`;
      }
      html += '</div>';

      const icon = L.divIcon({
        className: 'threat-marker-icon',
        html,
        iconSize: [size, size],
        iconAnchor: [size / 2, size / 2],
      });

      const leafletMarker = L.marker([lat, lng], { icon });
      leafletMarker.on('mouseover', (e: L.LeafletMouseEvent) => {
        showTooltip(e.originalEvent, marker, threatType);
      });
      leafletMarker.on('mouseout', hideTooltip);
      group.addLayer(leafletMarker);

      // Render trajectory
      if (traj?.end) {
        const endLat = traj.end[0];
        const endLng = traj.end[1];
        if (!isNaN(endLat) && !isNaN(endLng) &&
            (Math.abs(lat - endLat) >= 0.01 || Math.abs(lng - endLng) >= 0.01)) {
          const lineColor = traj.predicted ? 'rgba(251,191,36,0.85)' : 'rgba(255,255,255,0.8)';
          const polyline = L.polyline([[lat, lng], [endLat, endLng]], {
            color: lineColor,
            weight: 2,
            dashArray: '6,4',
            lineCap: 'round',
            opacity: 0.85,
          });
          trajGroup.addLayer(polyline);

          // Arrow at target
          const angle = Math.atan2(endLng - lng, endLat - lat) * (180 / Math.PI);
          const arrowIcon = L.divIcon({
            className: 'trajectory-arrow-icon',
            html: `<div class="trajectory-target-arrow" style="color:${lineColor};transform:rotate(${angle + 90}deg);">&#8744;</div>`,
            iconSize: [18, 18],
            iconAnchor: [9, 9],
          });
          trajGroup.addLayer(L.marker([endLat, endLng], { icon: arrowIcon, interactive: false }));
        }
      }
    });
  }, []);

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

    trajs.forEach((traj) => {
      if (!traj.actual_path || traj.actual_path.length < 2) return;

      const latLngs: L.LatLngExpression[] = traj.actual_path.map(([lat, lng]) => [lat, lng]);
      const polyline = L.polyline(latLngs, {
        color: '#ff6600',
        weight: 3,
        lineCap: 'round',
        lineJoin: 'round',
        opacity: 0.8,
      });
      group.addLayer(polyline);

      // Predicted path
      if (traj.predicted_path && traj.predicted_path.length >= 2) {
        const predLatLngs: L.LatLngExpression[] = traj.predicted_path.map(([lat, lng]) => [lat, lng]);
        const predLine = L.polyline(predLatLngs, {
          color: '#ff6600',
          weight: 2,
          dashArray: '10,6',
          opacity: 0.5,
        });
        group.addLayer(predLine);
      }
    });
  }, []);

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
  try {
    // Load MapLibre GL JS and Leaflet plugin from CDN
    await loadScript('https://unpkg.com/maplibre-gl/dist/maplibre-gl.js');
    await loadScript('https://unpkg.com/@maplibre/maplibre-gl-leaflet/leaflet-maplibre-gl.js');

    // Add MapLibre CSS
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://unpkg.com/maplibre-gl/dist/maplibre-gl.css';
    document.head.appendChild(link);

    const response = await fetch('https://tiles.openfreemap.org/styles/dark');
    const style = await response.json();

    // Modify text fields to show Ukrainian names
    style.layers.forEach((layer: Record<string, unknown>) => {
      const layout = layer.layout as Record<string, unknown> | undefined;
      if (layout?.['text-field']) {
        layout['text-field'] = ['coalesce', ['get', 'name:uk'], ['get', 'name']];
      }
      if (isMobile && layout?.['symbol-spacing']) {
        layout['symbol-spacing'] = ((layout['symbol-spacing'] as number) || 250) * 1.5;
      }
    });

    // Use the globally-available L.maplibreGL from the CDN scripts
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const LWithPlugin = L as any;
    if (LWithPlugin.maplibreGL) {
      LWithPlugin.maplibreGL({ style, attribution: '' }).addTo(map);
    } else {
      throw new Error('maplibreGL plugin not available after loading');
    }
  } catch (e) {
    console.warn('Failed to load MapLibre, falling back to OSM tiles:', e);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '',
      maxZoom: 19,
    }).addTo(map);
  }
}

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${src}"]`);
    if (existing) { resolve(); return; }
    const script = document.createElement('script');
    script.src = src;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error(`Failed to load ${src}`));
    document.head.appendChild(script);
  });
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
    fadeOpacity = 1 - (zoom - SVG_FADE_START_ZOOM) / (SVG_FADE_END_ZOOM - SVG_FADE_START_ZOOM);
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

function showTooltip(event: MouseEvent, marker: Marker, threatType: string) {
  hideTooltip();
  const tooltip = document.createElement('div');
  tooltip.className = 'marker-tooltip';
  tooltip.id = 'active-tooltip';

  const typeName = THREAT_NAMES[threatType] || threatType;
  tooltip.innerHTML = `
    <div class="tooltip-type">${typeName}</div>
    <div class="tooltip-place">${marker.place || 'Невідомо'}</div>
    ${marker.date ? `<div class="tooltip-time">${marker.date}</div>` : ''}
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

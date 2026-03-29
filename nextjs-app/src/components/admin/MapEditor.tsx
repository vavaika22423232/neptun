'use client';

import { useEffect, useRef, useCallback } from 'react';
import L from 'leaflet';

interface Marker {
  id: string;
  lat: number;
  lng: number;
  threat_type: string;
  place: string;
  text: string;
  date: string;
  manual?: boolean;
}

interface MapEditorProps {
  markers: Marker[];
  onAddMarker: (lat: number, lng: number) => void;
  onMoveMarker: (id: string, lat: number, lng: number) => void;
  onSelectMarker: (marker: Marker) => void;
}

const THREAT_COLORS: Record<string, string> = {
  shahed: '#36e4ff',
  raketa: '#ff5252',
  avia: '#ffab40',
  pvo: '#5ef5c4',
  vibuh: '#ff5252',
  alarm: '#ff5252',
  alarm_cancel: '#5ef5c4',
  obstril: '#ff5252',
  fpv: '#b388ff',
  pusk: '#ff5252',
  kab: '#ffab40',
  rszv: '#ff5252',
  rozved: '#b388ff',
  manual: '#36e4ff',
  default: '#8c9099',
};

export default function MapEditor({ markers, onAddMarker, onMoveMarker, onSelectMarker }: MapEditorProps) {
  const mapRef = useRef<L.Map | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);

  // Initialize map
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = L.map(containerRef.current, {
      center: [48.5, 32.0],
      zoom: 6,
      zoomControl: false,
      attributionControl: false,
    });

    L.tileLayer('https://tiles.openfreemap.org/styles/dark/{z}/{x}/{y}.png', {
      maxZoom: 18,
    }).addTo(map);

    L.control.zoom({ position: 'topright' }).addTo(map);

    const markersLayer = L.layerGroup().addTo(map);
    markersLayerRef.current = markersLayer;
    mapRef.current = map;

    // Click to add marker
    map.on('click', (e: L.LeafletMouseEvent) => {
      onAddMarker(e.latlng.lat, e.latlng.lng);
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Stable callback refs
  const onMoveRef = useRef(onMoveMarker);
  onMoveRef.current = onMoveMarker;
  const onSelectRef = useRef(onSelectMarker);
  onSelectRef.current = onSelectMarker;

  // Update markers on map
  const updateMarkers = useCallback(() => {
    const layer = markersLayerRef.current;
    if (!layer) return;
    layer.clearLayers();

    markers.forEach(m => {
      const color = THREAT_COLORS[m.threat_type] || THREAT_COLORS.default;
      const circle = L.circleMarker([m.lat, m.lng], {
        radius: 7,
        color,
        fillColor: color,
        fillOpacity: 0.6,
        weight: 2,
      });

      circle.bindTooltip(`${m.threat_type}: ${m.place || 'N/A'}`, { direction: 'top', offset: [0, -8] });

      if (m.manual) {
        // Draggable for manual markers — use a regular marker
        const draggable = L.marker([m.lat, m.lng], {
          draggable: true,
          icon: L.divIcon({
            className: 'admin-marker-icon',
            html: `<div style="width:14px;height:14px;border-radius:50%;background:${color};border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.5);"></div>`,
            iconSize: [14, 14],
            iconAnchor: [7, 7],
          }),
        });
        draggable.bindTooltip(`${m.threat_type}: ${m.place || 'N/A'}`, { direction: 'top', offset: [0, -8] });
        draggable.on('dragend', () => {
          const pos = draggable.getLatLng();
          onMoveRef.current(m.id, pos.lat, pos.lng);
        });
        draggable.on('click', () => onSelectRef.current(m));
        draggable.addTo(layer);
      } else {
        circle.on('click', (e) => {
          L.DomEvent.stopPropagation(e);
          onSelectRef.current(m);
        });
        circle.addTo(layer);
      }
    });
  }, [markers]);

  useEffect(() => {
    updateMarkers();
  }, [updateMarkers]);

  return (
    <div className="bg-[#1a2030] rounded-2xl border border-white/5 overflow-hidden">
      <div className="px-4 py-2.5 border-b border-white/5 flex items-center justify-between">
        <h3 className="text-sm font-medium text-white/70">
          <span className="material-icons text-[16px] mr-1.5 align-middle text-[#36e4ff]">map</span>
          Карта міток
        </h3>
        <span className="text-[11px] text-white/30">Клік на карті — додати мітку · Перетягування — перемістити</span>
      </div>
      <div ref={containerRef} className="h-[400px] w-full" style={{ background: 'var(--surface-dim)' }} />
    </div>
  );
}

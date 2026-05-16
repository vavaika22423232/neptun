import type { Map as MapLibreMap } from 'maplibre-gl';

/** Не може збігатися з реальним `mid` з GeoJSON. */
export const MAP_NO_SELECTION = '__map_no_sel__';

/**
 * `icon-opacity` для шару `unclustered-point`: public threat markers are binary.
 * A marker is either present at full opacity or removed by server-side policy.
 */
export function buildSymbolIconOpacityExpr(selectedMid: string | null): unknown[] {
  const base: unknown[] = ['coalesce', ['get', 'opacity'], 1];
  if (!selectedMid) {
    return base;
  }
  return ['case', ['==', ['get', 'mid'], ['literal', selectedMid]], ['min', 1, ['+', base, 0.08]], base];
}

/**
 * `icon-size`: легке збільшення обраного маркера (множники, без додаткових шарів).
 */
export function buildSymbolIconSizeExpr(selectedMid: string | null, normIconPx: number): unknown[] {
  const sizeFrac: unknown[] = ['/', ['get', 'icon_px'], normIconPx];
  if (!selectedMid) {
    return sizeFrac;
  }
  const selectedMul: unknown[] = ['case', ['==', ['get', 'mid'], ['literal', selectedMid]], 1.14, 1];
  return ['*', sizeFrac, selectedMul];
}

/** Застосувати paint для фокусу (без зміни GeoJSON). */
export function applyThreatMarkerFocus(map: MapLibreMap, selectedMid: string | null, normIconPx: number): void {
  if (!map.getLayer('unclustered-point')) return;
  map.setPaintProperty('unclustered-point', 'icon-opacity', buildSymbolIconOpacityExpr(selectedMid) as never);
  map.setLayoutProperty('unclustered-point', 'icon-size', buildSymbolIconSizeExpr(selectedMid, normIconPx) as never);
}

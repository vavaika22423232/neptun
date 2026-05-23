/** Active air-alarm overlay on oblast / district map layers. */
export const MAP_ALARM_COLOR = '#630e0e';

/**
 * MapLibre paint/layout tokens — data-driven where possible (GPU),
 * no per-frame JS for marker styling.
 */
export const MAP_NIGHT = {
  /** App chrome / map letterbox */
  canvasBg: '#181f29',
  /** Oblast outline when zoomed in (zoom expression applied in layer) */
  oblastLine: 'rgba(148, 163, 184, 0.22)',
  /** Alarm fill — hex + окремий fill-opacity (пульс / fade). */
  alarmFillHex: MAP_ALARM_COLOR,
  alarmFillDistrictHex: MAP_ALARM_COLOR,
  /** Тьмяний фон для областей без тривоги, коли десь є активна тривога */
  calmDimFill: '#11171e',
} as const;

/** Світла підложка (Liberty): той самий прийом, але ледь помітний відтінок без «сірої маски». */
export const MAP_DAY = {
  calmDimFill: '#1e293b',
} as const;

/** Hybrid / raster “night” readability (MapLibre raster paint). */
export function rasterNightPaint(
  basemap: 'googleHybrid' | 'rasterVectorDark' | 'uaRasterBasemap',
): Record<string, unknown> {
  if (basemap === 'rasterVectorDark') {
    return {
      'raster-saturation': -0.35,
      'raster-contrast': 0.22,
      'raster-brightness-min': 0.08,
      'raster-brightness-max': 0.72,
      'raster-fade-duration': 0,
    };
  }
  if (basemap === 'uaRasterBasemap') {
    return {
      'raster-saturation': 0,
      'raster-contrast': 0,
      'raster-brightness-min': 0,
      'raster-brightness-max': 1,
      'raster-fade-duration': 0,
    };
  }
  return {
    'raster-saturation': -0.25,
    'raster-contrast': 0.12,
    'raster-brightness-min': 0,
    'raster-brightness-max': 1,
    'raster-fade-duration': 0,
  };
}

/** Zoom-based oblast context lines — no JS (interpolate on zoom). */
export const OBLAST_LINE_OPACITY: unknown[] = [
  'interpolate',
  ['linear'],
  ['zoom'],
  5,
  0,
  6.2,
  0.06,
  8,
  0.12,
  10.5,
  0.16,
  14,
  0.22,
];

export const OBLAST_LINE_WIDTH: unknown[] = [
  'interpolate',
  ['linear'],
  ['zoom'],
  5,
  0,
  7,
  0.35,
  10,
  0.75,
  14,
  1.15,
];

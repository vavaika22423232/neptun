export type MapMode = 'svg_only' | 'hybrid_fade' | 'tiles_primary';

export type MapModeState = {
  mode: MapMode;
  svgOpacity: number;
  tileOpacity: number;
  revealed: boolean;
};

export type MapModeInput = {
  zoom: number;
  isMobile: boolean;
  revealed: boolean;
  zoomAfterFit: number | null;
  revealZoomEps: number;
  desktopFadeStart: number;
  desktopFadeEnd: number;
  mobileFadeStart: number;
  mobileFadeEnd: number;
};

function clamp01(value: number): number {
  return Math.max(0, Math.min(1, value));
}

function fadeOpacity(zoom: number, start: number, end: number): number {
  if (zoom < start) return 1;
  if (zoom >= end) return 0;
  return clamp01(1 - ((zoom - start) / Math.max(0.001, end - start)));
}

export function computeMapModeState(input: MapModeInput): MapModeState {
  let revealed = input.revealed;
  if (input.isMobile && !revealed && input.zoomAfterFit != null) {
    revealed = Math.abs(input.zoom - input.zoomAfterFit) > input.revealZoomEps;
  }

  if (input.isMobile && !revealed) {
    return { mode: 'svg_only', svgOpacity: 1, tileOpacity: 0, revealed };
  }

  const start = input.isMobile ? input.mobileFadeStart : input.desktopFadeStart;
  const end = input.isMobile ? input.mobileFadeEnd : input.desktopFadeEnd;
  const svgOpacity = fadeOpacity(input.zoom, start, end);
  const tileOpacity = 1 - svgOpacity;
  const mode: MapMode = svgOpacity === 1
    ? 'svg_only'
    : svgOpacity === 0
      ? 'tiles_primary'
      : 'hybrid_fade';
  return { mode, svgOpacity, tileOpacity, revealed };
}

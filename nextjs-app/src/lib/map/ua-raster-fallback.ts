/**
 * Шаблони растрових тайлів підкладу (темний / світлий). ENV перевизначає закодований fallback.
 */
const UA_RASTER_TILES_DARK_B64 =
  'aHR0cHM6Ly9zdDEuZGVlcHN0YXRlbWFwLmxpdmUvc3R5bGVzL0RTVWtyYWluZVVrRGFyay97en0ve3h9L3t5fUAyeC53ZWJw';
const UA_RASTER_TILES_LIGHT_B64 =
  'aHR0cHM6Ly9zdDEuZGVlcHN0YXRlbWFwLmxpdmUvc3R5bGVzL0RTVWtyYWluZVVrL3t6fS97eH0ve3l9QDJ4LndlYnA=';

function decodeConfigB64(b64: string): string {
  try {
    return typeof atob === 'function' ? atob(b64) : '';
  } catch {
    return '';
  }
}

export function resolveUaRasterTilesDarkTemplate(): string {
  const env = process.env.NEXT_PUBLIC_UA_RASTER_TILES_DARK;
  if (env && env.length > 0) return env;
  return decodeConfigB64(UA_RASTER_TILES_DARK_B64);
}

export function resolveUaRasterTilesLightTemplate(): string {
  const env = process.env.NEXT_PUBLIC_UA_RASTER_TILES_LIGHT;
  if (env && env.length > 0) return env;
  return decodeConfigB64(UA_RASTER_TILES_LIGHT_B64);
}

/** Origin для CSP і preconnect (`https://host`). */
export function resolveUaRasterTileOrigin(): string | undefined {
  const raw = resolveUaRasterTilesDarkTemplate();
  if (!raw) return undefined;
  try {
    const stub = raw.replace(/\{[^}]*\}/g, '0');
    return new URL(stub).origin;
  } catch {
    return undefined;
  }
}

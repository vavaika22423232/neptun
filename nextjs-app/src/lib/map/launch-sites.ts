/**
 * Known Russian/Crimean launch sites for Shahed drones and missiles.
 * Coordinates are approximate geographic centers of the known launch areas.
 * Used to render origin markers and trajectory arcs on the map.
 */

export interface LaunchSite {
  name: string;
  shortName: string;
  lat: number;
  lng: number;
  /** What types of threats are launched from here */
  threatKinds: ('shahed' | 'missile' | 'ballistic')[];
}

/** Normalized lookup keys — match what `origin` field from AI returns */
export const LAUNCH_SITES: Record<string, LaunchSite> = {
  // ── Crimea ────────────────────────────────────────────────────────────
  'крим':              { name: 'Крим', shortName: 'КРМ', lat: 45.15, lng: 33.99, threatKinds: ['shahed', 'missile'] },
  'криму':             { name: 'Крим', shortName: 'КРМ', lat: 45.15, lng: 33.99, threatKinds: ['shahed', 'missile'] },
  'чауда':             { name: 'Мис Чауда', shortName: 'ЧДА', lat: 44.88, lng: 35.27, threatKinds: ['shahed'] },
  'приморсько-ахтарськ': { name: 'Приморсько-Ахтарськ', shortName: 'ПАХ', lat: 46.05, lng: 38.18, threatKinds: ['shahed'] },
  'приморсько':        { name: 'Приморсько-Ахтарськ', shortName: 'ПАХ', lat: 46.05, lng: 38.18, threatKinds: ['shahed'] },
  // ── Black / Azov Sea ─────────────────────────────────────────────────
  'чорне море':        { name: 'Чорне море', shortName: 'ЧМ',  lat: 45.72, lng: 30.82, threatKinds: ['missile', 'shahed'] },
  'чорного моря':      { name: 'Чорне море', shortName: 'ЧМ',  lat: 45.72, lng: 30.82, threatKinds: ['missile', 'shahed'] },
  'азовське море':     { name: 'Азовське море', shortName: 'АМ', lat: 46.2, lng: 36.5,  threatKinds: ['missile'] },
  // ── Russia border regions ─────────────────────────────────────────────
  'курськ':            { name: 'Курськ', shortName: 'КУР', lat: 51.73, lng: 36.19, threatKinds: ['shahed', 'missile', 'ballistic'] },
  'бєлгород':          { name: 'Бєлгород', shortName: 'БЛГ', lat: 50.59, lng: 36.59, threatKinds: ['ballistic', 'missile'] },
  'белгород':          { name: 'Бєлгород', shortName: 'БЛГ', lat: 50.59, lng: 36.59, threatKinds: ['ballistic', 'missile'] },
  'воронеж':           { name: 'Воронеж', shortName: 'ВРЖ', lat: 51.66, lng: 39.2,  threatKinds: ['missile', 'ballistic'] },
  'ростов':            { name: 'Ростов-на-Дону', shortName: 'РСТ', lat: 47.22, lng: 39.71, threatKinds: ['shahed', 'missile'] },
  'ростов-на-дону':    { name: 'Ростов-на-Дону', shortName: 'РСТ', lat: 47.22, lng: 39.71, threatKinds: ['shahed', 'missile'] },
  'краснодар':         { name: 'Краснодар', shortName: 'КРД', lat: 45.03, lng: 38.98, threatKinds: ['shahed'] },
  'єйськ':             { name: 'Єйськ', shortName: 'ЄЙС', lat: 46.7, lng: 38.27, threatKinds: ['shahed'] },
  'єйська':            { name: 'Єйськ', shortName: 'ЄЙС', lat: 46.7, lng: 38.27, threatKinds: ['shahed'] },
  'орел':              { name: 'Орел', shortName: 'ОРЛ', lat: 52.97, lng: 36.07, threatKinds: ['shahed'] },
  'орла':              { name: 'Орел', shortName: 'ОРЛ', lat: 52.97, lng: 36.07, threatKinds: ['shahed'] },
  'луганськ':          { name: 'Луганськ (ТОТ)', shortName: 'ЛГН', lat: 48.57, lng: 39.30, threatKinds: ['ballistic', 'missile'] },
  'донецьк':           { name: 'Донецьк (ТОТ)', shortName: 'ДНЦ', lat: 48.00, lng: 37.80, threatKinds: ['ballistic', 'missile'] },
};

/**
 * Resolve an origin string (from AI/worker) to a known launch site.
 * Case-insensitive, partial match on known keys.
 */
export function resolveLaunchSite(origin: string | null | undefined): LaunchSite | null {
  if (!origin) return null;
  const normalized = origin.toLowerCase().trim();
  // Exact match
  if (LAUNCH_SITES[normalized]) return LAUNCH_SITES[normalized];
  // Partial match — find a key that is contained in the origin text
  for (const [key, site] of Object.entries(LAUNCH_SITES)) {
    if (normalized.includes(key) || key.includes(normalized)) {
      return site;
    }
  }
  return null;
}

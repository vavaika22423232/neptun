export type ShelterType = 'shelter' | 'bunker' | 'metro' | 'transit';

export type Shelter = {
  name: string;
  type: ShelterType;
  latitude: number;
  longitude: number;
  distanceM: number;
};

type OverpassElement = {
  lat?: number;
  lon?: number;
  center?: { lat?: number; lon?: number };
  tags?: Record<string, string>;
};

function haversineM(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const r = 6371000;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLon / 2) ** 2;
  return r * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function shelterTypeName(tags: Record<string, string>): string {
  if (tags.railway === 'subway_entrance') return 'Вхід в метро';
  if (tags.bunker_type) return 'Бомбосховище';
  if (tags.building === 'bunker') return 'Бункер';
  if (tags.shelter_type === 'public_transport') return 'Зупинка';
  return 'Укриття';
}

function shelterType(tags: Record<string, string>): ShelterType {
  if (tags.railway === 'subway_entrance' || tags.station === 'subway') return 'metro';
  if (tags.bunker_type || tags.building === 'bunker') return 'bunker';
  if (tags.shelter_type === 'public_transport') return 'transit';
  return 'shelter';
}

function parseElements(elements: OverpassElement[], originLat: number, originLon: number): Shelter[] {
  const out: Shelter[] = [];
  for (const e of elements) {
    const lat = e.lat ?? e.center?.lat;
    const lon = e.lon ?? e.center?.lon;
    if (lat == null || lon == null || lat === 0 || lon === 0) continue;
    const tags = e.tags ?? {};
    const name = tags.name?.trim() || shelterTypeName(tags);
    out.push({
      name,
      type: shelterType(tags),
      latitude: lat,
      longitude: lon,
      distanceM: haversineM(originLat, originLon, lat, lon),
    });
  }
  return out;
}

async function overpassPost(query: string, timeoutMs: number): Promise<OverpassElement[]> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch('https://overpass-api.de/api/interpreter', {
      method: 'POST',
      body: query,
      signal: controller.signal,
    });
    if (!response.ok) throw new Error('Помилка завантаження укриттів');
    const data = (await response.json()) as { elements?: OverpassElement[] };
    return data.elements ?? [];
  } finally {
    clearTimeout(timer);
  }
}

export async function fetchNearbyShelters(lat: number, lon: number): Promise<Shelter[]> {
  const query = `
[out:json][timeout:25];
(
  node["amenity"="shelter"](around:2000,${lat},${lon});
  node["bunker_type"](around:2000,${lat},${lon});
  node["building"="bunker"](around:2000,${lat},${lon});
  way["amenity"="shelter"](around:2000,${lat},${lon});
  way["bunker_type"](around:2000,${lat},${lon});
  way["building"="bunker"](around:2000,${lat},${lon});
  node["shelter_type"="public_transport"](around:1000,${lat},${lon});
  node["railway"="subway_entrance"](around:1500,${lat},${lon});
  node["public_transport"="station"]["subway"="yes"](around:1500,${lat},${lon});
);
out body center;
`;
  const shelters = parseElements(await overpassPost(query, 30000), lat, lon);

  try {
    const metroQuery = `
[out:json][timeout:15];
(
  node["railway"="station"]["station"="subway"](around:3000,${lat},${lon});
  node["railway"="subway_entrance"](around:2000,${lat},${lon});
);
out body;
`;
    const metro = parseElements(await overpassPost(metroQuery, 15000), lat, lon).map((s) => ({
      ...s,
      name: s.name === 'Укриття' ? 'Станція метро' : s.name,
      type: 'metro' as const,
    }));
    shelters.push(...metro);
  } catch {
    /* metro optional */
  }

  shelters.sort((a, b) => a.distanceM - b.distanceM);
  return shelters.slice(0, 20);
}

export function formatShelterDistance(meters: number): string {
  if (meters < 1000) return `${Math.round(meters)} м`;
  return `${(meters / 1000).toFixed(1)} км`;
}

export function shelterMapsDirectionsUrl(
  originLat: number,
  originLon: number,
  destLat: number,
  destLon: number,
): string {
  return `https://www.google.com/maps/dir/?api=1&origin=${originLat},${originLon}&destination=${destLat},${destLon}&travelmode=walking`;
}

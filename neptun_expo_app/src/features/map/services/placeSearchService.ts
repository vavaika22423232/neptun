import { absoluteUrl } from '../../../config/api';

export type PlaceTypeCode = 'city' | 'town' | 'village' | 'suburb' | 'other';

export type PlaceSearchResult = {
  id: string;
  name: string;
  nameUk: string;
  subtitle: string;
  placeType: PlaceTypeCode;
  lat: number;
  lng: number;
  oblastHasc?: string;
  population?: number;
  slug?: string;
  regionSlug?: string;
  source: 'gazetteer' | 'geojson';
};

export function flyToZoomForPlaceType(placeType: PlaceTypeCode): number {
  switch (placeType) {
    case 'city':
      return 12;
    case 'town':
    case 'suburb':
      return 13;
    case 'village':
      return 13.5;
    default:
      return 12.5;
  }
}

export async function searchPlaces(query: string, limit = 8): Promise<PlaceSearchResult[]> {
  const q = query.trim();
  if (q.length < 2) return [];
  const url = absoluteUrl(`/api/places/search?q=${encodeURIComponent(q)}&limit=${limit}`);
  const response = await fetch(url);
  if (!response.ok) {
    const body = await response.json().catch(() => ({} as { error?: string }));
    throw new Error(body.error || 'Пошук тимчасово недоступний');
  }
  const data = (await response.json()) as { results?: PlaceSearchResult[] };
  return data.results ?? [];
}

export async function popularPlaces(limit = 8): Promise<PlaceSearchResult[]> {
  const url = absoluteUrl(`/api/places/search?popular=1&limit=${limit}`);
  const response = await fetch(url);
  if (!response.ok) return [];
  const data = (await response.json()) as { results?: PlaceSearchResult[] };
  return data.results ?? [];
}

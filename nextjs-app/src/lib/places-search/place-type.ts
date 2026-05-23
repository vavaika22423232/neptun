import type { PlaceTypeCode } from '@/lib/places-search/types';

const UA_TYPE_MAP: Record<string, PlaceTypeCode> = {
  місто: 'city',
  село: 'village',
  селище: 'town',
  'селище міського типу': 'town',
};

const GEOJSON_TYPE_MAP: Record<string, PlaceTypeCode> = {
  city: 'city',
  town: 'town',
  village: 'village',
  suburb: 'suburb',
};

export function placeTypeFromGazetteer(raw: string | null | undefined): PlaceTypeCode {
  if (!raw) return 'other';
  return UA_TYPE_MAP[raw.trim().toLowerCase()] ?? 'other';
}

export function placeTypeFromGeojson(code: string | null | undefined): PlaceTypeCode {
  if (!code) return 'other';
  return GEOJSON_TYPE_MAP[code] ?? 'other';
}

export function placeTypeLabelUk(t: PlaceTypeCode): string {
  switch (t) {
    case 'city':
      return 'Місто';
    case 'town':
      return 'СМТ / містечко';
    case 'village':
      return 'Село';
    case 'suburb':
      return 'Район';
    default:
      return 'Населений пункт';
  }
}

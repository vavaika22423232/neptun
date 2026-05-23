export type PlaceTypeCode = 'city' | 'town' | 'village' | 'suburb' | 'other';

export interface PlaceSearchResult {
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
}

export interface PlaceSearchResponse {
  results: PlaceSearchResult[];
}

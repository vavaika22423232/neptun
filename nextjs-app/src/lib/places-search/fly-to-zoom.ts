import type { PlaceTypeCode } from '@/lib/places-search/types';

/** Map zoom when user picks a place from search (closer for smaller settlements). */
export function flyToZoomForPlaceType(placeType: PlaceTypeCode): number {
  switch (placeType) {
    case 'city':
      return 12;
    case 'town':
      return 13;
    case 'village':
      return 13.5;
    case 'suburb':
      return 13;
    default:
      return 12.5;
  }
}

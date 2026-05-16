import { isLngLatInsideUkraineAdm0 } from '@/lib/map/ukraine-adm0-boundary';

/**
 * Викликати **після** `isPlausibleThreatCoordinate`: прямокутний bbox охоплює Молдову та інших сусідів,
 * але публічна карта має показувати лише територію UA (ADM0) або прилегле море/Азовський сектор.
 */
export function isPublicMapThreatGeography(lat: number, lng: number): boolean {
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return false;
  if (isLngLatInsideUkraineAdm0(lng, lat)) return true;

  return isAdjacentUaMaritimeThreatGeography(lat, lng);
}

export function isAdjacentUaMaritimeThreatGeography(lat: number, lng: number): boolean {
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return false;
  /** Західне Чорне моря + море поблизу узбережжя UA без далекого Кубані (Tuapse lng ~39e). Зміїний ~30.75°E. */
  return lat >= 43.82 && lat <= 47.95 && lng >= 30.38 && lng <= 37.92;
}

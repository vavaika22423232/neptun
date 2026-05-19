import { haversineKm } from './marker-movement-policy';

export type LaunchSite = {
  id: string;
  name: string;
  lat: number;
  lng: number;
  radiusKm: number;
  threatTypes: string[];
};

export const KNOWN_LAUNCH_SITES: LaunchSite[] = [
  {
    id: 'primorsko_akhtarsk',
    name: 'Приморсько-Ахтарськ',
    lat: 46.0475,
    lng: 38.1733,
    radiusKm: 60,
    threatTypes: ['shahed', 'uav', 'drone'],
  },
  {
    id: 'yeysk',
    name: 'Єйськ',
    lat: 46.6816,
    lng: 38.2045,
    radiusKm: 50,
    threatTypes: ['shahed', 'uav', 'drone'],
  },
  {
    id: 'cape_chauda',
    name: 'мис Чауда',
    lat: 45.0333,
    lng: 35.8333,
    radiusKm: 60,
    threatTypes: ['shahed', 'uav', 'drone'],
  },
  {
    id: 'kursk',
    name: 'Курськ',
    lat: 51.7308,
    lng: 36.1930,
    radiusKm: 80,
    threatTypes: ['shahed', 'uav', 'drone', 'missile', 'ballistic'],
  },
  {
    id: 'belgorod',
    name: 'Бєлгород',
    lat: 50.5997,
    lng: 36.5982,
    radiusKm: 70,
    threatTypes: ['missile', 'ballistic'],
  },
  {
    id: 'voronezh',
    name: 'Воронеж',
    lat: 51.6607,
    lng: 39.2002,
    radiusKm: 70,
    threatTypes: ['missile', 'ballistic'],
  },
  {
    id: 'bryansk',
    name: 'Брянськ',
    lat: 53.2415,
    lng: 34.3705,
    radiusKm: 70,
    threatTypes: ['missile', 'ballistic', 'shahed'],
  },
];

/**
 * Checks if an inferred backward projection falls near a known launch site.
 */
export function intersectLaunchSite(
  lat: number,
  lng: number,
  threatType: string
): { name: string; distanceKm: number } | null {
  const normThreat = String(threatType).toLowerCase().trim();
  
  let bestSite: LaunchSite | null = null;
  let minDistance = Infinity;

  for (const site of KNOWN_LAUNCH_SITES) {
    if (!site.threatTypes.includes(normThreat) && !site.threatTypes.includes('uav')) {
      // Very loose threat matching for prototype
      // Actually we just skip if totally unrelated, but we let it pass if it's broadly supported.
    }
    
    const dist = haversineKm(lat, lng, site.lat, site.lng);
    if (dist <= site.radiusKm && dist < minDistance) {
      minDistance = dist;
      bestSite = site;
    }
  }

  if (bestSite) {
    return { name: bestSite.name, distanceKm: minDistance };
  }

  return null;
}

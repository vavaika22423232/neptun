import type { Marker } from '@/types';
import { isLngLatInsideUkraineAdm0 } from '@/lib/map/ukraine-adm0-boundary';
import { resolveThreatBearingDeg } from '@/lib/threat-bearing';

/** Оголошена кількість у тексті — верхня межа для попапу (захист від сміття в парсері). */
export const SWARM_DECLARED_CAP = 199;

/** Публічна карта показує один трек/пін на одну групу, навіть якщо у тексті count > 1. */
export const SWARM_VISUAL_MAX = 1;

const R_MIN_KM = 14;
const R_MAX_KM = 52;
const MIN_PAIR_SEP_KM = 12;
const PLACE_ATTEMPTS = 56;

function hashSeed(str: string): number {
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

/** Mulberry32 — стабільний PRNG від seed. */
function mulberry32(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function haversineKm(aLat: number, aLng: number, bLat: number, bLng: number): number {
  const R = 6371;
  const dLat = ((bLat - aLat) * Math.PI) / 180;
  const dLng = ((bLng - aLng) * Math.PI) / 180;
  const lat1 = (aLat * Math.PI) / 180;
  const lat2 = (bLat * Math.PI) / 180;
  const h =
    Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.min(1, Math.sqrt(h)));
}

function kmOffsetFromCenter(lat: number, lng: number, angleRad: number, rKm: number): [number, number] {
  const latRad = (lat * Math.PI) / 180;
  const kmDegLat = 1 / 111.32;
  const cosLat = Math.cos(latRad);
  const kmDegLng = cosLat > 0.05 ? 1 / (111.32 * cosLat) : kmDegLat;
  const dLat = Math.cos(angleRad) * rKm * kmDegLat;
  const dLng = Math.sin(angleRad) * rKm * kmDegLng;
  return [lat + dLat, lng + dLng];
}

/**
 * Будує visualN позицій: перша — точні координати інжесту; решта — випадково в кільці,
 * з мінімальною відстанню між усіма парами (щоб не зліпалися в одну купу).
 */
function buildSwarmPositions(
  centerLat: number,
  centerLng: number,
  visualN: number,
  seedStr: string,
  bearingDeg?: number | null,
): [number, number][] {
  const positions: [number, number][] = [[centerLat, centerLng]];
  if (visualN <= 1) return positions;

  // Если есть курс, строим "друг за другом" (sequential)
  if (bearingDeg != null) {
    const angleRad = (bearingDeg * Math.PI) / 180;
    // Офсет назад по курсу (летим "хвостом")
    const backAngle = angleRad + Math.PI;
    const spacingKm = 8.5; // Расстояние между шахедами в цепочке
    
    for (let i = 1; i < visualN; i++) {
      const [plat, plng] = kmOffsetFromCenter(centerLat, centerLng, backAngle, i * spacingKm);
      // Если точка за пределами Украины, пробуем небольшой рандомный сдвиг
      if (isLngLatInsideUkraineAdm0(plng, plat)) {
        positions.push([plat, plng]);
      } else {
        // Fallback к случайному расположению если хвост уходит за границу
        break; 
      }
    }
    if (positions.length === visualN) return positions;
  }

  // Fallback to original random swarm if bearing is missing or tail is out of bounds
  const golden = Math.PI * (3 - Math.sqrt(5));

  for (let i = 1; i < visualN; i++) {
    let chosen: [number, number] | null = null;

    for (let attempt = 0; attempt < PLACE_ATTEMPTS; attempt++) {
      const rand = mulberry32(hashSeed(`${seedStr}|sat|${i}|${attempt}`));
      const angle = rand() * 2 * Math.PI;
      const r = R_MIN_KM + rand() * (R_MAX_KM - R_MIN_KM);
      const [plat, plng] = kmOffsetFromCenter(centerLat, centerLng, angle, r);

      let ok = isLngLatInsideUkraineAdm0(plng, plat);
      if (!ok) continue;

      for (const [qlat, qlng] of positions) {
        if (haversineKm(plat, plng, qlat, qlng) < MIN_PAIR_SEP_KM) {
          ok = false;
          break;
        }
      }
      if (ok) {
        chosen = [plat, plng];
        break;
      }
    }

    if (!chosen) {
      const rand = mulberry32(hashSeed(`${seedStr}|fallback|${i}`));
      const t = i + rand();
      const angle = t * golden + rand() * 0.9;
      const r = R_MIN_KM + ((i / Math.max(1, visualN - 1)) * (R_MAX_KM - R_MIN_KM)) + rand() * 8;
      let fb = kmOffsetFromCenter(centerLat, centerLng, angle, Math.min(R_MAX_KM + 12, r));
      if (!isLngLatInsideUkraineAdm0(fb[1], fb[0])) {
        let rCur = Math.min(R_MAX_KM + 12, r);
        for (let step = 0; step < 28 && rCur >= 2; step++) {
          rCur *= 0.72;
          fb = kmOffsetFromCenter(centerLat, centerLng, angle, rCur);
          if (isLngLatInsideUkraineAdm0(fb[1], fb[0])) break;
        }
      }
      chosen = fb;
      positions.push(chosen);
      continue;
    }

    positions.push(chosen);
  }

  return positions;
}

function swarmEligibleThreat(marker: Marker): boolean {
  const tt = String(marker.threat_type || marker.type || '').toLowerCase();
  if (
    tt === 'shahed' ||
    tt === 'drone' ||
    tt === 'uav' ||
    tt === 'default' ||
    tt === 'fpv' ||
    tt.includes('shahed') ||
    tt.includes('drone')
  ) {
    return true;
  }
  return false;
}

/**
 * Дублює один маркер у кілька видимих пінів, коли в тексті вказано кількість (наприклад «до 20 шахедів»).
 * За замовчуванням SWARM_VISUAL_MAX = 1: на публічній карті один пін на запис, без «розводу» рою.
 */
export function expandMarkersForSwarmDisplay(markers: Marker[]): Marker[] {
  if (SWARM_VISUAL_MAX <= 1) {
    return markers;
  }

  const out: Marker[] = [];

  for (const m of markers) {
    const raw = Number(m.count);
    if (!Number.isFinite(raw) || raw < 2 || !swarmEligibleThreat(m)) {
      out.push(m);
      continue;
    }

    const declared = Math.min(SWARM_DECLARED_CAP, Math.max(2, Math.floor(raw)));
    const visualN = Math.min(SWARM_VISUAL_MAX, declared);
    const seedBase = String(m.track_id || m.id || `${m.lat},${m.lng}`);
    const bearing = resolveThreatBearingDeg(m);
    const coords = buildSwarmPositions(m.lat, m.lng, visualN, seedBase, bearing);

    for (let i = 0; i < visualN; i++) {
      const [plat, plng] = coords[i]!;
      if (i === 0) {
        out.push({
          ...m,
          lat: plat,
          lng: plng,
          swarm_unit_index: 1,
          swarm_total: visualN,
        });
        continue;
      }

      const baseId = String(m.id ?? m.track_id ?? 'swarm').slice(0, 96);
      out.push({
        ...m,
        lat: plat,
        lng: plng,
        id: `${baseId}_swarm_${i}`,
        track_id: undefined,
        swarm_unit_index: i + 1,
        swarm_total: visualN,
        count: 1,
        display_class: 'corroborated_point',
        show_precise_pin: true,
        display_uncertainty_km: 0,
      });
    }
  }

  return out;
}

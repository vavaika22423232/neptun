import { findOblastHascForRegionLabel } from '@/lib/map/alarm-hasc-filter';
import type { OblastFeatureCollection } from '@/lib/map/alarm-hasc-filter';

/** GADM HASC_1 aligned with `TEXT_TO_HASC` in ukraine-oblast-validate.ts */
const OBLAST_LABEL_TO_HASC: Record<string, string> = {
  'Київська область': 'UA.KV',
  'м. Київ': 'UA.KC',
  'Київ': 'UA.KC',
  'Харківська область': 'UA.KK',
  'Одеська область': 'UA.OD',
  'Дніпропетровська область': 'UA.DP',
  'Львівська область': 'UA.LV',
  'Донецька область': 'UA.DT',
  'Запорізька область': 'UA.ZP',
  'Вінницька область': 'UA.VI',
  'Житомирська область': 'UA.ZT',
  'Черкаська область': 'UA.CK',
  'Чернігівська область': 'UA.CH',
  'Полтавська область': 'UA.PL',
  'Сумська область': 'UA.SM',
  'Миколаївська область': 'UA.MY',
  'Херсонська область': 'UA.KS',
  'Кіровоградська область': 'UA.KH',
  'Хмельницька область': 'UA.KM',
  'Рівненська область': 'UA.RV',
  'Волинська область': 'UA.VO',
  'Тернопільська область': 'UA.TP',
  'Івано-Франківська область': 'UA.IF',
  'Закарпатська область': 'UA.ZK',
  'Чернівецька область': 'UA.CV',
  'Луганська область': 'UA.LH',
  'АР Крим': 'UA.KR',
  'Севастополь': 'UA.SC',
};

let cachedOblastFc: OblastFeatureCollection | null = null;

export function resolveOblastHasc(oblastLabel: string): string | undefined {
  const direct = OBLAST_LABEL_TO_HASC[oblastLabel.trim()];
  if (direct) return direct;
  if (cachedOblastFc) {
    return findOblastHascForRegionLabel(oblastLabel, cachedOblastFc) ?? undefined;
  }
  return undefined;
}

export function setOblastFcForHascLookup(fc: OblastFeatureCollection | null): void {
  cachedOblastFc = fc;
}

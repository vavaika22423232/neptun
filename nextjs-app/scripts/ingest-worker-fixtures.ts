/**
 * Чеклист полей для Python worker → `/api/ingest` (сервер уже умеет это использовать).
 * См. также `src/lib/api-schemas.ts`, `src/lib/ukraine-oblast-validate.ts`, `src/types/index.ts`.
 */
export const WORKER_INGEST_CHECKLIST = `
Обязательно для координат и карты
- lat, lng — числа в допустимом bbox (см. geo-bounds / worker geo_bounds.py)
- threat_type — shahed | missile | … (как у вас в парсере)

Сильно желательно (точность и коррелятор)
- track_id — стабильный ID одного трека; без него после ужесточения correlator возможны лишние отдельные маркеры
- resolved_oblast_hasc — GADM HASC_1, напр. UA.KK, UA.OD (лучше regex по region)
- region_key — один и тот же ключ для всех апдейтов одного события в одной области (гейт слияния)
- region и/или oblast — свободный текст; сервер сверяет с полигонами и при mismatch снапит на центроид области

Геокод и качество (ingest v2 meta — всё через passthrough, сервер и build-markers читают при наличии)
- placement_mode — point | approximate | predictive …
- confidence / confidence_0_100 (отсутствие не значит 100% — на карте порог minConfidence)
- geocode_tier — point | multi | ambiguous
- candidates_count — число кандидатов, если массив candidates не передаёте
- geocode_source / source_tier — необязательные метки происхождения координат
- candidates — запасные варианты геокода (отладка / будущий rerank)

Коридоры «з області A в B»
- Одна представительная точка (середина сегмента или центроид целевой области), не город-омоним без контекста
- placement_mode: approximate

Не полагаться только на place для области — микрорайоны дают ложные совпадения; область — из NER/resolved_oblast_hasc.
`.trim();

function newId(prefix: string): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

export type IngestFixture = {
  description: string;
  marker: Record<string, unknown>;
};

/**
 * Готовые сценарии для smoke POST /api/ingest (локально или на стенде).
 */
export function buildIngestFixtures(): Record<string, IngestFixture> {
  return {
    minimal_manual: {
      description: 'Ручная метка в bbox; region-валидация не трогает (manual: true).',
      marker: {
        id: newId('fx'),
        lat: 46.482,
        lng: 30.723,
        threat_type: 'shahed',
        manual: true,
        place: 'smoke-test',
        text: 'ingest smoke: minimal manual',
      },
    },

    region_text_mismatch_snap: {
      description:
        'region=Одеська область, координаты в районе Харкова → сервер должен сдвинуть на центроид Одесской области.',
      marker: {
        id: newId('fx'),
        track_id: newId('trk'),
        lat: 49.9935,
        lng: 36.2304,
        threat_type: 'shahed',
        manual: false,
        region: 'Одеська область',
        text: 'ingest smoke: region mismatch snap',
        confidence: 0.9,
        confidence_0_100: 90,
      },
    },

    resolved_hasc_mismatch_snap: {
      description:
        'resolved_oblast_hasc=UA.CH (Чернігівщина), точка в Одесской области → снап на центроид UA.CH.',
      marker: {
        id: newId('fx'),
        track_id: newId('trk'),
        lat: 46.482,
        lng: 30.723,
        threat_type: 'shahed',
        manual: false,
        resolved_oblast_hasc: 'UA.CH',
        region: 'Чернігівська область',
        text: 'ingest smoke: resolved_hasc mismatch',
        confidence: 0.85,
        confidence_0_100: 85,
      },
    },

    correlator_region_key_split: {
      description:
        'Два разных region_key — correlator не должен сливать (проверка вручную по двум POST подряд).',
      marker: {
        id: newId('fx'),
        track_id: newId('trk'),
        lat: 48.0,
        lng: 35.0,
        threat_type: 'shahed',
        manual: false,
        region_key: 'smoke_oblast_a',
        resolved_oblast_hasc: 'UA.DP',
        text: 'ingest smoke: region_key A',
        confidence: 0.8,
        confidence_0_100: 80,
      },
    },

    geocode_meta_multi: {
      description:
        'Несколько кандидатов геокода без массива candidates — публичная политика должна уйти в region_signal, пока нет corroboration.',
      marker: {
        id: newId('fx'),
        track_id: newId('trk'),
        lat: 48.45,
        lng: 35.05,
        threat_type: 'shahed',
        manual: false,
        placement_mode: 'point',
        geocode_tier: 'multi',
        candidates_count: 4,
        geocode_source: 'nominatim_smoke',
        region: 'Дніпропетровська область',
        text: 'ingest smoke: multi geocode meta',
        confidence: 0.82,
        confidence_0_100: 82,
      },
    },
  };
}

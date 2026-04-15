/**
 * Smoke POST /api/ingest с фикстурами из ingest-worker-fixtures.ts.
 *
 * Usage:
 *   INGEST_SECRET=your_secret npx tsx scripts/run-ingest-smoke.ts
 *   BASE_URL=http://127.0.0.1:3000 INGEST_SECRET=... npx tsx scripts/run-ingest-smoke.ts
 *
 * Options:
 *   --checklist   только вывести WORKER_INGEST_CHECKLIST и выйти
 *   --pair        после основных фикстур: два POST с одними lat/lng, разные region_key (не должны сливаться)
 */

import { buildIngestFixtures, WORKER_INGEST_CHECKLIST } from './ingest-worker-fixtures';

const baseUrl = process.env.BASE_URL || 'http://127.0.0.1:3000';
const secret = process.env.INGEST_SECRET || process.env.AUTH_SECRET || '';

function newId(prefix: string): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

async function postIngest(
  url: string,
  name: string,
  description: string,
  marker: Record<string, unknown>,
): Promise<void> {
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Auth-Secret': secret,
      },
      body: JSON.stringify({ marker }),
    });
    const body = await res.text();
    let parsed: unknown;
    try {
      parsed = JSON.parse(body);
    } catch {
      parsed = body;
    }
    console.log(`--- ${name} ---`);
    console.log(description);
    console.log(`HTTP ${res.status}`, parsed);
    console.log('');
  } catch (e) {
    console.error(`--- ${name} FAILED ---`, e);
  }
}

async function main() {
  const args = process.argv.slice(2);
  if (args.includes('--checklist')) {
    console.log(WORKER_INGEST_CHECKLIST);
    process.exit(0);
  }

  if (!secret) {
    console.error('[ingest-smoke] Set INGEST_SECRET or AUTH_SECRET (same as server).');
    process.exit(1);
  }

  const fixtures = buildIngestFixtures();
  const url = `${baseUrl.replace(/\/$/, '')}/api/ingest`;

  console.log(`[ingest-smoke] POST ${url}\n`);

  for (const [name, { description, marker }] of Object.entries(fixtures)) {
    await postIngest(url, name, description, marker);
  }

  if (args.includes('--pair')) {
    const lat = 48.0;
    const lng = 35.0;
    const base = {
      lat,
      lng,
      threat_type: 'shahed',
      manual: false,
      confidence: 0.75,
      confidence_0_100: 75,
      text: 'ingest smoke: region_key pair',
    };
    await postIngest(url, 'pair_A', 'Тот же квадрат, region_key A', {
      ...base,
      id: newId('pair'),
      track_id: newId('trk_pair_a'),
      region_key: 'smoke_pair_oblast_a',
      resolved_oblast_hasc: 'UA.DP',
    });
    await postIngest(url, 'pair_B', 'Тот же квадрат, region_key B — не сливать с A', {
      ...base,
      id: newId('pair'),
      track_id: newId('trk_pair_b'),
      region_key: 'smoke_pair_oblast_b',
      resolved_oblast_hasc: 'UA.ZP',
    });
    console.log(
      '[ingest-smoke] Проверьте /api/data: должны быть два маркера (разные region_key / resolved_oblast_hasc).',
    );
  } else {
    console.log('[ingest-smoke] Подсказка: добавьте --pair для пары POST с разными region_key на одних координатах.');
  }
}

main();

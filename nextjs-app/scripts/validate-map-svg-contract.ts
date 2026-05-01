import { readFile } from 'node:fs/promises';
import path from 'node:path';

type SvgStats = {
  ids: string[];
  pathCount: number;
  textCount: number;
};

const publicDir = path.join(process.cwd(), 'public');

function parseSvgStats(svg: string): SvgStats {
  const ids = [...svg.matchAll(/\sid="([^"]+)"/g)].map((m) => m[1]);
  return {
    ids,
    pathCount: (svg.match(/<path\b/g) ?? []).length,
    textCount: (svg.match(/<text\b/g) ?? []).length,
  };
}

function fail(messages: string[]): never {
  for (const msg of messages) {
    console.error(`map-svg-contract: ${msg}`);
  }
  process.exit(1);
}

async function main(): Promise<void> {
  const [states, districts, names] = await Promise.all([
    readFile(path.join(publicDir, 'ukraine_states.svg'), 'utf8'),
    readFile(path.join(publicDir, 'ukraine_districts_detailed.svg'), 'utf8'),
    readFile(path.join(publicDir, 'ukraine_names.svg'), 'utf8'),
  ]);

  const stateStats = parseSvgStats(states);
  const districtStats = parseSvgStats(districts);
  const nameStats = parseSvgStats(names);
  const errors: string[] = [];

  if (!states.includes('id="statesMap"')) errors.push('ukraine_states.svg must expose #statesMap');
  if (!districts.includes('id="districtsMap"')) errors.push('ukraine_districts_detailed.svg must expose #districtsMap');
  if (!names.includes('id="regionNames"')) errors.push('ukraine_names.svg must expose #regionNames');

  if (stateStats.pathCount < 25) errors.push(`states SVG has too few paths: ${stateStats.pathCount}`);
  if (districtStats.pathCount < 120) errors.push(`district SVG has too few district paths: ${districtStats.pathCount}`);
  if (nameStats.textCount < 25) errors.push(`names SVG has too few labels: ${nameStats.textCount}`);

  const stateAlarmIds = stateStats.ids.filter((id) => /^\d+$/.test(id));
  const districtAlarmIds = districtStats.ids.filter((id) => /^\d+$/.test(id));
  if (new Set(stateAlarmIds).size < 25) errors.push(`states SVG has too few numeric alarm ids: ${new Set(stateAlarmIds).size}`);
  if (new Set(districtAlarmIds).size < 120) {
    errors.push(`district SVG has too few numeric alarm ids: ${new Set(districtAlarmIds).size}`);
  }
  if (districts.includes('<line') || districts.includes('<polyline')) {
    errors.push('district SVG must not contain explicit line/polyline geometry');
  }

  if (errors.length) fail(errors);
  console.log(
    `map-svg-contract: ok (states=${new Set(stateAlarmIds).size}, districts=${new Set(districtAlarmIds).size}, names=${nameStats.textCount})`,
  );
}

void main().catch((error: unknown) => {
  console.error(error);
  process.exit(1);
});

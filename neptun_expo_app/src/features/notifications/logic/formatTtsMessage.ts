/** Mirrors Flutter `_formatTtsMessage` / `_getPlaceName` / `_detectThreatType`. */

function cleanRegionName(region: string): string {
  return region.trim();
}

function getPlaceName(location: string, region: string): string {
  const loc = location.trim();
  const reg = region.trim();
  if (
    loc.length >= 5 &&
    loc !== reg &&
    !loc.toLowerCase().includes('область')
  ) {
    let city = loc;
    if (loc.includes('(')) {
      city = loc.split('(')[0]?.trim() ?? loc;
    }
    if (city.length < 5) return cleanRegionName(reg);
    if (reg.includes('область')) {
      return `${city}, ${cleanRegionName(reg)}`;
    }
    return city;
  }
  return cleanRegionName(reg);
}

function detectThreatType(body: string, threatType: string): string {
  const text = `${body} ${threatType}`.toLowerCase();
  if (text.includes('балістичн') || text.includes('крилат')) return 'Ракетна небезпека';
  if (text.includes('ракет')) return 'Загроза ракетного удару';
  if (text.includes('каб')) return 'Загроза застосування КАБів';
  if (text.includes('бпла') || text.includes('дрон') || text.includes('шахед')) {
    return 'Загроза ударних БПЛА';
  }
  if (text.includes('вибух')) return 'Повідомляють про вибухи';
  if (text.includes('артилер')) return 'Артилерійська загроза';
  if (
    threatType.trim().length > 3 &&
    !threatType.toLowerCase().includes('повітряна тривога')
  ) {
    return threatType.trim();
  }
  return '';
}

export function formatTtsMessage(params: {
  region: string;
  location: string;
  threatType: string;
  alarmState: string;
  body: string;
}): string {
  const { region, location, threatType, alarmState, body } = params;
  const lowerBody = body.toLowerCase();
  const lowerThreat = threatType.toLowerCase();

  if (
    alarmState === 'ended' ||
    lowerBody.includes('відбій') ||
    lowerBody.includes('знято') ||
    lowerThreat.includes('відбій')
  ) {
    const place = getPlaceName(location, region);
    return `Відбій тривоги. ${place}.`;
  }

  const place = getPlaceName(location, region);
  const threat = detectThreatType(body, threatType);
  if (threat) return `Увага! ${place}. ${threat}.`;
  return `Увага! ${place}. Повітряна тривога.`;
}

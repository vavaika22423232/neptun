import type { BriefingData } from '../domain/briefingData';
import { briefingTotalThreats } from '../domain/briefingData';

function wordEnd(n: number, one: string, few: string, many: string): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 19) return many;
  if (mod10 === 1) return one;
  if (mod10 >= 2 && mod10 <= 4) return few;
  return many;
}

function alarmWord(n: number): string {
  if (n === 1) return 'тривога';
  if (n >= 2 && n <= 4) return 'тривоги';
  return 'тривог';
}

/** Flutter `BriefingService._buildBriefingTitle`. */
export function buildBriefingNotificationTitle(data: BriefingData): string {
  if (data.userRegionAlarmCount > 0 && data.userRegionName) {
    return `☀️ Ранок. Ваш регіон: ${data.userRegionAlarmCount} ${alarmWord(data.userRegionAlarmCount)}`;
  }
  if (data.totalAlarmsToday > 0) {
    return '☀️ Ранковий бріфінг';
  }
  return '☀️ Спокійна ніч';
}

/** Flutter `BriefingService._buildBriefingBody`. */
export function buildBriefingNotificationBody(data: BriefingData): string {
  const parts: string[] = [];
  const totalThreats = briefingTotalThreats(data);

  if (totalThreats > 0) {
    const threats: string[] = [];
    if (data.drones > 0) {
      threats.push(`${data.drones} дрон${wordEnd(data.drones, '', 'и', 'ів')}`);
    }
    if (data.missiles > 0) {
      threats.push(`${data.missiles} ракет${wordEnd(data.missiles, 'а', 'и', '')}`);
    }
    if (data.kab > 0) threats.push(`${data.kab} КАБ`);
    if (data.ballistic > 0) {
      threats.push(`${data.ballistic} балістик${wordEnd(data.ballistic, 'а', 'и', '')}`);
    }
    if (threats.length > 0) parts.push(`Загрози: ${threats.join(', ')}`);
  }

  if (data.totalAlarmsToday > 0) {
    parts.push(`Тривог по Україні: ${data.totalAlarmsToday}`);
  }

  if (parts.length === 0) {
    return 'Вночі все було тихо. Зараз спокійно.';
  }
  return parts.join(' · ');
}

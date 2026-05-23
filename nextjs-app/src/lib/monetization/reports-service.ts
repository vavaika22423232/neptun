/**
 * Rule-based daily/weekly reports from alert history + live alarms.
 */

import {
  aggregateRegionStatsDaily,
  getCurrentAlertsFromRedis,
  listAlertEvents,
} from './alert-history-store';

export type DailyReport = {
  date: string;
  regionId: string | null;
  regionName: string | null;
  totalAlerts: number;
  totalAlarmMinutes: number;
  threatTypes: Record<string, number>;
  activeHours: number[];
  highlights: string[];
  summaryText: string;
};

function cautiousSummary(parts: string[]): string {
  return `${parts.join(' ')} Інформація оновлюється; формулювання орієнтовні.`;
}

export async function buildDailyReport(regionId: string | null, date: string): Promise<DailyReport> {
  const from = `${date}T00:00:00.000Z`;
  const to = `${date}T23:59:59.999Z`;
  const events = await listAlertEvents({
    regionId: regionId ?? undefined,
    fromIso: from,
    toIso: to,
    limit: 500,
  });

  const threatTypes: Record<string, number> = {};
  const hours = new Set<number>();
  let totalMinutes = 0;

  for (const ev of events) {
    threatTypes[ev.type] = (threatTypes[ev.type] ?? 0) + 1;
    hours.add(new Date(ev.startedAt).getUTCHours());
    if (ev.endedAt) {
      totalMinutes += (Date.parse(ev.endedAt) - Date.parse(ev.startedAt)) / 60_000;
    }
  }

  const live = await getCurrentAlertsFromRedis();
  const activeNow = regionId
    ? live.filter((a) => a.regionId === regionId && a.activeAlerts?.length)
    : live.filter((a) => a.activeAlerts?.length);

  const highlights: string[] = [];
  if (events.length > 0) {
    highlights.push(`За наявними даними зафіксовано ${events.length} подій.`);
  }
  if (activeNow.length > 0) {
    highlights.push(`Зараз активні тривоги в ${activeNow.length} регіонах (орієнтовно).`);
  }

  const topTypes = Object.entries(threatTypes)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([t, n]) => `${t}: ${n}`)
    .join(', ');

  const summaryText = cautiousSummary([
    `Підсумок доби ${date}.`,
    events.length ? `Подій: ${events.length}.` : 'Подій за добу не зафіксовано.',
    topTypes ? `Типи: ${topTypes}.` : '',
    totalMinutes > 0 ? `Орієнтовна сумарна тривалість: ${Math.round(totalMinutes)} хв.` : '',
  ]);

  return {
    date,
    regionId,
    regionName: events[0]?.metadataJson?.regionName as string | null ?? null,
    totalAlerts: events.length,
    totalAlarmMinutes: Math.round(totalMinutes),
    threatTypes,
    activeHours: [...hours].sort((a, b) => a - b),
    highlights,
    summaryText,
  };
}

export async function buildWeeklyReport(regionId: string | null, weekStart: string): Promise<{
  weekStart: string;
  days: Awaited<ReturnType<typeof aggregateRegionStatsDaily>>;
  summaryText: string;
}> {
  const start = new Date(weekStart);
  const end = new Date(start);
  end.setDate(end.getDate() + 7);
  const days = regionId
    ? await aggregateRegionStatsDaily(regionId, start.toISOString(), end.toISOString())
    : [];

  const total = days.reduce((s, d) => s + d.totalAlerts, 0);
  const summaryText = cautiousSummary([
    `Тижневий підсумок з ${weekStart}.`,
    `Орієнтовно ${total} подій за 7 днів.`,
  ]);

  return { weekStart, days, summaryText };
}

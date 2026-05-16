import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { getRedis } from '@/lib/redis';
import { ADMIN_FEED_REDIS_KEY } from '@/lib/admin-feed-store';

export const dynamic = 'force-dynamic';

const EXPECTED_CHANNELS = [
  { slug: 'raketa_trevoga', name: 'Чому тривога | Радар', priority: 2 },
  { slug: 'war_monitor', name: 'monitor', priority: 2 },
  { slug: 'povitryanatrivogaaa', name: 'Повітряна тривога', priority: 1 },
  { slug: 'UkraineAlarmSignal', name: 'єТривога', priority: 1 },
  { slug: 'napramok', name: 'Напрямок ракет', priority: 2 },
  { slug: 'radarraketppo', name: 'Радар України', priority: 2 },
  { slug: 'ukrainsiypposhnik', name: 'Український ППОшник', priority: 2 },
  { slug: 'veselyy_pivden', name: 'Веселий Південь', priority: 3 },
  { slug: 'sectorv666', name: 'Сектор V', priority: 3 },
  { slug: 'odessaveter', name: 'Одесса Ветер', priority: 3 },
  { slug: 'korabely_media', name: 'Корабелы Миколаєва', priority: 3 },
  { slug: 'kpszsu', name: 'Повітряні Сили ЗСУ', priority: 1 },
  { slug: 'monikppy', name: 'Моніторинг ППО', priority: 2 },
  { slug: 'monitor1654', name: 'monitor 1654 | Харків', priority: 3 },
  { slug: 'operatyvnohlep', name: 'Оперативний Запоріжжя', priority: 3 },
  { slug: 'eyes_everywhere_ua', name: 'Очі Всюди Запоріжжя', priority: 3 },
  { slug: 'odessa_knight', name: 'Odesa Knight', priority: 3 },
  { slug: 'temporis_odesa', name: 'Temporis Odesa', priority: 3 },
  { slug: 'rozvidkaneba', name: 'Розвідка неба', priority: 2 },
  { slug: 'my_safety_Chernigiv', name: 'SafetyChe', priority: 3 },
  { slug: 'RadarChernihiv', name: 'Чернігівський Моніторинг', priority: 3 },
  { slug: 'taktychna_rukavuchkaa', name: 'Тактична Рукавичка/Ніжин', priority: 3 },
  { slug: 'ShahedChernihiv', name: 'єШахед Чернігів', priority: 3 },
  { slug: 'odessa_inform', name: 'ОДЕССА ИНФО LIVE', priority: 3 },
  { slug: 'horizon_of_war_Official', name: 'Горизонт Війни', priority: 3 },
  { slug: 'zahidnimonitoring', name: 'Західний Моніторинг', priority: 3 },
  { slug: 'sumygo', name: 'SUMY GO', priority: 3 },
  { slug: 'svessainfo', name: 'Свеса INFO', priority: 3 },
  { slug: 'Northern_Sich_ukr', name: 'Північний Сич', priority: 3 },
  { slug: 'radar_top_ua', name: 'Куди летить? | Радар', priority: 2 },
  { slug: 'kremen_sv', name: 'Кременчуцький Миколай', priority: 3 },
  { slug: 'cherkasy_nebbo', name: 'Черкаське небо', priority: 3 },
  { slug: 'pivden_varta', name: 'Вартові Півдня', priority: 3 },
  { slug: 'krolevetsnews', name: 'Новини Кролевця та Сумської області', priority: 3 },
  { slug: 'shovnebi', name: 'Шо там в небі', priority: 3 },
  { slug: 'JeniokSay', name: 'Женьок Вещає', priority: 3 },
  { slug: 'ReniHub', name: 'ReniHub | Одещина', priority: 3 },
  { slug: 'kudy_letyt', name: 'Ринда моніторить', priority: 2 },
  { slug: 'UkraineRadar_24_7', name: 'Де Ракета? | Радар України', priority: 2 },
  { slug: 'eRadarrua', name: 'єРадар', priority: 2 },
  { slug: 'pivden_FPV', name: 'Вартові Півдня Фпв/Молнія', priority: 3 },
  { slug: 'PhantomChe', name: 'Чернігівський Фантом', priority: 3 },
  { slug: 'kharkivlife', name: 'Харьков life | Харків', priority: 3 },
  { slug: 'newspn', name: 'ПН | Преступности.НЕТ', priority: 3 },
  { slug: 'tlknewsua', name: 'TLk News', priority: 3 },
  { slug: 'rdsprostir', name: 'RDS-prostir', priority: 3 },
  { slug: 'Karkivw', name: 'Харківський Простір Онлайн', priority: 3 },
  { slug: 'dnepr_nagladach', name: 'Наглядач Днепра', priority: 3 },
  { slug: 'Donetskiy_on', name: 'Донецький', priority: 3 },
] as const;

type FeedStatus =
  | 'processed'
  | 'skipped'
  | 'dropped'
  | 'deduped'
  | 'chain_update'
  | 'error'
  | 'retargeted';

interface FeedEntry {
  status?: FeedStatus;
  ts?: string;
  channel_name?: string;
  reason?: string;
  marker_id?: string;
}

interface ChannelHealth {
  slug: string;
  name: string;
  priority: number;
  seen: number;
  processed: number;
  mapMarkers: number;
  skipped: number;
  dropped: number;
  errors: number;
  lastSeenAt: string | null;
  lastStatus: FeedStatus | null;
  lastReason: string | null;
  topReasons: { reason: string; count: number }[];
  actionableDrops: number;
  conversionRate: number;
  health: 'active' | 'degraded' | 'quiet' | 'blocked' | 'silent';
}

function blankChannelHealth(channel: (typeof EXPECTED_CHANNELS)[number]): ChannelHealth {
  return {
    slug: channel.slug,
    name: channel.name,
    priority: channel.priority,
    seen: 0,
    processed: 0,
    mapMarkers: 0,
    skipped: 0,
    dropped: 0,
    errors: 0,
    lastSeenAt: null,
    lastStatus: null,
    lastReason: null,
    topReasons: [],
    actionableDrops: 0,
    conversionRate: 0,
    health: 'silent',
  };
}

function healthFor(row: ChannelHealth): ChannelHealth['health'] {
  if (row.seen === 0) return 'silent';
  if (row.mapMarkers > 0) {
    // "Active" only means useful if the channel contributes reliable map signal.
    // High hidden/no-geo/parser-empty rates need operator attention.
    if (row.actionableDrops >= 3 && row.actionableDrops >= row.mapMarkers && row.actionableDrops / row.seen >= 0.3) {
      return 'degraded';
    }
    return 'active';
  }
  if (row.dropped + row.skipped + row.errors > 0) return 'blocked';
  return 'quiet';
}

function toReason(value: unknown): string {
  if (typeof value !== 'string' || value.trim() === '') return 'unknown';
  return value.trim();
}

function isActionableDropReason(reason: string): boolean {
  return (
    reason.includes('hidden') ||
    reason.includes('no coordinates') ||
    reason.includes('both parsers empty') ||
    reason.includes('unknown type') ||
    reason.includes('no active alarm') ||
    reason.includes('implausible')
  );
}

/**
 * GET /api/admin/channel-health
 *
 * Builds a short-lived health snapshot from the worker admin feed. This is
 * intentionally derived from feed events rather than logs so the admin UI can
 * explain why a channel looks inactive: no events, parsed but dropped, or
 * processed into map markers.
 */
export async function GET() {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  const startedAt = Date.now();
  const rows = new Map<string, ChannelHealth>(
    EXPECTED_CHANNELS.map(channel => [channel.slug, blankChannelHealth(channel)]),
  );
  const reasons = new Map<string, Map<string, number>>();

  for (const channel of EXPECTED_CHANNELS) {
    reasons.set(channel.slug, new Map());
  }

  try {
    const redis = getRedis();
    const raw = await redis.lrange(ADMIN_FEED_REDIS_KEY, 0, 499);

    for (const item of raw) {
      let entry: FeedEntry;
      try {
        entry = JSON.parse(item) as FeedEntry;
      } catch {
        continue;
      }

      const channelName = entry.channel_name;
      if (!channelName || !rows.has(channelName)) continue;

      const row = rows.get(channelName);
      if (!row) continue;

      row.seen += 1;
      if (!row.lastSeenAt && entry.ts) row.lastSeenAt = entry.ts;
      if (!row.lastStatus && entry.status) row.lastStatus = entry.status;
      if (!row.lastReason && entry.reason) row.lastReason = entry.reason;

      if (entry.status === 'processed') row.processed += 1;
      if (entry.marker_id) row.mapMarkers += 1;
      if (entry.status === 'skipped') row.skipped += 1;
      if (entry.status === 'dropped') row.dropped += 1;
      if (entry.status === 'error') row.errors += 1;

      if (entry.status !== 'processed' || entry.reason) {
        const reason = toReason(entry.reason || entry.status);
        const channelReasons = reasons.get(channelName);
        channelReasons?.set(reason, (channelReasons.get(reason) || 0) + 1);
        if (isActionableDropReason(reason)) row.actionableDrops += 1;
      }
    }

    const channels = Array.from(rows.values()).map(row => {
      const channelReasons = reasons.get(row.slug) || new Map<string, number>();
      row.topReasons = Array.from(channelReasons.entries())
        .map(([reason, count]) => ({ reason, count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 3);
      row.conversionRate = row.seen > 0 ? Number((row.mapMarkers / row.seen).toFixed(3)) : 0;
      row.health = healthFor(row);
      return row;
    });

    const summary = channels.reduce(
      (acc, row) => {
        acc[row.health] += 1;
        acc.seen += row.seen;
        acc.processed += row.processed;
        acc.mapMarkers += row.mapMarkers;
        return acc;
      },
      { active: 0, degraded: 0, quiet: 0, blocked: 0, silent: 0, seen: 0, processed: 0, mapMarkers: 0 },
    );

    return NextResponse.json({
      channels,
      summary,
      feedWindow: raw.length,
      generatedAt: new Date().toISOString(),
      durationMs: Date.now() - startedAt,
    });
  } catch (err) {
    console.warn('[CHANNEL_HEALTH] Redis read error:', err);
    return NextResponse.json(
      {
        channels: Array.from(rows.values()),
        summary: { active: 0, degraded: 0, quiet: 0, blocked: 0, silent: EXPECTED_CHANNELS.length, seen: 0, processed: 0, mapMarkers: 0 },
        feedWindow: 0,
        generatedAt: new Date().toISOString(),
      },
      { status: 200 },
    );
  }
}

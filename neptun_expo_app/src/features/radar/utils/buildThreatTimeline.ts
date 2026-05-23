import { radarThreatTypeLabel } from '../domain/radarThreatLabel';
import type { ThreatSource, ThreatTimelineItem } from '../types/radar.types';
import { severityForCategoryKey } from '../domain/radarSeverity';

function sourceFromMarker(m: Record<string, unknown>): ThreatSource {
  const ch = String(m.channel ?? m.source ?? '').toLowerCase();
  if (ch.includes('telegram')) return 'telegram';
  if (ch.includes('official')) return 'official';
  return 'system';
}

/** Надійний Unix ms з полів маркера API. */
export function parseMarkerTimeMs(m: Record<string, unknown>): number | null {
  for (const key of ['last_update_epoch', 'created_at_epoch', 'last_observation_epoch'] as const) {
    const n = Number(m[key]);
    if (Number.isFinite(n) && n > 0) return n;
  }
  const dateStr = String(m.date ?? m.timestamp ?? '').trim();
  if (dateStr) {
    const t = Date.parse(dateStr);
    if (Number.isFinite(t)) return t;
  }
  return null;
}

export function formatTimelineTime(ms: number | null, fallback = ''): string {
  if (ms == null || !Number.isFinite(ms)) return fallback.trim() || '—';
  try {
    return new Intl.DateTimeFormat('uk-UA', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
      timeZone: 'Europe/Kyiv',
    }).format(new Date(ms));
  } catch {
    const d = new Date(ms);
    const pad = (n: number) => n.toString().padStart(2, '0');
    return `${pad(d.getDate())}.${pad(d.getMonth() + 1)} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }
}

function normalizeTrackPointTs(raw: number): number | null {
  if (!Number.isFinite(raw) || raw <= 0) return null;
  return raw < 20_000_000_000 ? raw * 1000 : raw;
}

function trackPoints(m: Record<string, unknown>): Record<string, unknown>[] {
  const obs = m.observations;
  if (Array.isArray(obs) && obs.length >= 2) {
    return obs.filter((p) => p != null && typeof p === 'object') as Record<string, unknown>[];
  }
  const pos = m.positions;
  if (Array.isArray(pos) && pos.length >= 2) {
    return pos.filter((p) => p != null && typeof p === 'object') as Record<string, unknown>[];
  }
  return [];
}

function formatCoords(p: Record<string, unknown>): string {
  const lat = Number(p.lat);
  const lng = Number(p.lng);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return '';
  return `${lat.toFixed(2)}°, ${lng.toFixed(2)}°`;
}

function sourceLabel(raw: unknown): string {
  const s = String(raw ?? '').trim();
  if (!s || s === 'chain_update') return '';
  return s;
}

function sortTimeline(items: ThreatTimelineItem[]): ThreatTimelineItem[] {
  return [...items].sort((a, b) => {
    const ta = a.at ?? 0;
    const tb = b.at ?? 0;
    if (tb !== ta) return tb - ta;
    return a.id.localeCompare(b.id);
  });
}

/**
 * Хронологія однієї загрози: спостереження треку (новіші зверху) або повідомлення по track_id.
 */
export function buildThreatTimeline(
  primary: Record<string, unknown>,
  allMarkers: Record<string, unknown>[],
): ThreatTimelineItem[] {
  const categoryKey = String(primary.threatType ?? primary.threat_type ?? primary.type ?? 'unknown');
  const severity = severityForCategoryKey(categoryKey);
  const place = String(primary.place ?? primary.location ?? '').trim();
  const trackId = String(primary.track_id ?? '').trim();

  const trail = trackPoints(primary);
  if (trail.length >= 2) {
    const ordered = [...trail].sort(
      (a, b) => (normalizeTrackPointTs(Number(b.ts)) ?? 0) - (normalizeTrackPointTs(Number(a.ts)) ?? 0),
    );
    const items: ThreatTimelineItem[] = [];
    for (let i = 0; i < ordered.length; i += 1) {
      const p = ordered[i];
      const at = normalizeTrackPointTs(Number(p.ts));
      const src = sourceLabel(p.source);
      const coords = formatCoords(p);
      items.push({
        id: `trail-${trackId || 'local'}-${i}`,
        at,
        time: formatTimelineTime(at, ''),
        title: place || `Позиція ${i + 1}`,
        description: [coords, src].filter(Boolean).join(' · ') || undefined,
        source: sourceFromMarker(primary),
        severity,
      });
    }
    return items;
  }

  const related =
    trackId.length > 0
      ? allMarkers.filter((m) => String(m.track_id ?? '').trim() === trackId)
      : [primary];

  const byId = new Map<string, ThreatTimelineItem>();
  for (const m of related) {
    const id = String(m.id ?? m.track_id ?? '').trim() || `row-${byId.size}`;
    const at = parseMarkerTimeMs(m);
    const text = String(m.text ?? m.message ?? m.description ?? '').trim();
    const rowPlace = String(m.place ?? m.location ?? place).trim();
    byId.set(id, {
      id,
      at,
      time: formatTimelineTime(at, String(m.time ?? '')),
      title: rowPlace || radarThreatTypeLabel(categoryKey),
      description: text || undefined,
      source: sourceFromMarker(m),
      severity,
    });
  }

  const sorted = sortTimeline([...byId.values()]);
  if (sorted.length > 0) return sorted.slice(0, 12);

  const at = parseMarkerTimeMs(primary);
  const text = String(primary.text ?? primary.message ?? '').trim();
  return [
    {
      id: String(primary.id ?? 'single'),
      at,
      time: formatTimelineTime(at, String(primary.time ?? primary.date ?? '')),
      title: place || radarThreatTypeLabel(categoryKey),
      description: text || undefined,
      source: sourceFromMarker(primary),
      severity,
    },
  ];
}

import { severityForCategoryKey } from '../domain/radarSeverity';
import { radarThreatTypeLabel } from '../domain/radarThreatLabel';
import { qualityPercent, threatTrackMetaFromMarker } from '../domain/threatTrackMeta';
import type { RadarQuickFilter } from '../domain/radarQuickFilter';
import { radarFilterMatchesMarker } from '../domain/radarQuickFilter';
import type { ThreatCategory, ThreatEvent, ThreatSeverity, ThreatSource } from '../types/radar.types';
import { buildThreatTimeline, parseMarkerTimeMs } from './buildThreatTimeline';

function markerId(m: Record<string, unknown>, categoryKey: string, t: number | null): string {
  const id = String(m.id ?? m.track_id ?? '').trim();
  if (id) return id;
  return `${categoryKey}-${t ?? 0}-${String(m.place ?? m.location ?? '')}`;
}

function categoryFromKey(key: string): ThreatCategory {
  const t = key.toLowerCase();
  if (['shahed', 'drone', 'fpv', 'rozved'].includes(t)) return 'drone';
  if (['raketa', 'missile', 'ballistic', 'pusk', 'kab', 'rszv'].includes(t)) return 'missile';
  if (t === 'avia') return 'aviation';
  if (t === 'alarm' || t === 'alarm_cancel') return 'airAlert';
  if (['pvo', 'ppo', 'air_defense'].includes(t)) return 'airDefense';
  if (['vibuh', 'artillery', 'obstril'].includes(t)) return 'blast';
  return 'unknown';
}

function sourceFromMarker(m: Record<string, unknown>): ThreatSource {
  const ch = String(m.channel ?? m.source ?? '').toLowerCase();
  if (ch.includes('telegram')) return 'telegram';
  if (ch.includes('official')) return 'official';
  return 'system';
}

/** Одна картка = один маркер / одна загроза (без групування за типом). */
export function buildThreatEvents(
  markers: Record<string, unknown>[],
  opts: {
    filter: RadarQuickFilter;
    searchQuery?: string;
    myRegions?: string[];
    followedIds?: Set<string>;
    mutedCategories?: Set<string>;
  },
): ThreatEvent[] {
  const q = opts.searchQuery?.trim().toLowerCase() ?? '';
  const regions = opts.myRegions ?? [];
  const now = Date.now();

  const filtered = markers.filter((m) => {
    if (!radarFilterMatchesMarker(opts.filter, m, regions)) return false;
    if (!q) return true;
    const place = String(m.place ?? m.location ?? '').toLowerCase();
    const type = String(m.threatType ?? m.threat_type ?? m.type ?? '').toLowerCase();
    const label = radarThreatTypeLabel(type).toLowerCase();
    const text = String(m.text ?? m.message ?? '').toLowerCase();
    return place.includes(q) || type.includes(q) || label.includes(q) || text.includes(q);
  });

  const events: ThreatEvent[] = [];

  for (const m of filtered) {
    const categoryKey = String(m.threatType ?? m.threat_type ?? m.type ?? 'unknown');
    const updatedAt = parseMarkerTimeMs(m);
    const id = markerId(m, categoryKey, updatedAt);
    const place = String(m.place ?? m.location ?? '').trim();
    const text = String(m.text ?? m.message ?? '').trim();
    const meta = threatTrackMetaFromMarker(m);
    const confidence = qualityPercent(meta);
    const lat = Number(m.lat ?? m.latitude);
    const lng = Number(m.lng ?? m.longitude);
    const isNew = updatedAt != null && now - updatedAt < 8 * 60_000;
    const muted =
      (opts.mutedCategories?.has(id) ?? false) || (opts.mutedCategories?.has(categoryKey) ?? false);
    const timeline = buildThreatTimeline(m, filtered);

    events.push({
      id,
      category: categoryFromKey(categoryKey),
      categoryKey,
      title: radarThreatTypeLabel(categoryKey),
      locations: place ? [place] : [],
      severity: severityForCategoryKey(categoryKey),
      status: isNew ? 'active' : 'watch',
      createdAt: updatedAt,
      updatedAt,
      source: sourceFromMarker(m),
      signalCount: timeline.length > 0 ? timeline.length : 1,
      confidence,
      isNew,
      isFollowed: opts.followedIds?.has(id) ?? false,
      isMuted: muted,
      relatedMessages: text ? [text] : [],
      timeline,
      markers: [m],
      mapTarget: Number.isFinite(lat) && Number.isFinite(lng) ? { lat, lng } : undefined,
    });
  }

  events.sort((a, b) => {
    const du = (b.updatedAt ?? 0) - (a.updatedAt ?? 0);
    if (du !== 0) return du;
    return a.id.localeCompare(b.id);
  });

  return events;
}

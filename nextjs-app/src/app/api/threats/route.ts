import { NextResponse } from 'next/server';
import { cache } from '@/lib/cache';
import type { Marker } from '@/types';

export async function GET() {
  // Get markers from cache (populated by /api/data route)
  const entry = cache.get<{ tracks: Marker[] }>('data_markers');
  const markers = entry?.data.tracks || [];

  // Count threats by type
  const counts: Record<string, number> = {};
  markers.forEach((m) => {
    const type = m.threat_type || 'unknown';
    counts[type] = (counts[type] || 0) + 1;
  });

  return NextResponse.json({
    status: 'ok',
    total: markers.length,
    counts,
    timestamp: new Date().toISOString(),
  });
}

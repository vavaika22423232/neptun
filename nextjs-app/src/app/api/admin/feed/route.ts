import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { listAdminFeedEntries } from '@/lib/admin-feed-store';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  const { searchParams } = new URL(request.url);
  const limit = Number.parseInt(searchParams.get('limit') || '300', 10);
  const offset = Number.parseInt(searchParams.get('offset') || '0', 10);

  try {
    const result = await listAdminFeedEntries(limit, offset);
    return NextResponse.json(result);
  } catch (err) {
    console.warn('[ADMIN-FEED] Redis read error:', err);
    return NextResponse.json({
      entries: [],
      total: 0,
      limit: Math.max(1, Math.min(500, Number.isFinite(limit) ? limit : 300)),
      offset: Math.max(0, Number.isFinite(offset) ? offset : 0),
      error: 'feed_unavailable',
    });
  }
}

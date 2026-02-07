import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';

export async function POST() {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  try {
    // Clear the in-memory data cache (if using one) 
    // The main app cache is in @/lib/cache — we can clear it by importing
    const { cache } = await import('@/lib/cache');
    cache.clear();

    return NextResponse.json({ status: 'ok', message: 'Cache cleared' });
  } catch (err) {
    console.error('[ADMIN CACHE CLEAR]', err);
    return NextResponse.json({ error: 'Failed to clear cache' }, { status: 500 });
  }
}

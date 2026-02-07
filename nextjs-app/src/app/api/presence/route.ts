import { NextResponse } from 'next/server';

// In-memory presence tracking
const activeVisitors: Map<string, { platform: string; lastSeen: number }> = new Map();
const VISITOR_TIMEOUT = 60_000; // 60 seconds

function cleanupVisitors() {
  const now = Date.now();
  for (const [id, visitor] of activeVisitors) {
    if (now - visitor.lastSeen > VISITOR_TIMEOUT) {
      activeVisitors.delete(id);
    }
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { id, platform } = body;

    if (!id) {
      return NextResponse.json({ error: 'Missing id' }, { status: 400 });
    }

    // Update visitor
    activeVisitors.set(id, {
      platform: platform || 'web',
      lastSeen: Date.now(),
    });

    // Cleanup old visitors
    cleanupVisitors();

    // Count by platform
    let web = 0;
    let apps = 0;
    for (const visitor of activeVisitors.values()) {
      if (visitor.platform === 'web') web++;
      else apps++;
    }

    return NextResponse.json({
      total: activeVisitors.size,
      web,
      apps,
      android: apps,
    });
  } catch {
    return NextResponse.json({ total: 0, web: 0, apps: 0 }, { status: 200 });
  }
}

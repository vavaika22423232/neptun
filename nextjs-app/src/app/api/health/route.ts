import { NextResponse } from 'next/server';
import { redisHealthy } from '@/lib/redis';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const isRedisHealthy = await redisHealthy();
    
    if (!isRedisHealthy) {
      return NextResponse.json(
        { status: 'error', database: 'unhealthy', timestamp: new Date().toISOString() },
        { status: 503 }
      );
    }

    return NextResponse.json(
      { status: 'ok', database: 'healthy', timestamp: new Date().toISOString() },
      { status: 200 }
    );
  } catch (err) {
    return NextResponse.json(
      { status: 'error', message: 'Internal server error', timestamp: new Date().toISOString() },
      { status: 500 }
    );
  }
}

import { NextResponse } from 'next/server';
import { getMonetizationConfig } from '@/lib/monetization/config';

export const dynamic = 'force-dynamic';

export async function GET() {
  return NextResponse.json(getMonetizationConfig());
}

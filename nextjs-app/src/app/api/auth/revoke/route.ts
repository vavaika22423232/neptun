import { NextResponse } from 'next/server';

/**
 * POST /api/auth/revoke
 * Revoke tokens (logout). Fire-and-forget from the app side.
 */
export async function POST() {
  // In a stateless JWT system, there's nothing to revoke server-side.
  // If we later add a token blacklist, it would go here.
  return NextResponse.json({ status: 'ok' });
}

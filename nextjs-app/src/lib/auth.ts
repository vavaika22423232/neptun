import { getAdminHeaderSecret, safeCompare } from '@/lib/server-secrets';

// ============================================
// Admin authentication middleware
// ============================================

/**
 * Check if the request has a valid admin API secret (not ingest-only).
 * Looks in query param, header, or body.
 */
export function requireSecret(request: Request): boolean {
  const secret = getAdminHeaderSecret();
  if (!secret) return false;

  const url = new URL(request.url);
  const q = url.searchParams.get('secret');
  if (q && safeCompare(q, secret)) return true;

  const h = request.headers.get('X-Auth-Secret') || '';
  if (h && safeCompare(h, secret)) return true;

  return false;
}

/**
 * Return 401 response for unauthorized requests
 */
export function unauthorizedResponse(): Response {
  return new Response(JSON.stringify({ error: 'Unauthorized' }), {
    status: 401,
    headers: { 'Content-Type': 'application/json' },
  });
}

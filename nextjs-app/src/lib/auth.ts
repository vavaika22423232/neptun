// ============================================
// Admin authentication middleware
// ============================================

const AUTH_SECRET = process.env.AUTH_SECRET || '';

/**
 * Check if the request has a valid admin secret.
 * Looks in query param, header, or body.
 */
export function requireSecret(request: Request): boolean {
  if (!AUTH_SECRET) return false;

  // Check query param
  const url = new URL(request.url);
  if (url.searchParams.get('secret') === AUTH_SECRET) return true;

  // Check header
  if (request.headers.get('X-Auth-Secret') === AUTH_SECRET) return true;

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

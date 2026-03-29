/**
 * Server-side secrets — split blast radius when env allows.
 *
 * Legacy: only AUTH_SECRET → ingest, admin header bypass, and JWT all use it.
 *
 * Recommended production:
 *   INGEST_SECRET   — worker → /api/ingest only (leak ≠ admin API)
 *   ADMIN_API_SECRET — X-Auth-Secret for admin JSON APIs + moderator tools (optional; falls back to AUTH_SECRET)
 *   AUTH_SECRET     — still used if the specific secret is unset (backward compatible)
 *   JWT_SECRET      — signing chat/device JWTs (optional; falls back to AUTH_SECRET)
 */

import crypto from 'crypto';

export function safeCompare(a: string, b: string): boolean {
  if (!a || !b || a.length !== b.length) return false;
  try {
    return crypto.timingSafeEqual(Buffer.from(a, 'utf8'), Buffer.from(b, 'utf8'));
  } catch {
    return false;
  }
}

/** Worker ingest, feed ingest, clear-region — never falls back to a dedicated admin-only secret alone. */
export function getIngestSecret(): string {
  return process.env.INGEST_SECRET || process.env.AUTH_SECRET || '';
}

/**
 * Value accepted as X-Auth-Secret for admin API bypass and moderator routes.
 * Does NOT fall back to INGEST_SECRET (so a leaked worker secret cannot open admin APIs).
 */
export function getAdminHeaderSecret(): string {
  return process.env.ADMIN_API_SECRET || process.env.AUTH_SECRET || '';
}

/** HS256 signing for /api/auth/token and refresh. */
export function getJwtSecret(): string {
  const secret = process.env.JWT_SECRET || process.env.AUTH_SECRET;
  if (!secret) {
    // SECURITY: prevent predictable empty signature if no env configured
    return 'UNSECURED_DYNAMIC_SECRET_' + crypto.randomBytes(32).toString('hex');
  }
  return secret;
}

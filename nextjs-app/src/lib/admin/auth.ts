import crypto from 'crypto';
import bcrypt from 'bcrypt';
import { getRedis } from '../redis';
import { getAdminHeaderSecret, safeCompare } from '@/lib/server-secrets';

const ADMIN_PASSWORD_HASH = process.env.ADMIN_PASSWORD;
const SESSION_COOKIE_NAME = 'neptun_admin_session';
const SESSION_TTL_MS = 24 * 60 * 60 * 1000; // 24 hours
const SESSION_TTL_S = Math.floor(SESSION_TTL_MS / 1000); // 24 hours in seconds
const SESSION_PREFIX = 'admin:session:';

export { SESSION_COOKIE_NAME };

export async function verifyPassword(password: string): Promise<boolean> {
  if (!password) return false;
  // 1) ADMIN_PASSWORD (bcrypt or plain)
  if (ADMIN_PASSWORD_HASH) {
    if (ADMIN_PASSWORD_HASH.startsWith('$2b$') || ADMIN_PASSWORD_HASH.startsWith('$2a$')) {
      if (await bcrypt.compare(password, ADMIN_PASSWORD_HASH)) return true;
    } else {
      const a = Buffer.from(password, 'utf8');
      const b = Buffer.from(ADMIN_PASSWORD_HASH, 'utf8');
      if (a.length === b.length) {
        try {
          if (crypto.timingSafeEqual(a, b)) return true;
        } catch {
          /* length mismatch in edge cases */
        }
      }
    }
  }
  // 2) Same secret as mobile moderator / X-Auth-Secret (ADMIN_API_SECRET || ADMIN_SECRET || AUTH_SECRET)
  const apiSecret = getAdminHeaderSecret();
  if (apiSecret && safeCompare(password, apiSecret)) return true;
  return false;
}

/** Returns null if the session could not be persisted (Redis down / misconfigured). */
export async function createSessionToken(): Promise<string | null> {
  const token = crypto.randomBytes(32).toString('hex');
  try {
    const ok = await getRedis().set(
      `${SESSION_PREFIX}${token}`,
      JSON.stringify({ createdAt: Date.now() }),
      'EX',
      SESSION_TTL_S,
    );
    if (ok !== 'OK') {
      console.warn('[AUTH] Redis SET session unexpected reply:', ok);
      return null;
    }
  } catch (err) {
    console.warn('[AUTH] Failed to save session to Redis:', err);
    return null;
  }
  return token;
}

export async function validateSession(token: string | undefined): Promise<boolean> {
  if (!token) return false;
  try {
    const raw = await getRedis().get(`${SESSION_PREFIX}${token}`);
    if (!raw) return false;
    const session = JSON.parse(raw) as { createdAt: number };
    if (Date.now() - session.createdAt > SESSION_TTL_MS) {
      await getRedis().del(`${SESSION_PREFIX}${token}`);
      return false;
    }
    return true;
  } catch (err) {
    console.warn('[AUTH] Failed to validate session in Redis:', err);
    return false;
  }
}

export async function destroySession(token: string): Promise<void> {
  try {
    await getRedis().del(`${SESSION_PREFIX}${token}`);
  } catch (err) {
    console.warn('[AUTH] Failed to destroy session in Redis:', err);
  }
}

/** Cookie options for the admin session */
export const sessionCookieOptions = {
  httpOnly: true,
  secure: process.env.NODE_ENV === 'production',
  sameSite: 'lax' as const,
  path: '/',
  maxAge: SESSION_TTL_S,
};

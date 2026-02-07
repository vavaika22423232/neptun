import crypto from 'crypto';

const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || '99446626';
const SESSION_COOKIE_NAME = 'neptun_admin_session';
const SESSION_TTL_MS = 24 * 60 * 60 * 1000; // 24 hours

// In-memory session store (survives across requests in the same process)
const sessions = new Map<string, { createdAt: number }>();

export { SESSION_COOKIE_NAME };

export function verifyPassword(password: string): boolean {
  return password === ADMIN_PASSWORD;
}

export function createSessionToken(): string {
  const token = crypto.randomBytes(32).toString('hex');
  sessions.set(token, { createdAt: Date.now() });
  return token;
}

export function validateSession(token: string | undefined): boolean {
  if (!token) return false;
  const session = sessions.get(token);
  if (!session) return false;
  if (Date.now() - session.createdAt > SESSION_TTL_MS) {
    sessions.delete(token);
    return false;
  }
  return true;
}

export function destroySession(token: string): void {
  sessions.delete(token);
}

/** Cookie options for the admin session */
export const sessionCookieOptions = {
  httpOnly: true,
  secure: process.env.NODE_ENV === 'production',
  sameSite: 'lax' as const,
  path: '/',
  maxAge: SESSION_TTL_MS / 1000, // seconds
};

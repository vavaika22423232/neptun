import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';

/**
 * POST /api/test-notification
 * Send a test push notification to verify FCM setup.
 * Firebase Admin SDK is loaded dynamically at runtime only if installed.
 * Requires admin session or X-Auth-Secret (same as other admin APIs).
 */
export async function POST(request: Request) {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  try {
    const body = await request.json();
    const { token } = body;

    if (!token) {
      return NextResponse.json({ error: 'Missing FCM token' }, { status: 400 });
    }

    const firebaseCreds = process.env.FIREBASE_CREDENTIALS;
    if (firebaseCreds) {
      try {
        // Use dynamic require to avoid build-time module resolution
        // firebase-admin is an optional dependency installed only in production
        const adminModule = await (Function('return import("firebase-admin")')() as Promise<Record<string, unknown>>);
        const admin = adminModule as {
          apps: unknown[];
          initializeApp: (opts: Record<string, unknown>) => void;
          credential: { cert: (creds: Record<string, unknown>) => unknown };
          messaging: () => { send: (msg: Record<string, unknown>) => Promise<void> };
        };
        if (!admin.apps.length) {
          const creds = JSON.parse(Buffer.from(firebaseCreds, 'base64').toString('utf-8'));
          admin.initializeApp({ credential: admin.credential.cert(creds) });
        }
        await admin.messaging().send({
          token,
          notification: {
            title: 'Нептун',
            body: 'Тестове сповіщення працює! ✅',
          },
        });
        console.log('[FCM] Test notification sent');
        return NextResponse.json({ status: 'ok', sent: true });
      } catch (err) {
        console.error('[FCM] Test notification failed:', err);
        return NextResponse.json({ status: 'ok', sent: false, reason: 'firebase_error' });
      }
    }

    console.log('[FCM] Test notification requested but Firebase not configured');
    return NextResponse.json({ status: 'ok', sent: false, reason: 'firebase_not_configured' });
  } catch (err) {
    console.error('[FCM] Test error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}

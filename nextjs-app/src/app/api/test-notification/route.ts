import { NextResponse } from 'next/server';

/**
 * POST /api/test-notification
 * Send a test push notification to verify FCM setup.
 * TODO: Integrate with Firebase Admin SDK when FIREBASE_CREDENTIALS is set.
 */
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { token } = body;

    if (!token) {
      return NextResponse.json({ error: 'Missing FCM token' }, { status: 400 });
    }

    // Try to send via Firebase Admin SDK if configured
    const firebaseCreds = process.env.FIREBASE_CREDENTIALS;
    if (firebaseCreds) {
      try {
        // Dynamic import to avoid startup crash if firebase-admin not installed
        const admin = await import('firebase-admin');
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

    // Firebase not configured — still return OK so app doesn't error
    console.log('[FCM] Test notification requested but Firebase not configured');
    return NextResponse.json({ status: 'ok', sent: false, reason: 'firebase_not_configured' });
  } catch (err) {
    console.error('[FCM] Test error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}

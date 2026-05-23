/**
 * Firebase Cloud Messaging utility for the Next.js server.
 * Provides token-based push notifications (e.g., feedback replies).
 *
 * Firebase Admin SDK is loaded dynamically to avoid build-time issues
 * (it's an optional production dependency).
 */

import fs from 'fs';
import path from 'path';

const DATA_DIR = process.env.DATA_DIR || '/data';
const DEVICES_FILE = path.join(DATA_DIR, 'devices.json');

interface DeviceRegistration {
  token: string;
  device_id: string;
  platform?: string;
  enabled?: boolean;
  [key: string]: unknown;
}

let _firebaseInitialized = false;
let _messaging: { send: (msg: Record<string, unknown>) => Promise<string> } | null = null;

/**
 * Initialize Firebase Admin SDK (once). Returns messaging instance or null.
 */
async function getMessaging() {
  if (_firebaseInitialized) return _messaging;
  _firebaseInitialized = true;

  // Try FIREBASE_CREDENTIALS (base64) or FIREBASE_CREDENTIALS_FILE
  const credsB64 = process.env.FIREBASE_CREDENTIALS;
  const credsB64Alt = process.env.FIREBASE_CREDENTIALS_BASE64;
  const credsFile = process.env.FIREBASE_CREDENTIALS_FILE;

  const b64 = credsB64 || credsB64Alt;

  try {
    const adminModule = await (Function('return import("firebase-admin")')() as Promise<Record<string, unknown>>);
    // Handle both ESM default export and CommonJS module shape
    const admin = (adminModule.default || adminModule) as {
      apps: unknown[];
      initializeApp: (opts: Record<string, unknown>) => void;
      credential: { cert: (creds: Record<string, unknown>) => unknown };
      messaging: () => { send: (msg: Record<string, unknown>) => Promise<string> };
    };

    if (!admin.apps.length) {
      if (b64) {
        const creds = JSON.parse(Buffer.from(b64, 'base64').toString('utf-8'));
        admin.initializeApp({ credential: admin.credential.cert(creds) });
      } else if (credsFile && fs.existsSync(credsFile)) {
        const creds = JSON.parse(fs.readFileSync(credsFile, 'utf-8'));
        admin.initializeApp({ credential: admin.credential.cert(creds) });
      } else {
        console.warn('[FCM] No Firebase credentials configured');
        return null;
      }
    }

    _messaging = admin.messaging();
    return _messaging;
  } catch (err) {
    console.error('[FCM] Firebase init error:', err);
    return null;
  }
}

/**
 * Look up the FCM token for a given device_id from devices.json.
 */
function getFcmTokenForDevice(deviceId: string): string | null {
  if (!deviceId) return null;
  try {
    const raw = fs.readFileSync(DEVICES_FILE, 'utf-8');
    const devices: DeviceRegistration[] = JSON.parse(raw);
    const device = devices.find(d => d.device_id === deviceId && d.enabled !== false);
    return device?.token || null;
  } catch {
    return null;
  }
}

/**
 * Send a push notification to a specific device by device_id.
 * Returns true if sent successfully.
 */
export type GatedPushOptions = {
  regionId?: string;
  threatType?: string;
  severity?: 'low' | 'medium' | 'high' | 'critical';
  isCritical?: boolean;
  dedupeKey?: string;
  skipGate?: boolean;
};

/**
 * Send push only if monetization rules allow (PRO smart notifications, quiet mode, dedupe).
 * Critical alerts with criticalOverride still deliver during quiet hours when configured.
 */
export async function sendPushToDeviceGated(
  deviceId: string,
  title: string,
  body: string,
  data?: Record<string, string>,
  opts?: GatedPushOptions,
): Promise<boolean> {
  if (!opts?.skipGate) {
    try {
      const { shouldDeliverPush } = await import('@/lib/monetization/push-notification-gate');
      const gate = await shouldDeliverPush({
        deviceId,
        regionId: opts?.regionId,
        threatType: opts?.threatType,
        severity: opts?.severity,
        isCritical: opts?.isCritical,
        dedupeKey: opts?.dedupeKey ?? `${opts?.regionId ?? 'all'}:${opts?.threatType ?? 'general'}`,
      });
      if (!gate.allow) {
        console.log(`[FCM] Push suppressed for ${deviceId.slice(0, 8)}: ${gate.reason}`);
        return false;
      }
    } catch (err) {
      console.warn('[FCM] Push gate check failed — sending anyway:', err);
    }
  }
  return sendPushToDevice(deviceId, title, body, data);
}

export async function sendPushToDevice(
  deviceId: string,
  title: string,
  body: string,
  data?: Record<string, string>,
): Promise<boolean> {
  const token = getFcmTokenForDevice(deviceId);
  if (!token) {
    console.log(`[FCM] No token for device ${deviceId?.slice(0, 8)}...`);
    return false;
  }

  const messaging = await getMessaging();
  if (!messaging) return false;

  try {
    await messaging.send({
      token,
      notification: { title, body },
      data: data || {},
      android: {
        priority: 'high',
        notification: {
          channelId: 'feedback_alerts',
          icon: 'ic_notification',
          sound: 'default',
        },
      },
      apns: {
        payload: {
          aps: {
            alert: { title, body },
            sound: 'default',
            badge: 1,
            'content-available': 1,
          },
        },
        headers: { 'apns-priority': '10' },
      },
    });
    console.log(`[FCM] Feedback push sent to device ${deviceId?.slice(0, 8)}...`);
    return true;
  } catch (err) {
    console.error(`[FCM] Push to device failed:`, err);
    return false;
  }
}

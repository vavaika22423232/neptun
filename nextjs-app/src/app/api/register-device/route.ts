import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

const DATA_DIR = process.env.DATA_DIR || '/data';
const DEVICES_FILE = path.join(DATA_DIR, 'devices.json');

interface DeviceRegistration {
  token: string;
  regions: string[];
  oblast_ids?: string[];
  raion_ids?: string[];
  device_id: string;
  platform?: string;
  enabled?: boolean;
  updated_at: string;
}

function loadDevices(): DeviceRegistration[] {
  try {
    if (fs.existsSync(DEVICES_FILE)) {
      return JSON.parse(fs.readFileSync(DEVICES_FILE, 'utf-8'));
    }
  } catch { /* empty */ }
  return [];
}

function saveDevices(devices: DeviceRegistration[]) {
  const dir = path.dirname(DEVICES_FILE);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(DEVICES_FILE, JSON.stringify(devices, null, 2), 'utf-8');
}

/**
 * POST /api/register-device
 * Register or update FCM device token for push notifications.
 */
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { token, regions, oblast_ids, raion_ids, device_id, platform, enabled } = body;

    if (!device_id) {
      return NextResponse.json({ error: 'Missing device_id' }, { status: 400 });
    }

    const devices = loadDevices();
    const idx = devices.findIndex((d) => d.device_id === device_id);

    const registration: DeviceRegistration = {
      token: token || '',
      regions: regions || [],
      oblast_ids: oblast_ids || [],
      raion_ids: raion_ids || [],
      device_id,
      platform: platform || 'unknown',
      enabled: enabled !== false,
      updated_at: new Date().toISOString(),
    };

    if (idx >= 0) {
      devices[idx] = registration;
    } else {
      devices.push(registration);
    }

    // Keep last 10000 devices
    const trimmed = devices.slice(-10000);
    saveDevices(trimmed);

    console.log(`[DEVICE] Registered ${device_id} (${platform}) — ${regions?.length || 0} regions`);
    return NextResponse.json({ status: 'ok' });
  } catch (err) {
    console.error('[DEVICE] Register error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}

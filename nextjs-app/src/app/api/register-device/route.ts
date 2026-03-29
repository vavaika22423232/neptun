import { NextResponse } from 'next/server';
import fs from 'fs';
import fsp from 'fs/promises';
import path from 'path';
import crypto from 'crypto';
import { RegisterDeviceSchema } from '@/lib/api-schemas';

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

// In-memory device index for fast lookups
let _deviceMap: Map<string, number> | null = null;
let _devices: DeviceRegistration[] | null = null;
let _devicesLoaded = false;

async function loadDevices(): Promise<DeviceRegistration[]> {
  if (_devicesLoaded && _devices) return _devices;
  try {
    const raw = await fsp.readFile(DEVICES_FILE, 'utf-8');
    _devices = JSON.parse(raw) as DeviceRegistration[];
  } catch {
    _devices = [];
  }
  // Build index
  _deviceMap = new Map();
  _devices!.forEach((d, i) => _deviceMap!.set(d.device_id, i));
  _devicesLoaded = true;
  return _devices!;
}

async function saveDevices(devices: DeviceRegistration[]): Promise<void> {
  const dir = path.dirname(DEVICES_FILE);
  try { await fsp.access(dir); } catch { await fsp.mkdir(dir, { recursive: true }); }
  const tmp = DEVICES_FILE + '.tmp.' + crypto.randomBytes(4).toString('hex');
  await fsp.writeFile(tmp, JSON.stringify(devices), 'utf-8');
  await fsp.rename(tmp, DEVICES_FILE);
}

// Debounce writes — batch rapid registrations
let _saveTimer: ReturnType<typeof setTimeout> | null = null;
const SAVE_DEBOUNCE = 5_000; // flush to disk every 5s max

function scheduleSave() {
  if (_saveTimer) return; // already scheduled
  _saveTimer = setTimeout(async () => {
    _saveTimer = null;
    if (_devices) {
      try { await saveDevices(_devices); }
      catch (err) { console.error('[DEVICE] Save error:', err); }
    }
  }, SAVE_DEBOUNCE);
}

/**
 * POST /api/register-device
 * Register or update FCM device token for push notifications.
 */
export async function POST(request: Request) {
  try {
    const rawBody = await request.json();
    const parsed = RegisterDeviceSchema.safeParse(rawBody);
    if (!parsed.success) {
      return NextResponse.json({ error: parsed.error.issues[0]?.message || 'Invalid input' }, { status: 400 });
    }
    const { token, regions, oblast_ids, raion_ids, device_id, platform, enabled } = parsed.data;

    const devices = await loadDevices();
    const idx = _deviceMap!.get(device_id);

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

    if (idx !== undefined) {
      devices[idx] = registration;
    } else {
      devices.push(registration);
      _deviceMap!.set(device_id, devices.length - 1);
    }

    // Trim to 10K in-memory
    if (devices.length > 10000) {
      _devices = devices.slice(-10000);
      // Rebuild index
      _deviceMap = new Map();
      _devices.forEach((d, i) => _deviceMap!.set(d.device_id, i));
    }

    // Debounced save (avoids full serialize on every registration)
    scheduleSave();

    console.log(`[DEVICE] Registered ${device_id} (${platform}) — ${regions?.length || 0} regions`);
    return NextResponse.json({ status: 'ok' });
  } catch (err) {
    console.error('[DEVICE] Register error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}

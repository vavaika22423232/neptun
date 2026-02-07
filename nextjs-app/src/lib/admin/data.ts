import fs from 'fs';
import path from 'path';
import crypto from 'crypto';

const DATA_DIR = process.env.DATA_DIR || '/data';
const MESSAGES_FILE = path.join(DATA_DIR, 'messages.json');
const HIDDEN_FILE = path.join(DATA_DIR, 'hidden.json');
const BLOCKED_FILE = path.join(DATA_DIR, 'blocked.json');
const SETTINGS_FILE = path.join(DATA_DIR, 'admin_settings.json');
const FALLBACK_DIR = path.resolve(process.cwd(), '..');

function resolveFile(primary: string, filename: string): string {
  if (fs.existsSync(primary)) return primary;
  const fallback = path.join(FALLBACK_DIR, filename);
  if (fs.existsSync(fallback)) return fallback;
  return primary; // default to primary even if not exists
}

/** Atomic write: write to tmp then rename */
function atomicWrite(filePath: string, data: string): void {
  const dir = path.dirname(filePath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  const tmp = filePath + '.tmp.' + crypto.randomBytes(4).toString('hex');
  fs.writeFileSync(tmp, data, 'utf-8');
  fs.renameSync(tmp, filePath);
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function readJson<T = any>(filePath: string, fallbackFilename: string, defaultVal: T): T {
  const resolved = resolveFile(filePath, fallbackFilename);
  try {
    if (fs.existsSync(resolved)) {
      const raw = fs.readFileSync(resolved, 'utf-8');
      return JSON.parse(raw) as T;
    }
  } catch (err) {
    console.warn(`[ADMIN DATA] Failed to read ${resolved}:`, err);
  }
  return defaultVal;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export interface MessageRecord { [key: string]: any; }

// ── Messages ──

export function loadMessages(): MessageRecord[] {
  const data = readJson(MESSAGES_FILE, 'messages.json', [] as MessageRecord[]);
  return Array.isArray(data) ? data : (data as { messages?: MessageRecord[] }).messages || [];
}

export function saveMessages(messages: MessageRecord[]): void {
  atomicWrite(resolveFile(MESSAGES_FILE, 'messages.json'), JSON.stringify(messages, null, 2));
}

// ── Hidden markers ──

export function loadHidden(): string[] {
  return readJson<string[]>(HIDDEN_FILE, 'hidden.json', []);
}

export function saveHidden(hidden: string[]): void {
  atomicWrite(resolveFile(HIDDEN_FILE, 'hidden.json'), JSON.stringify(hidden, null, 2));
}

// ── Blocked users ──

export function loadBlocked(): string[] {
  return readJson<string[]>(BLOCKED_FILE, 'blocked.json', []);
}

export function saveBlocked(blocked: string[]): void {
  atomicWrite(resolveFile(BLOCKED_FILE, 'blocked.json'), JSON.stringify(blocked, null, 2));
}

// ── Admin settings ──

export interface AdminSettings {
  monitorPeriod: number; // minutes
  ttlEnabled: boolean;
}

export function loadSettings(): AdminSettings {
  return readJson<AdminSettings>(SETTINGS_FILE, 'admin_settings.json', {
    monitorPeriod: 30,
    ttlEnabled: true,
  });
}

export function saveSettings(settings: AdminSettings): void {
  atomicWrite(SETTINGS_FILE, JSON.stringify(settings, null, 2));
}

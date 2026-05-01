import fs from 'fs';
import fsp from 'fs/promises';
import path from 'path';
import crypto from 'crypto';

const DATA_DIR = process.env.DATA_DIR || '/data';
const MESSAGES_FILE = path.join(DATA_DIR, 'messages.json');
const HIDDEN_FILE = path.join(DATA_DIR, 'hidden.json');
const BLOCKED_FILE = path.join(DATA_DIR, 'blocked.json');
const SETTINGS_FILE = path.join(DATA_DIR, 'admin_settings.json');
const CHAT_BANS_FILE = path.join(DATA_DIR, 'chat_bans.json');
const CHAT_MODS_FILE = path.join(DATA_DIR, 'chat_moderators.json');
const FALLBACK_DIR = path.resolve(process.cwd(), '..');

// ── In-memory read cache with TTL ────────────────────────────────────────
interface CachedItem<T> { data: T; ts: number; }
const CACHE_TTL = 30_000; // 30s — settings/hidden/bans/mods rarely change
const _rcache = new Map<string, CachedItem<unknown>>();

function getCached<T>(key: string): T | null {
  const e = _rcache.get(key);
  if (!e || Date.now() - e.ts > CACHE_TTL) { _rcache.delete(key); return null; }
  return e.data as T;
}
function setCached<T>(key: string, data: T): T { _rcache.set(key, { data, ts: Date.now() }); return data; }
export function invalidateCache(key?: string) {
  if (key) _rcache.delete(key);
  else _rcache.clear();
}

// ── File resolution ──────────────────────────────────────────────────────
function resolveFile(primary: string, filename: string): string {
  if (fs.existsSync(primary)) return primary;
  const fallback = path.join(FALLBACK_DIR, filename);
  if (fs.existsSync(fallback)) return fallback;
  return primary;
}

// ── Atomic write ─────────────────────────────────────────────────────────
function atomicWrite(filePath: string, data: string): void {
  const dir = path.dirname(filePath);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  const tmp = filePath + '.tmp.' + crypto.randomBytes(4).toString('hex');
  fs.writeFileSync(tmp, data, 'utf-8');
  fs.renameSync(tmp, filePath);
}

async function atomicWriteAsync(filePath: string, data: string): Promise<void> {
  const dir = path.dirname(filePath);
  try { await fsp.access(dir); } catch { await fsp.mkdir(dir, { recursive: true }); }
  const tmp = filePath + '.tmp.' + crypto.randomBytes(4).toString('hex');
  await fsp.writeFile(tmp, data, 'utf-8');
  await fsp.rename(tmp, filePath);
}

// ── Read JSON (sync, cached for small config files) ──────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function readJson<T = any>(filePath: string, fallbackFilename: string, defaultVal: T, cacheKey?: string): T {
  if (cacheKey) { const c = getCached<T>(cacheKey); if (c !== null) return c; }
  const resolved = resolveFile(filePath, fallbackFilename);
  try {
    if (fs.existsSync(resolved)) {
      const raw = fs.readFileSync(resolved, 'utf-8');
      const result = JSON.parse(raw) as T;
      if (cacheKey) setCached(cacheKey, result);
      return result;
    }
  } catch (err) {
    console.warn(`[ADMIN DATA] Failed to read ${resolved}:`, err);
  }
  return defaultVal;
}

// ── Async read JSON (for large files like messages.json) ─────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
async function readJsonAsync<T = any>(filePath: string, fallbackFilename: string, defaultVal: T): Promise<T> {
  const resolved = resolveFile(filePath, fallbackFilename);
  try {
    const raw = await fsp.readFile(resolved, 'utf-8');
    return JSON.parse(raw) as T;
  } catch { return defaultVal; }
}

// ── Write lock for messages.json (prevents concurrent clobber) ───────────
let _writeLock: Promise<void> = Promise.resolve();

export function withWriteLock<T>(fn: () => Promise<T>): Promise<T> {
  const prev = _writeLock;
  let resolve!: () => void;
  _writeLock = new Promise<void>((r) => { resolve = r; });
  return prev.then(fn).finally(() => resolve());
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export interface MessageRecord { [key: string]: any; }

// ── Messages (NOT cached — large, frequently written) ────────────────────

export function loadMessages(): MessageRecord[] {
  const data = readJson(MESSAGES_FILE, 'messages.json', [] as MessageRecord[]);
  return Array.isArray(data) ? data : (data as { messages?: MessageRecord[] }).messages || [];
}

export async function loadMessagesAsync(): Promise<MessageRecord[]> {
  const data = await readJsonAsync(MESSAGES_FILE, 'messages.json', [] as MessageRecord[]);
  return Array.isArray(data) ? data : (data as { messages?: MessageRecord[] }).messages || [];
}

export function saveMessages(messages: MessageRecord[]): void {
  atomicWrite(resolveFile(MESSAGES_FILE, 'messages.json'), JSON.stringify(messages));
}

export async function saveMessagesAsync(messages: MessageRecord[]): Promise<void> {
  await atomicWriteAsync(resolveFile(MESSAGES_FILE, 'messages.json'), JSON.stringify(messages));
}

// ── Hidden markers (cached 30s) ──────────────────────────────────────────

export function loadHidden(): string[] {
  return readJson<string[]>(HIDDEN_FILE, 'hidden.json', [], 'hidden');
}

export function saveHidden(hidden: string[]): void {
  invalidateCache('hidden');
  atomicWrite(resolveFile(HIDDEN_FILE, 'hidden.json'), JSON.stringify(hidden));
}

// ── Blocked users (cached 30s) ───────────────────────────────────────────

export function loadBlocked(): string[] {
  return readJson<string[]>(BLOCKED_FILE, 'blocked.json', [], 'blocked');
}

export function saveBlocked(blocked: string[]): void {
  invalidateCache('blocked');
  atomicWrite(resolveFile(BLOCKED_FILE, 'blocked.json'), JSON.stringify(blocked));
}

// ── Admin settings (NO cache — PM2 multi-worker: confidence threshold must apply immediately) ───

export interface AdminSettings {
  monitorPeriod: number;
  ttlEnabled: boolean;
  minConfidence: number;
  /** When false, spatial correlator (`findSpatialMatch`) is skipped — only `track_id` merges. */
  spatialCorrelatorEnabled?: boolean;
  corroborationMinObservations?: number;
  corroborationWindowMinutes?: number;
  corroborationMaxRadiusKm?: number;
  /** 0 = off; >=2 requires that many distinct `source` values among recent track points. */
  corroborationMinDistinctSources?: number;
  /**
   * When true, public map / ingest hides markers until two distinct channel_name values
   * appear in observations (except channel_priority <= 1). Default on (new installs).
   */
  dualSourceMapGate?: boolean;
  regionUncertaintyKm?: number;
  corroboratedUncertaintyKm?: number;
}

const ADMIN_SETTINGS_DEFAULTS: AdminSettings = {
  monitorPeriod: 30,
  ttlEnabled: true,
  minConfidence: 0.65,
  spatialCorrelatorEnabled: true,
  corroborationMinObservations: 2,
  corroborationWindowMinutes: 30,
  corroborationMaxRadiusKm: 45,
  corroborationMinDistinctSources: 2,
  dualSourceMapGate: true,
  regionUncertaintyKm: 38,
  corroboratedUncertaintyKm: 9,
};

export function loadSettings(): AdminSettings {
  const fromDisk = readJson<Partial<AdminSettings>>(SETTINGS_FILE, 'admin_settings.json', {});
  return { ...ADMIN_SETTINGS_DEFAULTS, ...fromDisk };
}

export function saveSettings(settings: AdminSettings): void {
  invalidateCache('settings');
  atomicWrite(SETTINGS_FILE, JSON.stringify(settings));
}

// ── Chat bans (NO cache — PM2 runs 4 workers, cache would stale on other workers) ───

export interface BanEntry {
  device_id: string;
  nickname: string;
  reason: string;
  banned_at: string;
  banned_by?: string;
  /** ISO string; if set and in the past, ban is expired */
  expires_at?: string;
  /** Persists across app reinstall (Android ID) */
  hardware_id?: string;
}

export function loadChatBans(): BanEntry[] {
  return readJson<BanEntry[]>(CHAT_BANS_FILE, 'chat_bans.json', []); // no cacheKey = always read from disk
}

export function saveChatBans(bans: BanEntry[]): void {
  atomicWrite(resolveFile(CHAT_BANS_FILE, 'chat_bans.json'), JSON.stringify(bans, null, 2));
}

/** Check if a user is banned by device_id, nickname, or hardware_id (ignores expired bans) */
export function isBanned(
  deviceId?: string,
  nickname?: string,
  hardwareId?: string
): BanEntry | null {
  const bans = loadChatBans();
  const now = new Date();
  const found = bans.find((b) => {
    if (b.expires_at && new Date(b.expires_at) < now) return false;
    return (
      (deviceId && b.device_id && b.device_id === deviceId) ||
      (nickname && b.nickname && b.nickname.toLowerCase() === nickname.toLowerCase()) ||
      (hardwareId && b.hardware_id && b.hardware_id === hardwareId)
    );
  });
  return found ?? null;
}

// ── Chat moderators (cached 30s) ─────────────────────────────────────────

export function loadChatModerators(): string[] {
  return readJson<string[]>(CHAT_MODS_FILE, 'chat_moderators.json', [], 'chat_mods');
}

/** Check if device_id belongs to a moderator */
export function isModeratorDevice(deviceId: string): boolean {
  return loadChatModerators().includes(deviceId);
}

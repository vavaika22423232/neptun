import { AppState, type AppStateStatus } from 'react-native';
import { endpoints } from '../config/api';
import { AppConstants } from '../config/constants';
import { apiRequest } from './apiClient';
import { authService } from './authService';

type Listener = (total: number) => void;

let started = false;
let timer: ReturnType<typeof setTimeout> | null = null;
let listeners = new Set<Listener>();
let lastTotal: number | null = null;

function parseTotal(data: Record<string, unknown>): number {
  const direct = data.total;
  if (typeof direct === 'number') return Math.floor(direct);
  const web = Number(data.web ?? 0);
  const apps = Number(data.apps ?? data.android ?? 0);
  return web + apps;
}

function heartbeatDelay(): number {
  const fg = AppState.currentState === 'active';
  return fg ? AppConstants.presencePingIntervalMs : AppConstants.presenceBackgroundPingIntervalMs;
}

function scheduleNext(): void {
  if (!started) return;
  if (timer) clearTimeout(timer);
  timer = setTimeout(() => {
    void ping();
    scheduleNext();
  }, heartbeatDelay());
}

async function ping(): Promise<void> {
  try {
    const id = await authService.getDeviceId();
    if (!id) return;
    const data = await apiRequest<Record<string, unknown>>(endpoints.presence, {
      method: 'POST',
      body: JSON.stringify({ id, platform: 'app' }),
      timeoutMs: 15_000,
    });
    const total = parseTotal(data);
    if (lastTotal === total) return;
    lastTotal = total;
    listeners.forEach((fn) => fn(total));
  } catch {
    /* best-effort */
  }
}

function onAppStateChange(state: AppStateStatus): void {
  if (!started) return;
  if (state === 'active') void ping();
  scheduleNext();
}

export const presenceService = {
  subscribe(listener: Listener): () => void {
    listeners.add(listener);
    if (lastTotal != null) listener(lastTotal);
    return () => listeners.delete(listener);
  },

  start(): void {
    if (started) return;
    started = true;
    appStateSub = AppState.addEventListener('change', onAppStateChange);
    void ping();
    scheduleNext();
  },

  stop(): void {
    started = false;
    if (timer) clearTimeout(timer);
    timer = null;
    appStateSub?.remove();
    appStateSub = null;
  },
};

let appStateSub: { remove: () => void } | null = null;

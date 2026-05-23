import { API_BASE_URL, endpoints } from '../../config/api';

const CHECK_INTERVAL_MS = 45_000;
const REQUEST_TIMEOUT_MS = 5_000;

type ReachabilityListener = (ok: boolean, networkFailed: boolean) => void;

let lastOk: boolean | null = null;
let lastNetworkFailed = false;
let listeners = new Set<ReachabilityListener>();
let timer: ReturnType<typeof setInterval> | null = null;
let started = false;

async function pingHealth(): Promise<{ ok: boolean; networkFailed: boolean }> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const res = await fetch(`${API_BASE_URL}${endpoints.health}`, {
      signal: controller.signal,
      headers: { Accept: 'application/json' },
    });
    const ok = res.status >= 200 && res.status < 300;
    return { ok, networkFailed: false };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    const networkFailed =
      error instanceof TypeError ||
      /network request failed|failed to fetch|internet connection|offline/i.test(message);
    return { ok: false, networkFailed };
  } finally {
    clearTimeout(timeout);
  }
}

function emit(ok: boolean, networkFailed: boolean): void {
  if (lastOk === ok && lastNetworkFailed === networkFailed) return;
  lastOk = ok;
  lastNetworkFailed = networkFailed;
  listeners.forEach((fn) => fn(ok, networkFailed));
}

export const apiReachability = {
  subscribe(listener: ReachabilityListener): () => void {
    listeners.add(listener);
    if (lastOk != null) listener(lastOk, lastNetworkFailed);
    return () => listeners.delete(listener);
  },

  start(): void {
    if (started) return;
    started = true;
    const run = () => {
      void pingHealth().then(({ ok, networkFailed }) => emit(ok, networkFailed));
    };
    setTimeout(run, 2000);
    timer = setInterval(run, CHECK_INTERVAL_MS);
  },

  stop(): void {
    started = false;
    if (timer) clearInterval(timer);
    timer = null;
  },

  async checkNow(): Promise<boolean> {
    const { ok, networkFailed } = await pingHealth();
    emit(ok, networkFailed);
    return ok;
  },
};

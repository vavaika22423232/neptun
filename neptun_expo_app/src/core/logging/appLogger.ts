type LogCategory = 'api' | 'realtime' | 'purchase' | 'notification' | 'permission' | 'navigation' | 'storage';

const LOG_COOLDOWN_MS = 60_000;
const lastLogAt = new Map<string, number>();

function prefix(category: LogCategory): string {
  return `[NEPTUN:${category}]`;
}

function shouldEmitLog(category: LogCategory, message: string): boolean {
  const key = `${category}:${message}`;
  const now = Date.now();
  const prev = lastLogAt.get(key) ?? 0;
  if (now - prev < LOG_COOLDOWN_MS) return false;
  lastLogAt.set(key, now);
  return true;
}

/** Dev-only structured logs; production stays quiet unless explicitly enabled. */
export const appLogger = {
  error(category: LogCategory, message: string, detail?: unknown): void {
    if (!__DEV__ && !process.env.EXPO_PUBLIC_VERBOSE_LOGS) return;
    if (!shouldEmitLog(category, message)) return;
    if (detail !== undefined) {
      console.warn(prefix(category), message, detail);
    } else {
      console.warn(prefix(category), message);
    }
  },

  info(category: LogCategory, message: string): void {
    if (!__DEV__) return;
    console.log(prefix(category), message);
  },
};

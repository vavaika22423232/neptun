/**
 * Next.js Instrumentation Hook
 * Runs when the Next.js server starts.
 * Used to initialize background services.
 */
export async function register() {
  // Only run on the server
  if (process.env.NEXT_RUNTIME === 'nodejs') {
    const { startAlarmFetcher } = await import('./lib/alarm-fetcher');

    console.log('[INIT] Starting background services...');
    startAlarmFetcher();
    console.log('[INIT] Background services started');
  }
}

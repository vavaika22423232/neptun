/**
 * Next.js Instrumentation Hook
 * Runs when the Next.js server starts.
 * Used to initialize background services.
 */
export async function register() {
  // Only run on the server
  if (process.env.NEXT_RUNTIME === 'nodejs') {
    // Static generation workers: no Redis, no background timers, no external alarm API.
    if (process.env.NEXT_PHASE === 'phase-production-build') {
      console.log('[INIT] Skipping background services during Next.js production build');
      return;
    }

    const { startAlarmFetcher } = await import('@/lib/alarm-fetcher');
    const { initStore, startMarkerSync } = await import('@/lib/markers-store');

    console.log('[INIT] Starting background services...');
    await initStore();
    startMarkerSync();
    startAlarmFetcher();

    const { subscribeChatCacheInvalidation, subscribeMarkerDerivedCacheInvalidation } =
      await import('@/lib/redis');
    const { clearChatMessagesCacheLocal } = await import('@/lib/chat-messages-cache');
    const { clearMarkerDerivedApiCachesLocal } = await import('@/lib/cache');
    subscribeChatCacheInvalidation(() => clearChatMessagesCacheLocal());
    subscribeMarkerDerivedCacheInvalidation(() => clearMarkerDerivedApiCachesLocal());

    console.log('[INIT] Background services started');
  }
}

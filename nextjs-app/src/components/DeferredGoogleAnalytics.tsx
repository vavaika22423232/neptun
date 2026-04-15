'use client';

import Script from 'next/script';
import { useEffect, useState } from 'react';

const GA_ID = 'G-MW867VP8WK';

/**
 * Load gtag after window load + delay, then idle (or long timeout) so LCP/INP stay primary.
 */
export default function DeferredGoogleAnalytics() {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const w = window as Window & {
      requestIdleCallback?: (cb: () => void, opts?: { timeout: number }) => number;
      cancelIdleCallback?: (id: number) => void;
    };

    let cancelled = false;
    let loadDelayTimer: number | undefined;
    let idleId: number | undefined;
    let fallbackTimer: number | undefined;

    const run = () => {
      if (cancelled) return;
      setReady(true);
    };

    const scheduleAfterQuiet = () => {
      if (cancelled) return;
      if (typeof w.requestIdleCallback === 'function') {
        idleId = w.requestIdleCallback(run, { timeout: 8000 });
      } else {
        fallbackTimer = window.setTimeout(run, 5000);
      }
    };

    const afterLoad = () => {
      loadDelayTimer = window.setTimeout(scheduleAfterQuiet, 2000);
    };

    if (document.readyState === 'complete') {
      afterLoad();
    } else {
      window.addEventListener('load', afterLoad, { once: true });
    }

    return () => {
      cancelled = true;
      window.removeEventListener('load', afterLoad);
      if (loadDelayTimer !== undefined) window.clearTimeout(loadDelayTimer);
      if (fallbackTimer !== undefined) window.clearTimeout(fallbackTimer);
      if (idleId !== undefined) w.cancelIdleCallback?.(idleId);
    };
  }, []);

  if (!ready) return null;

  return (
    <>
      <Script src={`https://www.googletagmanager.com/gtag/js?id=${GA_ID}`} strategy="lazyOnload" />
      <Script id="ga-config-deferred" strategy="lazyOnload">
        {`
          window.dataLayer = window.dataLayer || [];
          function gtag(){dataLayer.push(arguments);}
          gtag('js', new Date());
          gtag('config', '${GA_ID}');
        `}
      </Script>
    </>
  );
}

'use client';

import { useEffect } from 'react';

const CT_ATTR = 'data-neptun-app-cta';
const STORE_ATTR = 'data-neptun-store';

declare global {
  interface Window {
    dataLayer?: unknown[];
    gtag?: (...cmd: unknown[]) => void;
  }
}

/** Той самий патерн короткого snippet, що й у Google Analytics — доки не підвантажився повний `gtag/js`. */
function ensureGtagShimMatchesGoogle() {
  if (typeof window === 'undefined') return;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- GA snippet uses `arguments`, not spread
  const w = window as any;
  w.dataLayer = w.dataLayer || [];

  if (typeof w.gtag === 'function') return;

  function gtag() {
    // eslint-disable-next-line prefer-rest-params -- must match Google's dataLayer queue format
    w.dataLayer.push(arguments);
  }
  w.gtag = gtag;
}

function inferStore(el: HTMLElement, href: string): string {
  const fromAttr = el.getAttribute(STORE_ATTR);
  if (fromAttr === 'google_play' || fromAttr === 'app_store') return fromAttr;

  const h = href.toLowerCase();
  if (h.includes('play.google.com')) return 'google_play';
  if (h.includes('apps.apple.com')) return 'app_store';
  return 'unknown';
}

/**
 * Події `neptun_app_install_click` у GA4 із параметрами `cta_slot` і `store`.
 * У Admin → Custom definitions можна додати їх як custom dimensions (подія custom).
 */
export default function NeptunAppInstallClickTracker() {
  useEffect(() => {
    ensureGtagShimMatchesGoogle();

    const onClickCapture = (e: MouseEvent) => {
      const target = e.target;
      if (!(target instanceof Element)) return;
      const el = target.closest(`a[${CT_ATTR}], button[${CT_ATTR}]`) as HTMLElement | null;
      if (!el) return;

      const slot = el.getAttribute(CT_ATTR);
      if (!slot) return;

      const href = el instanceof HTMLAnchorElement ? el.href : '';
      const store = inferStore(el, href);

      try {
        window.gtag?.('event', 'neptun_app_install_click', {
          cta_slot: slot,
          store,
        });
      } catch {
        /* ignore */
      }
    };

    document.addEventListener('click', onClickCapture, true);
    return () => document.removeEventListener('click', onClickCapture, true);
  }, []);

  return null;
}

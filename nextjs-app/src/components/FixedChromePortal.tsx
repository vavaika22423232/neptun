'use client';

import { useLayoutEffect, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

const CHROME_ROOT_ID = 'neptun-fixed-chrome';

/**
 * Renders top chrome outside Next/#__next and <main> so Leaflet/MapLibre transforms
 * and visual-viewport shifts on drag do not change the containing block for
 * position:fixed (avoids navbar/Telegram “jumping” when panning the map).
 */
export default function FixedChromePortal({ children }: { children: ReactNode }) {
  const [root, setRoot] = useState<HTMLElement | null>(null);

  useLayoutEffect(() => {
    let el = document.getElementById(CHROME_ROOT_ID) as HTMLElement | null;
    if (!el) {
      el = document.createElement('div');
      el.id = CHROME_ROOT_ID;
      el.setAttribute('data-neptun-chrome', '1');
      document.body.appendChild(el);
    }
    setRoot(el);
  }, []);

  useLayoutEffect(() => {
    if (!root) return;
    const vv = window.visualViewport;
    if (!vv) return;

    const sync = () => {
      // Pin fixed UI to the visual viewport (iOS rubber-band / dynamic toolbars).
      const y = vv.offsetTop;
      document.documentElement.style.setProperty('--neptun-vv-offset-y', `${y}px`);
    };

    sync();
    vv.addEventListener('resize', sync);
    vv.addEventListener('scroll', sync);
    return () => {
      vv.removeEventListener('resize', sync);
      vv.removeEventListener('scroll', sync);
      document.documentElement.style.removeProperty('--neptun-vv-offset-y');
    };
  }, [root]);

  if (!root) return null;
  return createPortal(children, root);
}

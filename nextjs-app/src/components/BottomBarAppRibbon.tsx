'use client';

import { useEffect, useState } from 'react';
import {
  type AppInstallAttributionSlot,
  type ClientStoreFlavor,
  detectClientStoreFlavor,
  trackedAppStoreUrl,
  trackedGooglePlayUrl,
} from '@/lib/app-download-urls';

function ctaAttrs(slot: AppInstallAttributionSlot, store: 'google_play' | 'app_store') {
  return {
    'data-neptun-app-cta': slot,
    'data-neptun-store': store,
  } as const;
}

/** Одна висота й відступи для мобільного та ПК нижнього бару */
const stripeBar =
  'flex w-full flex-nowrap items-center gap-2.5 px-4 py-1.5 transition-colors hover:bg-[var(--hud-hover)] active:bg-[var(--hud-active)]';

const btnPlay =
  'inline-flex shrink-0 items-center gap-1.5 rounded-[8px] border border-emerald-600/55 bg-emerald-500/90 px-2.5 py-1 text-[9px] font-bold uppercase tracking-[0.05em] text-black';

const btnApple =
  'inline-flex shrink-0 items-center gap-1.5 rounded-[8px] border border-white/14 bg-[color-mix(in_srgb,var(--hud-chip)_90%,transparent)] px-2.5 py-1 text-[9px] font-bold uppercase tracking-[0.05em] text-[var(--hud-text)]';

const NEPTUN_RIBBON_LOGO = '/logonep.png';

function LogoBadge() {
  return (
    // Public asset у `public/logonep.png`
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={NEPTUN_RIBBON_LOGO}
      alt="NEPTUN"
      width={56}
      height={56}
      draggable={false}
      className="h-7 w-7 shrink-0 select-none object-contain"
    />
  );
}

function SvgPlay(props: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={props.className} fill="currentColor" aria-hidden>
      <path d="M3.18 23.76c.3.17.64.22.98.14l12.35-7.12-2.61-2.61-10.72 9.59zm-1.69-20.3a1.5 1.5 0 00-.49 1.1v15.88c0 .43.18.83.49 1.1l.06.06 8.9-8.9V12.5l-8.9-8.9-.06.06zM20.4 10.34l-2.55-1.47-2.93 2.93 2.93 2.93 2.57-1.48a1.5 1.5 0 000-2.91zM4.16.38L16.51 7.5l-2.61 2.61L3.18.52a1.11 1.11 0 01.98-.14z" />
    </svg>
  );
}

function SvgApple(props: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={props.className} fill="currentColor" aria-hidden>
      <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98l-.09.06c-.22.14-2.2 1.28-2.18 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.37 2.77M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z" />
    </svg>
  );
}

function RibbonCaption() {
  return (
    <span className="flex min-w-0 flex-1 flex-col justify-center gap-px leading-snug">
      <span className="truncate text-[11px] font-bold text-[var(--hud-text)]">Додаток NEPTUN</span>
      <span className="truncate text-[10px] text-[var(--hud-muted)]">Push-тривоги та карта загроз поруч із вами</span>
    </span>
  );
}

function RibbonStoresRow({ slot, flavor }: { slot: AppInstallAttributionSlot; flavor: ClientStoreFlavor }) {
  const gp = trackedGooglePlayUrl(slot);
  const asUrl = trackedAppStoreUrl(slot);

  const rowCls = 'flex shrink-0 flex-nowrap items-center gap-1.5';

  const playBtn = (
    <a {...ctaAttrs(slot, 'google_play')} href={gp} target="_blank" rel="noopener noreferrer" className={btnPlay}>
      <SvgPlay className="h-3 w-3" />
      Google Play
    </a>
  );

  const appBtn = (
    <a {...ctaAttrs(slot, 'app_store')} href={asUrl} target="_blank" rel="noopener noreferrer" className={btnApple}>
      <SvgApple className="h-3 w-3" />
      App Store
    </a>
  );

  if (flavor === 'ios') {
    return (
      <div className={rowCls}>
        {appBtn}
        {playBtn}
      </div>
    );
  }

  return (
    <div className={rowCls}>
      {playBtn}
      {appBtn}
    </div>
  );
}

/**
 * Одна верстка стрічки додатку; `slot` різний для мобільних / десктопних UTM та аналітики.
 */
export function BottomBarAppRibbonStripe({ slot }: { slot: AppInstallAttributionSlot }) {
  const [flavor, setFlavor] = useState<ClientStoreFlavor>('unknown');
  useEffect(() => {
    setFlavor(detectClientStoreFlavor());
  }, []);

  return (
    <div className={stripeBar} aria-label="Застосунок NEPTUN у Google Play та App Store">
      <LogoBadge />
      <RibbonCaption />
      <RibbonStoresRow slot={slot} flavor={flavor} />
    </div>
  );
}

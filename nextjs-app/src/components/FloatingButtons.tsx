'use client';

import { useEffect, useState } from 'react';
import {
  trackedAppStoreUrl,
  trackedGooglePlayUrl,
  detectClientStoreFlavor,
  type ClientStoreFlavor,
} from '@/lib/app-download-urls';

interface FloatingButtonsProps {
  onDonate: () => void;
}

export default function FloatingButtons({ onDonate }: FloatingButtonsProps) {
  const [flavor, setFlavor] = useState<ClientStoreFlavor>('unknown');
  useEffect(() => {
    setFlavor(detectClientStoreFlavor());
  }, []);

  const gp = trackedGooglePlayUrl('floating');
  const asUrl = trackedAppStoreUrl('floating');
  const appHref =
    flavor === 'ios' ? asUrl : flavor === 'android' ? gp : gp;
  const label =
    flavor === 'ios' ? 'Через App Store' : flavor === 'android' ? 'Через Google Play' : 'Завантажити додаток';

  const primaryStore: 'google_play' | 'app_store' =
    flavor === 'ios' ? 'app_store' : flavor === 'android' ? 'google_play' : 'google_play';

  return (
    <div className="fixed bottom-6 right-6 z-[1100] flex flex-col gap-2.5 max-md:bottom-20 max-md:right-3">
      {/* Donate button */}
      <button
        onClick={onDonate}
        className="flex items-center justify-center gap-2 px-5 py-3 bg-[#2c2c2e] border border-white/10 rounded-full text-[13px] font-medium text-white/70 hover:bg-[#3a3a3c] hover:text-white transition-all cursor-pointer"
      >
        <span className="material-icons text-[20px]">favorite</span>
        <span className="btn-text">Підтримати</span>
      </button>

      {/* Store — primary storefront by device */}
      <a
        href={appHref}
        data-neptun-app-cta="floating"
        data-neptun-store={primaryStore}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center justify-center gap-2 px-5 py-3 bg-[#2c2c2e] border border-white/10 rounded-full text-[13px] font-medium text-white/70 hover:bg-[#3a3a3c] hover:text-white transition-all no-underline"
      >
        <span className="material-icons text-[20px]">get_app</span>
        <span className="btn-text">{label}</span>
      </a>

      {(flavor === 'ios' || flavor === 'android') && (
        <a
          href={flavor === 'ios' ? gp : asUrl}
          data-neptun-app-cta="floating"
          data-neptun-store={flavor === 'ios' ? 'google_play' : 'app_store'}
          target="_blank"
          rel="noopener noreferrer"
          className="rounded-full px-4 py-2 text-center text-[11px] font-semibold text-white/55 no-underline transition hover:text-white/90 hover:underline"
        >
          {flavor === 'ios' ? 'Google Play замість цього' : 'Версія для iPhone'}
        </a>
      )}
    </div>
  );
}

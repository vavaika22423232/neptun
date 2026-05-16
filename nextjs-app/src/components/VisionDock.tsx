'use client';

import React from 'react';
import { TELEGRAM_CHANNEL_URL } from '@/lib/constants';
import { trackedAppStoreUrl, trackedGooglePlayUrl } from '@/lib/app-download-urls';
import { glass } from '@/lib/glassSurface';

interface VisionDockProps {
  onDonate: () => void;
  onFaq: () => void;
}

export default function VisionDock({ onDonate, onFaq }: VisionDockProps) {
  return (
    <div className="fixed bottom-safe pb-6 left-1/2 -translate-x-1/2 z-[1500]">
      <div className={`p-2 flex items-center gap-3 ${glass.dock}`}>
        
        {/* Apple Icon */}
        <a href={trackedAppStoreUrl('vision_dock')} target="_blank" rel="noopener noreferrer" data-neptun-app-cta="vision_dock" data-neptun-store="app_store" className={`w-12 h-12 flex items-center justify-center ${glass.button}`}>
          <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5 opacity-80">
            <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"/>
          </svg>
        </a>

        {/* Play Icon */}
        <a href={trackedGooglePlayUrl('vision_dock')} target="_blank" rel="noopener noreferrer" data-neptun-app-cta="vision_dock" data-neptun-store="google_play" className={`w-12 h-12 flex items-center justify-center ${glass.button}`}>
          <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5 opacity-80">
            <path d="M3.609 1.814L13.792 12 3.61 22.186a.996.996 0 01-.61-.92V2.734a1 1 0 01.609-.92zm10.89 10.893l2.302 2.302-10.937 6.333 8.635-8.635zm3.199-3.199l2.302 2.302-2.302 2.302-2.698-2.698 2.698-2.698-.001.792h.001v-.792zm-3.906-3.906l10.937 6.333-2.302 2.302L13.792 5.602z"/>
          </svg>
        </a>

        {/* Telegram Icon */}
        <a href={TELEGRAM_CHANNEL_URL} target="_blank" rel="noopener noreferrer" className={`w-12 h-12 flex items-center justify-center ${glass.button}`}>
           <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5 opacity-80">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/>
          </svg>
        </a>

        {/* Divider */}
        <div className="w-px h-8 bg-white/10 mx-1"></div>

        {/* Donate Icon */}
        <button onClick={onDonate} className={`w-12 h-12 flex items-center justify-center text-[#ff2a5f] ${glass.button}`}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>
        </button>

        {/* FAQ Icon */}
        <button onClick={onFaq} className={`w-12 h-12 flex items-center justify-center opacity-80 ${glass.button}`}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5"><circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
        </button>

      </div>
    </div>
  );
}

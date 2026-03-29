'use client';

import { useEffect, useState, useRef } from 'react';

export default function DeploymentScreen() {
  const [visible, setVisible] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const abortedRef = useRef(false);

  useEffect(() => {
    abortedRef.current = false;
    let attempts = 0;

    const checkHealth = async () => {
      if (abortedRef.current) return;
      attempts++;
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);
        const res = await fetch('/api/health', {
          method: 'GET',
          cache: 'no-store',
          signal: controller.signal,
        });
        clearTimeout(timeoutId);

        if (abortedRef.current) return;

        if (res.ok) {
          setVisible(false);
          setTimeout(checkHealth, 30000);
        } else {
          setVisible(true);
          const delay = Math.min(3000 * Math.pow(1.3, Math.min(attempts, 8)), 15000);
          setTimeout(checkHealth, delay);
        }
      } catch {
        if (abortedRef.current) return;
        setVisible(true);
        const delay = Math.min(3000 * Math.pow(1.3, Math.min(attempts, 8)), 15000);
        setTimeout(checkHealth, delay);
      }
    };

    checkHealth();

    return () => {
      abortedRef.current = true;
    };
  }, []);

  useEffect(() => {
    if (visible) {
      setSeconds(0);
      intervalRef.current = setInterval(() => {
        setSeconds((s) => s + 1);
      }, 1000);
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [visible]);

  if (!visible) return null;

  return (
    <div className="fixed inset-0 z-[99999] flex flex-col items-center justify-center bg-[#050505]/90 backdrop-blur-3xl text-white selection:bg-[#ff2a5f]/30">
      
      {/* Background Radar Rings */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-20">
        <div className="w-[500px] h-[500px] rounded-full border border-white/10 absolute animate-[ping_4s_cubic-bezier(0,0,0.2,1)_infinite]" />
        <div className="w-[300px] h-[300px] rounded-full border border-white/20 absolute animate-[ping_3s_cubic-bezier(0,0,0.2,1)_infinite_0.5s]" />
      </div>

      <div className="relative z-10 flex flex-col items-center text-center max-w-[400px] px-8 py-12">
        {/* Core branding */}
        <div className="mb-8 text-2xl font-bold tracking-[0.4em] uppercase text-white shadow-[0_0_24px_rgba(255,255,255,0.2)]">
          NEPTUN
        </div>

        {/* Loading Ring */}
        <div className="relative flex h-24 w-24 items-center justify-center mb-8">
          <div className="absolute inset-0 rounded-full border-[1px] border-white/10" />
          <div className="absolute inset-0 animate-spin rounded-full border-[2px] border-t-transparent border-r-transparent border-b-[#ff2a5f] border-l-[#ff2a5f] drop-shadow-[0_0_8px_rgba(255,42,95,0.8)]" />
          <div className="text-[10px] font-bold tracking-[0.2em] text-white/50 uppercase tabular-nums">
            {seconds}s
          </div>
        </div>

        {/* Text */}
        <div className="mb-2 text-sm font-bold tracking-[0.1em] text-[#ff2a5f] uppercase animate-pulse">
          Встановлення З'єднання
        </div>
        <div className="text-[11px] font-medium tracking-widest text-white/40 uppercase">
          Оновлення топографії та радарних даних...
        </div>
      </div>
      
    </div>
  );
}

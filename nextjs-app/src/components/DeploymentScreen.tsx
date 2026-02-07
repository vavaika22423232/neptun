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
          // Keep polling every 30s to detect future deployments
          setTimeout(checkHealth, 30000);
        } else {
          // Any non-ok (502, 503, 500, etc.) — show screen and retry
          setVisible(true);
          const delay = Math.min(3000 * Math.pow(1.3, Math.min(attempts, 8)), 15000);
          setTimeout(checkHealth, delay);
        }
      } catch {
        if (abortedRef.current) return;
        // Network error or abort — show screen and retry
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

  // Second counter
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
    <div className="fixed inset-0 z-[99999] flex flex-col items-center justify-center bg-[#0a0e17] text-white">
      <div className="text-3xl font-medium tracking-[8px] mb-6 text-white/90">NEPTUN</div>
      <div className="text-lg mb-2 animate-pulse">Вносяться зміни</div>
      <div className="text-white/50 text-sm mb-4">Треба хвилинку почекати...</div>
      <div className="w-8 h-8 border-2 border-white/20 border-t-blue-500 rounded-full animate-spin" />
      <div className="mt-5 text-white/30 text-xs">
        Перевірка: {seconds} сек
      </div>
    </div>
  );
}

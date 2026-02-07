'use client';

import { useEffect, useState } from 'react';

export default function DeploymentScreen() {
  const [visible, setVisible] = useState(false);
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    let timer: ReturnType<typeof setInterval>;
    let attempts = 0;

    const checkHealth = async () => {
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

        if (res.ok) {
          setVisible(false);
        } else if (res.status === 502 || res.status === 503) {
          setVisible(true);
        }
      } catch {
        setVisible(true);
        const delay = Math.min(3000 * Math.pow(1.5, Math.min(attempts, 5)), 10000);
        setTimeout(checkHealth, delay);
      }
    };

    checkHealth();

    // Timer
    timer = setInterval(() => {
      if (visible) setSeconds((s) => s + 1);
    }, 1000);

    return () => clearInterval(timer);
  }, [visible]);

  if (!visible) return null;

  return (
    <div className="fixed inset-0 z-[99999] flex flex-col items-center justify-center bg-[#0a0e17] text-white">
      <div className="text-3xl font-medium tracking-[8px] mb-6 text-white/90">NEPTUN</div>
      <div className="text-lg mb-2 animate-pulse">🔄 Вносяться зміни</div>
      <div className="text-white/50 text-sm mb-4">Треба хвилинку почекати...</div>
      <div className="w-8 h-8 border-2 border-white/20 border-t-blue-500 rounded-full animate-spin" />
      <div className="mt-5 text-white/30 text-xs">
        Перевірка: {seconds} сек
      </div>
    </div>
  );
}

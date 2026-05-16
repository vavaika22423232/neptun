'use client';

import { useMemo, useRef, useEffect } from 'react';
import type { Alarm } from '@/types';

interface AlarmStatusBarProps {
  alarms: Alarm[];
}

const OBLAST_SHORT: Record<string, string> = {
  'Автономна Республіка Крим': 'АР Крим',
  'Вінницька область': 'Вінницька',
  'Волинська область': 'Волинська',
  'Дніпропетровська область': 'Дніпровська',
  'Донецька область': 'Донецька',
  'Житомирська область': 'Житомирська',
  'Закарпатська область': 'Закарпатська',
  'Запорізька область': 'Запорізька',
  'Івано-Франківська область': 'Ів.-Франківська',
  'Київська область': 'Київська',
  'Кіровоградська область': 'Кіровоградська',
  'Луганська область': 'Луганська',
  'Львівська область': 'Львівська',
  'Миколаївська область': 'Миколаївська',
  'Одеська область': 'Одеська',
  'Полтавська область': 'Полтавська',
  'Рівненська область': 'Рівненська',
  'Сумська область': 'Сумська',
  'Тернопільська область': 'Тернопільська',
  'Харківська область': 'Харківська',
  'Херсонська область': 'Херсонська',
  'Хмельницька область': 'Хмельницька',
  'Черкаська область': 'Черкаська',
  'Чернівецька область': 'Чернівецька',
  'Чернігівська область': 'Чернігівська',
  'місто Київ': 'Київ',
  'місто Севастополь': 'Севастополь',
};

function shortName(regionName: string | undefined): string {
  if (!regionName) return '—';
  return OBLAST_SHORT[regionName] || regionName.replace(' область', '').replace('Автономна Республіка ', '');
}

export default function AlarmStatusBar({ alarms }: AlarmStatusBarProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  const activeRegions = useMemo(
    () => alarms.filter((a) => a.regionType === 'State' && a.activeAlerts?.length > 0),
    [alarms],
  );

  const count = activeRegions.length;

  // Auto-scroll through regions
  useEffect(() => {
    const el = scrollRef.current;
    if (!el || count <= 3) return;
    let frame: number;
    let scrollX = 0;
    const speed = 0.4; // px per frame
    const animate = () => {
      scrollX += speed;
      if (scrollX >= el.scrollWidth - el.clientWidth + 2) scrollX = 0;
      el.scrollLeft = scrollX;
      frame = requestAnimationFrame(animate);
    };
    frame = requestAnimationFrame(animate);
    const stop = () => cancelAnimationFrame(frame);
    el.addEventListener('mouseenter', stop);
    el.addEventListener('touchstart', stop, { passive: true });
    return () => {
      cancelAnimationFrame(frame);
      el.removeEventListener('mouseenter', stop);
      el.removeEventListener('touchstart', stop);
    };
  }, [count]);

  if (count === 0) {
    return (
      <div className="alarm-status-bar alarm-status-bar--clear" aria-live="polite" aria-label="Статус тривог: чисто">
        <span className="alarm-status-bar__dot alarm-status-bar__dot--ok" aria-hidden />
        <span className="alarm-status-bar__label-clear">Небо чисте</span>
      </div>
    );
  }

  return (
    <div
      className="alarm-status-bar alarm-status-bar--active"
      aria-live="polite"
      aria-label={`Активні тривоги: ${count} регіонів`}
    >
      {/* Пульсуючий індикатор */}
      <span className="alarm-status-bar__dot alarm-status-bar__dot--alarm" aria-hidden />

      {/* Лічильник */}
      <span className="alarm-status-bar__count" aria-hidden>
        {count}
      </span>

      {/* Scrollable chips */}
      <div
        ref={scrollRef}
        className="alarm-status-bar__chips scrollbar-none"
        aria-hidden
      >
        {activeRegions.map((a) => (
          <span key={a.regionId} className="alarm-status-bar__chip">
            {shortName(a.regionName)}
          </span>
        ))}
        {/* Duplicate for seamless loop */}
        {count > 3 && activeRegions.map((a) => (
          <span key={`d_${a.regionId}`} className="alarm-status-bar__chip" aria-hidden>
            {shortName(a.regionName)}
          </span>
        ))}
      </div>
    </div>
  );
}

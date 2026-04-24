'use client';

/**
 * Декоративний шар поверх тайлів карти, під HUD (z нижче панелей).
 * Без великих blur-фільтрів — лише градієнти / inset-тінь / лінії.
 */
export default function MapAtmosphereOverlay() {
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-0 z-[1990] overflow-hidden"
    >
      {/* Краєва затемнення — «об’єктив» */}
      <div
        className="absolute inset-0
          shadow-[inset_0_0_100px_rgba(15,23,42,0.18),inset_0_-40px_80px_rgba(15,23,42,0.12)]
          dark:shadow-[inset_0_0_120px_rgba(0,0,0,0.55),inset_0_-50px_100px_rgba(0,0,0,0.35)]"
      />
      {/* Кольори по боках — не в центрі мапи */}
      <div
        className="absolute inset-0
          bg-[radial-gradient(ellipse_65%_115%_at_-5%_45%,rgba(58,158,253,0.11)_0%,transparent_55%),radial-gradient(ellipse_60%_110%_at_105%_52%,rgba(99,102,241,0.07)_0%,transparent_52%)]
          dark:bg-[radial-gradient(ellipse_58%_120%_at_-8%_42%,rgba(255,42,95,0.09)_0%,transparent_54%),radial-gradient(ellipse_58%_120%_at_108%_58%,rgba(105,240,174,0.075)_0%,transparent_54%)]"
      />
      {/* Дуже легка «сітка радару» */}
      <div
        className="absolute inset-0 opacity-[0.04]
          dark:opacity-[0.07]
          bg-[repeating-linear-gradient(0deg,transparent,transparent_3px,rgba(15,23,42,0.12)_3px,rgba(15,23,42,0.12)_4px)]
          dark:bg-[repeating-linear-gradient(0deg,transparent,transparent_3px,rgba(255,255,255,0.06)_3px,rgba(255,255,255,0.06)_4px)]"
      />
      <div
        className="absolute inset-0 opacity-[0.022] dark:opacity-[0.04]
          bg-[repeating-linear-gradient(90deg,transparent,transparent_6px,rgba(15,23,42,0.09)_6px,rgba(15,23,42,0.09)_7px)]
          dark:bg-[repeating-linear-gradient(90deg,transparent,transparent_6px,rgba(255,255,255,0.05)_6px,rgba(255,255,255,0.05)_7px)]"
      />
    </div>
  );
}

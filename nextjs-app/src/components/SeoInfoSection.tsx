'use client';

import { useEffect, useRef } from 'react';
import Link from 'next/link';
import { TELEGRAM_CHANNEL_URL } from '@/lib/constants';

interface SeoInfoSectionProps {
  isOpen: boolean;
  onClose: () => void;
}

const REGION_LINKS = [
  { slug: 'kyiv', name: 'Київ' },
  { slug: 'kyivska', name: 'Київська' },
  { slug: 'kharkivska', name: 'Харківська' },
  { slug: 'odeska', name: 'Одеська' },
  { slug: 'dnipropetrovska', name: 'Дніпропетровська' },
  { slug: 'zaporizka', name: 'Запорізька' },
  { slug: 'lvivska', name: 'Львівська' },
  { slug: 'mykolaivska', name: 'Миколаївська' },
  { slug: 'khersonska', name: 'Херсонська' },
  { slug: 'poltavska', name: 'Полтавська' },
  { slug: 'vinnytska', name: 'Вінницька' },
  { slug: 'sumska', name: 'Сумська' },
  { slug: 'chernihivska', name: 'Чернігівська' },
  { slug: 'zhytomyrska', name: 'Житомирська' },
  { slug: 'cherkaska', name: 'Черкаська' },
  { slug: 'rivnenska', name: 'Рівненська' },
  { slug: 'volynska', name: 'Волинська' },
  { slug: 'ternopilska', name: 'Тернопільська' },
  { slug: 'ivano-frankivska', name: 'Івано-Франківська' },
  { slug: 'zakarpatska', name: 'Закарпатська' },
  { slug: 'chernivetska', name: 'Чернівецька' },
  { slug: 'khmelnytska', name: 'Хмельницька' },
  { slug: 'kirovohradska', name: 'Кіровоградська' },
  { slug: 'donetska', name: 'Донецька' },
  { slug: 'luhanska', name: 'Луганська' },
];

const FAQ_ITEMS = [
  {
    q: 'Що таке NEPTUN?',
    a: 'NEPTUN — безкоштовна інтерактивна карта шахедів і повітряних тривог України в реальному часі. Відстежує шахеди, ракети, БПЛА та КАБ 24/7.',
  },
  {
    q: 'Де подивитися карту шахедів онлайн?',
    a: 'Карта шахедів і тривог України доступна на neptun.in.ua — інтерактивна карта повітряних тривог в реальному часі по всіх областях.',
  },
  {
    q: 'Як часто оновлюються дані?',
    a: 'Дані оновлюються кілька разів на хвилину. Ви бачите актуальну ситуацію з мінімальною затримкою в режимі реального часу.',
  },
  {
    q: 'Чим відрізняється карта шахедів від карти тривог?',
    a: 'Карта тривог показує активні сирени по регіонах. Карта шахедів показує рух БПЛА, маршрути та напрямок польоту — разом це повна картина загроз.',
  },
  {
    q: 'Чи є мобільний додаток?',
    a: 'Так, додаток NEPTUN доступний безкоштовно в Google Play з push-сповіщеннями про тривоги у вашому регіоні.',
  },
  {
    q: 'Чи є карта офіційною?',
    a: 'Ні. У разі реальної загрози — використовуйте офіційний застосунок «Повітряна тривога». NEPTUN збирає дані з публічних відкритих джерел.',
  },
  {
    q: 'Що означають стрілки та лінії на карті?',
    a: 'Прогнозовані та поточні вектори руху цілей: балістичних ракет, крилатих ракет, шахедів та авіації.',
  },
  {
    q: 'Як отримати push-сповіщення?',
    a: 'Завантажте NEPTUN з Google Play, встановіть свій регіон — і отримуйте миттєві сповіщення про тривоги у вашій області.',
  },
];

const POPULAR_SEARCH_LINKS = [
  { label: 'Карта тривог', href: '/' },
  { label: 'Карта шахедів', href: '/karta-shahediv' },
  { label: 'Нептун карта', href: '/' },
  { label: 'Тривога', href: '/tryvoga-zaraz' },
  { label: 'Повітряна тривога', href: '/povitryana-tryvoga' },
  { label: 'Мапа тривог', href: '/karta-tryvoh' },
  { label: 'Карта повітряних тривог', href: '/karta-tryvoh' },
  { label: 'Карта шахедов', href: '/karta-shahediv' },
  { label: 'Карта NEPTUN', href: '/' },
];

export default function SeoInfoSection({ isOpen, onClose }: SeoInfoSectionProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [isOpen, onClose]);

  useEffect(() => {
    document.body.style.overflow = isOpen ? 'hidden' : '';
    return () => { document.body.style.overflow = ''; };
  }, [isOpen]);

  useEffect(() => {
    if (isOpen && scrollRef.current) scrollRef.current.scrollTop = 0;
  }, [isOpen]);

  return (
    <>
      {/* Backdrop */}
      <div
        aria-hidden={!isOpen}
        onClick={onClose}
        className={`fixed inset-0 z-[9000] bg-[var(--hud-backdrop)] backdrop-blur-sm transition-opacity duration-300 ${isOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'}`}
      />

      {/* Sheet — bottom on mobile, centered modal on sm+ */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="info-title"
        aria-hidden={!isOpen}
        className={`fixed inset-x-0 bottom-0 z-[9100] transition-transform duration-500 ease-[cubic-bezier(0.22,1,0.36,1)]
          sm:inset-0 sm:flex sm:items-center sm:justify-center sm:p-6
          ${isOpen ? 'translate-y-0 pointer-events-auto' : 'translate-y-full sm:translate-y-0 pointer-events-none'}
        `}
      >
        <div
          className={`relative w-full overflow-hidden rounded-t-[28px] border border-[color:var(--hud-border)] bg-[var(--hud-surface-strong)] shadow-[var(--hud-modal-shadow)] backdrop-blur-2xl transition-[opacity,transform] duration-500 ease-[cubic-bezier(0.22,1,0.36,1)]
            sm:max-w-2xl sm:rounded-[28px]
            max-h-[92dvh] sm:max-h-[88dvh]
            ${isOpen ? 'opacity-100 sm:scale-100' : 'opacity-0 sm:scale-[0.96]'}
          `}
          onClick={e => e.stopPropagation()}
        >
          {/* Drag pill — mobile only */}
          <div className="mx-auto mt-3 h-1 w-9 rounded-full bg-[var(--hud-divider)] sm:hidden" />

          {/* ── SCROLLABLE BODY ── */}
          <div ref={scrollRef} className="overflow-y-auto overscroll-contain scrollbar-none max-h-[90dvh] sm:max-h-[88dvh]">

            {/* ── HEADER ── */}
            <div className="sticky top-0 z-10 flex items-center gap-4 border-b border-[color:var(--hud-border)] bg-[var(--hud-surface-strong)] px-5 py-4 backdrop-blur-xl sm:px-7">
              <div className="flex-1 min-w-0">
                <p className="text-[10px] font-black uppercase tracking-[0.3em] text-[var(--hud-danger)]">neptun.in.ua</p>
                <h2 id="info-title" className="truncate text-[18px] font-black tracking-tight text-[var(--hud-text)] sm:text-xl">
                  Про NEPTUN / FAQ
                </h2>
              </div>
              <button
                onClick={onClose}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[var(--hud-chip)] text-[var(--hud-muted)] transition-colors hover:bg-[var(--hud-hover)] hover:text-[var(--hud-text)]"
                aria-label="Закрити"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="h-4 w-4">
                  <path d="M18 6 6 18M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="px-5 py-5 sm:px-7 sm:py-6 space-y-6">

              {/* ── ABOUT ── */}
              <div className="rounded-[20px] bg-[var(--hud-chip)] p-5 sm:p-6">
                <div className="mb-3 flex items-center gap-2">
                  <span className="flex h-2 w-2 rounded-full bg-[var(--hud-danger)] shadow-[0_0_6px_var(--hud-danger)]" />
                  <span className="text-[10px] font-black uppercase tracking-[0.22em] text-[var(--hud-danger)]">Live моніторинг</span>
                </div>
                <p className="text-[13px] leading-relaxed text-[var(--hud-muted)]">
                  <strong className="font-bold text-[var(--hud-text)]">NEPTUN</strong> — найшвидша{' '}
                  <strong className="font-semibold text-[var(--hud-text)]">карта тривог і шахедів України</strong> онлайн.
                  Відстежуйте повітряні тривоги, БПЛА, ракети та КАБ в реальному часі.
                  Дані оновлюються кожні кілька секунд, 24/7.
                </p>

                {/* Stats */}
                <div className="mt-5 grid grid-cols-3 gap-2">
                  {[
                    { v: '25', l: 'областей' },
                    { v: '~5с', l: 'оновлення' },
                    { v: '24/7', l: 'без перерв' },
                  ].map(({ v, l }) => (
                    <div key={l} className="flex flex-col items-center gap-0.5 rounded-[14px] bg-[var(--hud-hover)] py-3.5 text-center">
                      <span className="text-[18px] font-black tabular-nums text-[var(--hud-text)]">{v}</span>
                      <span className="text-[10px] text-[var(--hud-muted)]">{l}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* ── WHAT WE TRACK ── */}
              <div>
                <p className="mb-3 text-[10px] font-black uppercase tracking-[0.22em] text-[var(--hud-muted)]">Що відстежує система</p>
                <div className="flex flex-wrap gap-2">
                  {[
                    { label: 'Шахеди / БПЛА', color: 'var(--hud-danger)' },
                    { label: 'Крилаті ракети', color: 'var(--hud-danger)' },
                    { label: 'Балістика', color: '#f97316' },
                    { label: 'КАБ', color: '#f97316' },
                    { label: 'Авіація', color: '#eab308' },
                    { label: 'Повітряні тривоги', color: '#22c55e' },
                    { label: 'Push-сповіщення', color: '#3b82f6' },
                    { label: 'Траєкторії польоту', color: '#a78bfa' },
                  ].map(({ label, color }) => (
                    <div
                      key={label}
                      className="flex items-center gap-2 rounded-full border border-[color:var(--hud-border)] bg-[var(--hud-chip)] px-3 py-1.5 text-[11px] font-medium text-[var(--hud-text)]"
                    >
                      <span className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ backgroundColor: color, boxShadow: `0 0 5px ${color}` }} />
                      {label}
                    </div>
                  ))}
                </div>
              </div>

              {/* ── FAQ ── */}
              <div>
                <p className="mb-3 text-[10px] font-black uppercase tracking-[0.22em] text-[var(--hud-muted)]">Часті питання</p>
                <div className="flex flex-col gap-2">
                  {FAQ_ITEMS.map((item, i) => (
                    <details
                      key={i}
                      className="group rounded-[16px] border border-[color:var(--hud-border)] bg-[var(--hud-chip)] transition-colors hover:bg-[var(--hud-hover)] open:bg-[var(--hud-hover)]"
                    >
                      <summary className="flex cursor-pointer list-none items-center gap-3.5 px-4 py-3.5">
                        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-[6px] bg-[var(--hud-active)] text-[10px] font-black tabular-nums text-[var(--hud-muted)]">
                          {i + 1}
                        </span>
                        <span className="flex-1 text-[12px] font-semibold leading-snug text-[var(--hud-text)]">{item.q}</span>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4 shrink-0 text-[var(--hud-muted)] transition-transform duration-200 group-open:rotate-180">
                          <polyline points="6 9 12 15 18 9" />
                        </svg>
                      </summary>
                      <div className="px-4 pb-4 pl-[3.375rem] text-[12px] leading-relaxed text-[var(--hud-muted)]">
                        {item.a}
                      </div>
                    </details>
                  ))}
                </div>
              </div>

              {/* ── POPULAR SEARCH INTENTS ── */}
              <div>
                <p className="mb-3 text-[10px] font-black uppercase tracking-[0.22em] text-[var(--hud-muted)]">Популярні запити</p>
                <nav aria-label="Популярні пошукові запити NEPTUN" className="flex flex-wrap gap-1.5">
                  {POPULAR_SEARCH_LINKS.map(({ label, href }) => (
                    <Link
                      key={`${href}-${label}`}
                      href={href}
                      className="rounded-[8px] border border-[color:var(--hud-border)] bg-[var(--hud-chip)] px-2.5 py-1.5 text-[11px] font-medium text-[var(--hud-muted)] transition-colors hover:border-[color:var(--hud-divider)] hover:text-[var(--hud-text)]"
                    >
                      {label}
                    </Link>
                  ))}
                </nav>
              </div>

              {/* ── REGIONS ── */}
              <div>
                <p className="mb-3 text-[10px] font-black uppercase tracking-[0.22em] text-[var(--hud-muted)]">Моніторинг по регіонах</p>
                <nav aria-label="Регіональні карти тривог" className="flex flex-wrap gap-1.5">
                  {REGION_LINKS.map(({ slug, name }) => (
                    <Link
                      key={slug}
                      href={`/region/${slug}`}
                      className="rounded-[8px] border border-[color:var(--hud-border)] bg-[var(--hud-chip)] px-2.5 py-1.5 text-[11px] font-medium text-[var(--hud-muted)] transition-colors hover:border-[color:var(--hud-divider)] hover:text-[var(--hud-text)]"
                    >
                      {name}
                    </Link>
                  ))}
                </nav>
              </div>

              {/* ── CTA ── */}
              <div className="flex flex-col gap-3 sm:flex-row pb-2">
                <a
                  href={TELEGRAM_CHANNEL_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex flex-1 items-center justify-center gap-2.5 rounded-[14px] bg-[var(--hud-text)] py-3.5 text-[11px] font-black uppercase tracking-[0.16em] text-[var(--hud-surface-strong)] transition-opacity hover:opacity-85"
                >
                  <svg viewBox="0 0 24 24" className="h-4 w-4 shrink-0" fill="currentColor">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z" />
                  </svg>
                  Telegram канал
                </a>
                <a
                  href="https://play.google.com/store/apps/details?id=com.neptunalarm.neptun_alarm_app"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex flex-1 items-center justify-center gap-2.5 rounded-[14px] border border-[color:var(--hud-border)] bg-[var(--hud-chip)] py-3.5 text-[11px] font-black uppercase tracking-[0.16em] text-[var(--hud-text)] transition-colors hover:bg-[var(--hud-hover)]"
                >
                  <svg viewBox="0 0 24 24" className="h-4 w-4 shrink-0" fill="currentColor">
                    <path d="M3.18 23.76c.3.17.64.22.98.14l12.35-7.12-2.61-2.61-10.72 9.59zm-1.69-20.3a1.5 1.5 0 00-.49 1.1v15.88c0 .43.18.83.49 1.1l.06.06 8.9-8.9V12.5l-8.9-8.9-.06.06zM20.4 10.34l-2.55-1.47-2.93 2.93 2.93 2.93 2.57-1.48a1.5 1.5 0 000-2.91zM4.16.38L16.51 7.5l-2.61 2.61L3.18.52a1.11 1.11 0 01.98-.14z" />
                  </svg>
                  Google Play
                </a>
              </div>

              {/* ── SEO FOOTER LINKS ── */}
              <div className="flex flex-wrap gap-x-5 gap-y-2 border-t border-[color:var(--hud-border)] pt-4 text-[11px] text-[var(--hud-muted)]">
                <Link href="/about" className="transition-colors hover:text-[var(--hud-text)]">Проєкт</Link>
                <Link href="/faq" className="transition-colors hover:text-[var(--hud-text)]">FAQ</Link>
                <Link href="/karta-tryvoh" className="transition-colors hover:text-[var(--hud-text)]">Карта тривог</Link>
                <Link href="/karta-shahediv" className="transition-colors hover:text-[var(--hud-text)]">Карта шахедів</Link>
                <Link href="/radar-shahediv" className="transition-colors hover:text-[var(--hud-text)]">Радар шахедів</Link>
                <Link href="/tryvoga-zaraz" className="transition-colors hover:text-[var(--hud-text)]">Тривога зараз</Link>
                <span className="ml-auto text-[10px] text-[var(--hud-muted)] opacity-50">NEPTUN © {new Date().getFullYear()}</span>
              </div>

            </div>
          </div>
        </div>
      </div>
    </>
  );
}

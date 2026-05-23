'use client';

import { useCallback, useEffect, useId, useRef, useState } from 'react';
import Link from 'next/link';
import type { Alarm } from '@/types';
import type { PlaceSearchResult } from '@/lib/places-search/types';
import { placeTypeLabelUk } from '@/lib/places-search/place-type';
import { isPlaceOblastInAlarm } from '@/lib/places-search/alarm-active';
import { dispatchNeptunMapGoto } from '@/lib/map/map-goto-bus';
import { flyToZoomForPlaceType } from '@/lib/places-search/fly-to-zoom';

const RECENT_KEY = 'neptun:recent-places';
const RECENT_MAX = 8;

function loadRecent(): PlaceSearchResult[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(RECENT_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as PlaceSearchResult[];
    return Array.isArray(parsed) ? parsed.slice(0, RECENT_MAX) : [];
  } catch {
    return [];
  }
}

function saveRecent(place: PlaceSearchResult) {
  const prev = loadRecent().filter((p) => p.id !== place.id);
  const next = [place, ...prev].slice(0, RECENT_MAX);
  localStorage.setItem(RECENT_KEY, JSON.stringify(next));
}

interface PlaceSearchProps {
  alarms: Alarm[];
  className?: string;
  initialQuery?: string;
  onQueryConsumed?: () => void;
}

export default function PlaceSearch({
  alarms,
  className = '',
  initialQuery,
  onQueryConsumed,
}: PlaceSearchProps) {
  const listId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<PlaceSearchResult[]>([]);
  const [recent, setRecent] = useState<PlaceSearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [mobileOpen, setMobileOpen] = useState(false);

  const displayList = query.trim().length >= 2 ? results : recent;

  const flyToPlace = useCallback((place: PlaceSearchResult) => {
    dispatchNeptunMapGoto({
      lat: place.lat,
      lng: place.lng,
      zoom: flyToZoomForPlaceType(place.placeType),
      duration: 1400,
      label: place.name,
    });
  }, []);

  const goToPlace = useCallback(
    (place: PlaceSearchResult) => {
      saveRecent(place);
      setRecent(loadRecent());
      setQuery(place.name);
      setOpen(false);
      setMobileOpen(false);
      flyToPlace(place);
    },
    [flyToPlace],
  );

  useEffect(() => {
    setRecent(loadRecent());
  }, []);

  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) {
      setResults([]);
      setLoading(false);
      setError(null);
      return;
    }

    const ac = new AbortController();
    setLoading(true);
    setError(null);
    const t = window.setTimeout(() => {
      fetch(`/api/places/search?q=${encodeURIComponent(q)}&limit=10`, {
        signal: ac.signal,
      })
        .then(async (r) => {
          if (!r.ok) {
            const body = await r.json().catch(() => ({}));
            throw new Error(body.error || 'Пошук недоступний');
          }
          return r.json() as Promise<{ results: PlaceSearchResult[] }>;
        })
        .then((data) => {
          setResults(data.results ?? []);
          setActiveIndex(data.results?.length ? 0 : -1);
        })
        .catch((err: Error) => {
          if (err.name === 'AbortError') return;
          setResults([]);
          setError(err.message || 'Помилка пошуку');
        })
        .finally(() => setLoading(false));
    }, 250);

    return () => {
      ac.abort();
      window.clearTimeout(t);
    };
  }, [query]);

  const goToPlaceRef = useRef(goToPlace);
  goToPlaceRef.current = goToPlace;

  useEffect(() => {
    if (!initialQuery || initialQuery.trim().length < 2) return;
    let cancelled = false;
    setQuery(initialQuery);
    setOpen(true);
    fetch(`/api/places/search?q=${encodeURIComponent(initialQuery.trim())}&limit=8`)
      .then((r) => r.json())
      .then((data: { results: PlaceSearchResult[] }) => {
        if (cancelled) return;
        const list = data.results ?? [];
        setResults(list);
        if (list[0]) goToPlaceRef.current(list[0]);
        onQueryConsumed?.();
      })
      .catch(() => {
        if (!cancelled) onQueryConsumed?.();
      });
    return () => {
      cancelled = true;
    };
  }, [initialQuery, onQueryConsumed]);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [open]);

  const onFocusEmpty = useCallback(() => {
    setOpen(true);
    if (query.trim().length < 2 && !recent.length) {
      setLoading(true);
      fetch('/api/places/search?popular=1')
        .then((r) => r.json())
        .then((data: { results: PlaceSearchResult[] }) => {
          setRecent(data.results?.length ? data.results : loadRecent());
        })
        .finally(() => setLoading(false));
    }
  }, [query, recent.length]);

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (!open || !displayList.length) {
      if (e.key === 'Escape') setOpen(false);
      return;
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex((i) => Math.min(displayList.length - 1, i + 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex((i) => Math.max(0, i - 1));
    } else if (e.key === 'Enter' && activeIndex >= 0) {
      e.preventDefault();
      goToPlace(displayList[activeIndex]);
    } else if (e.key === 'Escape') {
      setOpen(false);
    }
  };

  const panel = (
    <div
      ref={rootRef}
      className={`relative ${className}`}
      role="search"
    >
      <div className="flex h-11 items-center gap-2.5 rounded-full border border-[color:var(--hud-border)] bg-[var(--hud-surface)] px-3.5 shadow-[var(--hud-shadow)] backdrop-blur-2xl sm:gap-3 sm:px-4">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4 shrink-0 text-[var(--hud-muted)]" aria-hidden>
          <circle cx="11" cy="11" r="7" />
          <path d="M20 20l-3-3" strokeLinecap="round" />
        </svg>
        <input
          ref={inputRef}
          type="search"
          enterKeyHint="search"
          autoComplete="off"
          aria-label="Пошук міста або села"
          aria-expanded={open}
          aria-controls={listId}
          aria-activedescendant={activeIndex >= 0 ? `${listId}-opt-${activeIndex}` : undefined}
          placeholder="Місто, село…"
          className="h-full min-w-0 flex-1 bg-transparent text-[13px] text-[var(--hud-text)] placeholder:text-[var(--hud-muted)] focus:outline-none sm:text-[14px]"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={onFocusEmpty}
          onKeyDown={onKeyDown}
        />
        {loading ? (
          <span className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-[var(--hud-muted)] border-t-transparent" aria-hidden />
        ) : null}
      </div>

      {open && (displayList.length > 0 || error || (query.trim().length >= 2 && !loading)) ? (
        <ul
          id={listId}
          role="listbox"
          className="absolute left-0 right-0 top-[calc(100%+6px)] z-[3000] max-h-[min(320px,50vh)] overflow-y-auto rounded-[14px] border border-[color:var(--hud-border)] bg-[var(--hud-surface-strong)] py-1 shadow-[var(--hud-modal-shadow)] backdrop-blur-2xl"
        >
          {query.trim().length < 2 && recent.length > 0 ? (
            <li className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-[var(--hud-muted)]">
              Популярні / недавні
            </li>
          ) : null}
          {error ? (
            <li className="px-3 py-2 text-[12px] text-[var(--hud-danger)]">{error}</li>
          ) : null}
          {!error && displayList.length === 0 && query.trim().length >= 2 && !loading ? (
            <li className="px-3 py-2 text-[12px] text-[var(--hud-muted)]">Нічого не знайдено</li>
          ) : null}
          {displayList.map((place, idx) => {
            const alarm = isPlaceOblastInAlarm(alarms, place.oblastHasc, place.subtitle);
            return (
              <li key={place.id} role="option" id={`${listId}-opt-${idx}`} aria-selected={idx === activeIndex}>
                <button
                  type="button"
                  className={`flex w-full items-start gap-2 px-3 py-2.5 text-left transition-colors hover:bg-[var(--hud-hover)] ${
                    idx === activeIndex ? 'bg-[var(--hud-hover)]' : ''
                  }`}
                  onMouseEnter={() => setActiveIndex(idx)}
                  onClick={() => goToPlace(place)}
                >
                  <span className="min-w-0 flex-1">
                    <span className="block text-[13px] font-semibold text-[var(--hud-text)]">{place.name}</span>
                    <span className="block truncate text-[11px] text-[var(--hud-muted)]">{place.subtitle}</span>
                    <span className="mt-0.5 block text-[10px] text-[var(--hud-muted)]">
                      {placeTypeLabelUk(place.placeType)}
                    </span>
                  </span>
                  {alarm ? (
                    <span className="shrink-0 rounded-full bg-[var(--hud-danger-bg)] px-2 py-0.5 text-[9px] font-bold uppercase text-[var(--hud-danger)]">
                      Тривога
                    </span>
                  ) : null}
                </button>
                {place.slug ? (
                  <div className="border-t border-[color:var(--hud-border)] px-3 py-1">
                    <Link
                      href={`/city/${place.slug}`}
                      className="text-[10px] font-semibold text-[#3b82f6] hover:underline"
                      onClick={() => setOpen(false)}
                    >
                      Детальніше →
                    </Link>
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );

  return (
    <>
      <div className="hidden sm:block">{panel}</div>
      <div className="sm:hidden">
        {!mobileOpen ? (
          <button
            type="button"
            aria-label="Пошук населеного пункту"
            className="hud-top-icon-btn cinematic-button"
            onClick={() => {
              setMobileOpen(true);
              window.setTimeout(() => inputRef.current?.focus(), 50);
            }}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4" aria-hidden>
              <circle cx="11" cy="11" r="7" />
              <path d="M20 20l-3-3" strokeLinecap="round" />
            </svg>
          </button>
        ) : (
          <div className="pointer-events-auto fixed inset-x-3 top-[calc(env(safe-area-inset-top,0px)+0.5rem)] z-[2470]">
            <div className="mb-2 flex justify-end">
              <button
                type="button"
                aria-label="Закрити пошук"
                className="rounded-full cinematic-button px-3 py-1.5 text-[12px] font-semibold"
                onClick={() => setMobileOpen(false)}
              >
                Закрити
              </button>
            </div>
            {panel}
          </div>
        )}
      </div>
    </>
  );
}

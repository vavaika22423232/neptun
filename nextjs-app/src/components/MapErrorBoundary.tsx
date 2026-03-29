'use client';

import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
}

/**
 * Isolates Leaflet / map failures so the rest of the homepage (navbar, SEO, alarms) stays usable.
 */
export default class MapErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[MapErrorBoundary]', error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <div className="w-full h-full min-h-[200px] flex flex-col items-center justify-center gap-3 bg-[var(--surface-dim)] text-[var(--on-surface-variant)] px-6 text-center">
            <p className="text-sm font-medium text-[var(--on-surface)]">Не вдалося завантажити карту</p>
            <p className="text-xs max-w-sm">Спробуйте оновити сторінку. Тривоги та інші розділи сайту працюють.</p>
            <button
              type="button"
              className="mt-2 px-4 py-2 rounded-xl text-sm font-medium bg-[color-mix(in_srgb,var(--primary)_18%,transparent)] text-[var(--primary)] border border-[color-mix(in_srgb,var(--primary)_35%,transparent)] hover:bg-[color-mix(in_srgb,var(--primary)_28%,transparent)]"
              onClick={() => window.location.reload()}
            >
              Оновити сторінку
            </button>
          </div>
        )
      );
    }
    return this.props.children;
  }
}

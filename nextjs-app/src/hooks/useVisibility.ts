'use client';

import { useState, useEffect, useCallback } from 'react';

/**
 * Hook that tracks page visibility.
 * Returns true when the tab is visible, false when hidden.
 * Also provides isMobile detection for different polling intervals.
 */
export function useVisibility() {
  const [isVisible, setIsVisible] = useState(true);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    // Detect mobile
    setIsMobile(/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent));

    const handleVisibilityChange = () => {
      setIsVisible(!document.hidden);
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, []);

  return { isVisible, isMobile };
}

/**
 * Hook that polls a function at different intervals based on tab visibility.
 */
export function usePolling(
  callback: () => void | Promise<void>,
  activeInterval: number,
  hiddenInterval: number,
  enabled: boolean = true
) {
  const { isVisible } = useVisibility();

  useEffect(() => {
    if (!enabled) return;

    const interval = isVisible ? activeInterval : hiddenInterval;

    // Fetch immediately when becoming visible
    if (isVisible) {
      callback();
    }

    const id = setInterval(callback, interval);
    return () => clearInterval(id);
  }, [isVisible, activeInterval, hiddenInterval, enabled, callback]);
}

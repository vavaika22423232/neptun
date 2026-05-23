import { router } from 'expo-router';
import { toExpoHref } from './routePaths';

const TAB_ROOTS = new Set([
  '/(tabs)',
  '/(tabs)/',
  '/(tabs)/index',
  '/(tabs)/radar',
  '/(tabs)/chat',
  '/(tabs)/profile',
  '/(tabs)/regions',
]);

function isTabHref(href: string): boolean {
  return TAB_ROOTS.has(href) || href.startsWith('/(tabs)/');
}

/** Navigate using Flutter-parity path constants. */
export function navigateToFlutterPath(path: string, opts?: { replace?: boolean }): void {
  navigateToHref(toExpoHref(path), opts);
}

/** Deep links and push targets should replace tab routes to avoid stack clutter. */
export function navigateToHref(href: string, opts?: { replace?: boolean }): void {
  const replace = opts?.replace ?? isTabHref(href);
  if (replace) {
    router.replace(href as never);
  } else {
    router.push(href as never);
  }
}

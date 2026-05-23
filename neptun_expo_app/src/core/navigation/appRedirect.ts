import { RoutePaths } from './routePaths';
import { redirectFromWidgetUri } from './pushDeepLink';
import { toExpoHref } from './routePaths';

/**
 * Mirrors Flutter `resolveAppRedirect` — returns Expo Router href or null.
 */
export function resolveAppRedirectExpoHref(params: {
  isFirstLaunch: boolean;
  pathname: string;
  deepLinkUri?: string | null;
}): string | null {
  const location = params.pathname || '/';

  if (params.isFirstLaunch && !location.startsWith('/onboarding')) {
    return '/onboarding';
  }
  if (!params.isFirstLaunch && location.startsWith('/onboarding')) {
    return '/(tabs)';
  }
  if (location === '/regions' || location.endsWith('/regions')) {
    return '/(tabs)/regions';
  }

  if (params.deepLinkUri) {
    const widgetPath = redirectFromWidgetUri(params.deepLinkUri);
    if (widgetPath) return toExpoHref(widgetPath);
  }

  return null;
}

/** Flutter-path strings for unit tests (parity with `app_redirect.dart`). */
export function resolveAppRedirect(params: {
  isFirstLaunch: boolean;
  location: string;
  uri: string;
}): string | null {
  if (params.isFirstLaunch && params.location !== RoutePaths.onboarding) {
    return RoutePaths.onboarding;
  }
  if (!params.isFirstLaunch && params.location === RoutePaths.onboarding) {
    return RoutePaths.home;
  }
  if (params.location === '/regions') {
    return RoutePaths.alerts;
  }
  return redirectFromWidgetUri(params.uri);
}

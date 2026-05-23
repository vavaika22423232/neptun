import { RoutePaths } from './routePaths';
import { toExpoHref } from './routePaths';

export type PushPayload = Record<string, unknown>;

/** Maps FCM / local notification payload → route (Flutter `PushDeepLink.routeFromData`). */
export function routeFromPushData(data: PushPayload): string {
  const payload = String(data.payload ?? '').toLowerCase().trim();
  if (payload === 'briefing') {
    return RoutePaths.briefing;
  }

  const action = String(data.action ?? data.type ?? data.screen ?? '')
    .toLowerCase()
    .trim();

  switch (action) {
    case 'open_chat':
    case 'chat':
    case 'message':
      return RoutePaths.chat;
    case 'open_radar':
    case 'radar':
    case 'threat':
    case 'track':
      return RoutePaths.radar;
    case 'open_alerts':
    case 'alerts':
    case 'regions':
    case 'region':
      return RoutePaths.alerts;
    case 'open_map':
    case 'map':
    case 'threat_marker':
      return RoutePaths.home;
    case 'radar_full':
    case 'dashboard':
      return RoutePaths.radarFull;
    case 'briefing':
      return RoutePaths.briefing;
    case 'sos':
      return RoutePaths.home;
    default:
      break;
  }

  if (data.track_id != null || data.lat != null || data.lng != null || data.threat_type != null) {
    return RoutePaths.home;
  }

  return RoutePaths.home;
}

export function expoHrefFromPushData(data: PushPayload): string {
  return toExpoHref(routeFromPushData(data));
}

/** `neptun://alarm?open=radar` from home screen widget. */
export function redirectFromWidgetUri(uri: string): string | null {
  try {
    const parsed = new URL(uri);
    const scheme = parsed.protocol.replace(':', '');
    if (scheme !== 'neptun') return null;
    const open = parsed.searchParams.get('open')?.toLowerCase();
    switch (open) {
      case 'radar':
        return RoutePaths.radar;
      case 'chat':
        return RoutePaths.chat;
      case 'alerts':
      case 'regions':
        return RoutePaths.alerts;
      case 'map':
      case null:
        return RoutePaths.home;
      default:
        return RoutePaths.home;
    }
  } catch {
    return null;
  }
}

export function expoHrefFromWidgetUri(uri: string): string | null {
  const path = redirectFromWidgetUri(uri);
  return path ? toExpoHref(path) : null;
}

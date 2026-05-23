/** Expo Router paths — mirrors Flutter `RoutePaths`. */
export const RoutePaths = {
  home: '/',
  onboarding: '/onboarding',
  radar: '/radar',
  chat: '/chat',
  profile: '/profile',
  alerts: '/alerts',
  radarRegionsView: '/radar?view=regions',

  premium: '/premium',
  feedback: '/feedback',
  feedbackModeration: '/feedback-moderation',
  admin: '/admin',
  chatAdmin: '/chat-admin',
  complaints: '/complaints',
  shelters: '/shelters',
  safety: '/safety',
  trust: '/trust',
  history: '/history',
  analytics: '/analytics',
  heatmap: '/heatmap',
  radarFull: '/radar-full',
  briefing: '/briefing',
  smartNotifications: '/smart-notifications',
  myRadar: '/my-radar',
  telegramAdmin: '/telegram-admin',
} as const;

/** Maps Flutter route paths to Expo Router file routes. */
export function toExpoHref(flutterPath: string): string {
  switch (flutterPath) {
    case RoutePaths.home:
      return '/(tabs)';
    case RoutePaths.radar:
      return '/(tabs)/radar';
    case RoutePaths.chat:
      return '/(tabs)/chat';
    case RoutePaths.profile:
      return '/(tabs)/profile';
    case RoutePaths.onboarding:
      return '/onboarding';
    case RoutePaths.alerts:
      return '/(tabs)/regions';
    case RoutePaths.premium:
      return '/premium';
    case RoutePaths.history:
      return '/history';
    case RoutePaths.analytics:
      return '/analytics';
    case RoutePaths.heatmap:
      return '/heatmap';
    case RoutePaths.chatAdmin:
      return '/chat-admin';
    case RoutePaths.complaints:
      return '/complaints';
    case RoutePaths.radarFull:
      return '/radar-full';
    case RoutePaths.briefing:
      return '/briefing';
    case RoutePaths.smartNotifications:
      return '/smart-notifications';
    case RoutePaths.myRadar:
      return '/my-radar';
    case RoutePaths.telegramAdmin:
      return '/telegram-admin';
    case RoutePaths.trust:
      return '/trust';
    case RoutePaths.feedback:
      return '/feedback';
    case RoutePaths.feedbackModeration:
      return '/feedback-moderation';
    case RoutePaths.admin:
      return '/admin';
    case RoutePaths.safety:
      return '/safety';
    case RoutePaths.shelters:
      return '/shelters';
    default:
      return '/(tabs)';
  }
}

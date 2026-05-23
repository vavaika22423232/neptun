import Constants from 'expo-constants';

const extra = Constants.expoConfig?.extra as { apiBaseUrl?: string } | undefined;

export const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL || extra?.apiBaseUrl || 'https://neptun.in.ua';

export const endpoints = {
  alarms: '/api/alarms',
  alarmsFull: '/api/alarms/full',
  alarmsAll: '/api/alarms/all',
  alarmStatus: '/api/alarm-status',
  data: '/data',
  threats: '/api/threats',
  registerDevice: '/api/register-device',
  devicePreferences: '/api/devices/preferences',
  testNotification: '/api/test-notification',
  health: '/api/health',
  appRequirements: '/api/app-requirements',
  presence: '/api/presence',
  feedback: '/api/feedback',
  verifyPurchase: '/api/verify-purchase',
  premiumEntitlement: '/api/premium/entitlement',
  v1UsersBootstrap: '/api/v1/users/bootstrap',
  v1MeEntitlements: '/api/v1/me/entitlements',
  v1PurchasesGoogleVerify: '/api/v1/purchases/google/verify',
  v1PurchasesAppleVerify: '/api/v1/purchases/apple/verify',
  v1PurchasesRestore: '/api/v1/purchases/restore',
  v1SubscriptionsStatus: '/api/v1/subscriptions/status',
  v1ConfigMonetization: '/api/v1/config/monetization',
  v1NotificationRules: '/api/v1/notification-rules',
  v1Me: '/api/v1/me',
  v1MyRadar: '/api/v1/my-radar',
  v1MyRadarSummary: '/api/v1/my-radar/summary',
  v1MyRadarLocations: '/api/v1/my-radar/locations',
  v1AlertsHistory: '/api/v1/alerts/history',
  v1AlertsCurrent: '/api/v1/alerts/current',
  v1ReportsDaily: '/api/v1/reports/daily',
  v1ReportsWeekly: '/api/v1/reports/weekly',
  v1ReportsUserSummary: '/api/v1/reports/user-summary',
  v1ReportsMyRadarDaily: '/api/v1/reports/my-radar/daily',
  v1ReportsRegionSummary: '/api/v1/reports/region',
  v1RegionsStatsDaily: '/api/v1/regions/stats/daily',
  v1TelegramExport: '/api/v1/admin-tools/telegram/export-card',
  v1TelegramTemplates: '/api/v1/admin-tools/telegram/templates',
  v1TelegramGenerate: '/api/v1/admin-tools/telegram/generate-summary',
  authToken: '/api/auth/token',
  authRefresh: '/api/auth/refresh',
  authRevoke: '/api/auth/revoke',
  chatMessages: '/api/chat/messages',
  chatSend: '/api/chat/send',
  chatUploadAudio: '/api/chat/upload-audio',
  chatUploadImage: '/api/chat/upload-image',
  chatStream: '/api/chat/stream',
  chatCheckBan: '/api/chat/check-ban',
  chatCheckNickname: '/api/chat/check-nickname',
  chatRegisterNickname: '/api/chat/register-nickname',
  chatBanUser: '/api/chat/ban-user',
  chatReport: '/api/chat/report',
  chatAddModerator: '/api/chat/add-moderator',
  chatRemoveModerator: '/api/chat/remove-moderator',
  adminChatDeleteUserMessages: '/api/admin/chat/delete-user-messages',
  adminChatReports: '/api/admin/chat/reports',
  adminChatReportsResolve: '/api/admin/chat/reports/resolve',
  adminChatBanUser: '/api/admin/chat/ban-user',
  adminMarkersDelete: '/api/admin/markers/delete',
  adminChatBanList: '/api/admin/chat/ban-list',
  adminChatUnban: '/api/admin/chat/unban',
  chatBanList: '/api/chat/ban-list',
  chatUnban: '/api/chat/unban',
} as const;

export function absoluteUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) return path;
  return `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;
}

export function wsCompatibleUrl(path: string): string {
  const url = new URL(absoluteUrl(path));
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  return url.toString();
}

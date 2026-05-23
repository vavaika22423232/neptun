export const AppConstants = {
  appName: 'Dron Alerts',
  appVersion: '2.1.1',
  appBuildNumber: 47,
  premiumDisplayPrice: '150 грн назавжди',
  playStoreListingUrl:
    'https://play.google.com/store/apps/details?id=com.neptunalarm.neptun_alarm_app',
  appStoreListingUrl: 'https://apps.apple.com/app/id6743895428',
  defaultMapCenter: [31.0, 48.5] as [number, number],
  defaultMapZoom: 5.8,
  minMapZoom: 4,
  maxMapZoom: 11,
  telegramUrl: 'https://t.me/+Q0PcuV4OkuxmYjVi',

  presencePingIntervalMs: 5 * 60 * 1000,
  presenceBackgroundPingIntervalMs: 2 * 60 * 1000,
} as const;

const fs = require('fs');
const path = require('path');
const {
  withAndroidManifest,
  withDangerousMod,
  withEntitlementsPlist,
} = require('@expo/config-plugins');

const FLUTTER_ANDROID = path.join(__dirname, '../../neptun_alarm_app/android/app/src/main');
const WIDGET_PROVIDER = '.NeptunWidgetProvider';

function copyRecursive(src, dest) {
  if (!fs.existsSync(src)) return false;
  const stat = fs.statSync(src);
  if (stat.isDirectory()) {
    fs.mkdirSync(dest, { recursive: true });
    for (const entry of fs.readdirSync(src)) {
      copyRecursive(path.join(src, entry), path.join(dest, entry));
    }
    return true;
  }
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.copyFileSync(src, dest);
  return true;
}

/** Copies Flutter home-screen widget assets + registers `NeptunWidgetProvider`. */
function withNeptunHomeWidget(config) {
  config = withDangerousMod(config, [
    'android',
    async (cfg) => {
      const projectRoot = cfg.modRequest.projectRoot;
      const main = path.join(
        projectRoot,
        'android/app/src/main',
      );
      const kotlinDest = path.join(
        main,
        'java/com/neptunalarm/neptun_alarm_app',
      );
      fs.mkdirSync(kotlinDest, { recursive: true });

      const kotlinSrc = path.join(
        FLUTTER_ANDROID,
        'kotlin/com/neptunalarm/neptun_alarm_app/NeptunWidgetProvider.kt',
      );
      if (fs.existsSync(kotlinSrc)) {
        fs.copyFileSync(
          kotlinSrc,
          path.join(kotlinDest, 'NeptunWidgetProvider.kt'),
        );
      }

      for (const sub of ['res/layout', 'res/drawable', 'res/xml']) {
        const from = path.join(FLUTTER_ANDROID, sub);
        const to = path.join(main, sub);
        copyRecursive(from, to);
      }

      return cfg;
    },
  ]);

  config = withAndroidManifest(config, (cfg) => {
    const manifest = cfg.modResults;
    const app = manifest.manifest.application?.[0];
    if (!app) return cfg;

    const receivers = app.receiver ?? [];
    const exists = receivers.some(
      (r) => r.$?.['android:name'] === WIDGET_PROVIDER,
    );
    if (!exists) {
      app.receiver = [
        ...receivers,
        {
          $: {
            'android:name': WIDGET_PROVIDER,
            'android:exported': 'true',
          },
          'intent-filter': [
            {
              action: [
                {
                  $: {
                    'android:name': 'android.appwidget.action.APPWIDGET_UPDATE',
                  },
                },
              ],
            },
          ],
          'meta-data': [
            {
              $: {
                'android:name': 'android.appwidget.provider',
                'android:resource': '@xml/neptun_widget_info',
              },
            },
          ],
        },
      ];
    }
    return cfg;
  });

  config = withEntitlementsPlist(config, (cfg) => {
    const entitlements = cfg.modResults;
    const group = 'group.com.neptunalarm.neptunAlarmApp';
    const key = 'com.apple.security.application-groups';
    const groups = entitlements[key] ?? [];
    if (!groups.includes(group)) {
      entitlements[key] = [...groups, group];
    }
    return cfg;
  });

  return config;
}

module.exports = withNeptunHomeWidget;

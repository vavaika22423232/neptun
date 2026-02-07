// ============================================
// Constants migrated from constants.py
// ============================================

// Firebase Topic Mapping
export const REGION_TOPIC_MAP: Record<string, string> = {
  'Київ': 'region_kyiv_city',
  'Київська область': 'region_kyivska',
  'Дніпропетровська область': 'region_dnipropetrovska',
  'Харківська область': 'region_kharkivska',
  'Одеська область': 'region_odeska',
  'Львівська область': 'region_lvivska',
  'Донецька область': 'region_donetska',
  'Запорізька область': 'region_zaporizka',
  'Вінницька область': 'region_vinnytska',
  'Житомирська область': 'region_zhytomyrska',
  'Черкаська область': 'region_cherkaska',
  'Чернігівська область': 'region_chernihivska',
  'Полтавська область': 'region_poltavska',
  'Сумська область': 'region_sumska',
  'Миколаївська область': 'region_mykolaivska',
  'Херсонська область': 'region_khersonska',
  'Кіровоградська область': 'region_kirovohradska',
  'Хмельницька область': 'region_khmelnytska',
  'Рівненська область': 'region_rivnenska',
  'Волинська область': 'region_volynska',
  'Тернопільська область': 'region_ternopilska',
  'Івано-Франківська область': 'region_ivano_frankivska',
  'Закарпатська область': 'region_zakarpatska',
  'Чернівецька область': 'region_chernivetska',
  'Луганська область': 'region_luhanska',
};

// Oblast ID Mapping
export const REGION_TO_OBLAST_ID: Record<string, string> = {
  'м. Київ': 'UA-30',
  'Київ': 'UA-30',
  'Київська область': 'UA-32',
  'Дніпропетровська область': 'UA-12',
  'Харківська область': 'UA-63',
  'Одеська область': 'UA-51',
  'Львівська область': 'UA-46',
  'Донецька область': 'UA-14',
  'Запорізька область': 'UA-23',
  'Вінницька область': 'UA-05',
  'Житомирська область': 'UA-18',
  'Черкаська область': 'UA-71',
  'Чернігівська область': 'UA-74',
  'Полтавська область': 'UA-53',
  'Сумська область': 'UA-59',
  'Миколаївська область': 'UA-48',
  'Херсонська область': 'UA-65',
  'Кіровоградська область': 'UA-35',
  'Хмельницька область': 'UA-68',
  'Рівненська область': 'UA-56',
  'Волинська область': 'UA-07',
  'Тернопільська область': 'UA-61',
  'Івано-Франківська область': 'UA-26',
  'Закарпатська область': 'UA-21',
  'Чернівецька область': 'UA-77',
  'Луганська область': 'UA-44',
  'АР Крим': 'UA-43',
  'Севастополь': 'UA-40',
};

// Oblast centers (fallback coordinates)
export const OBLAST_CENTERS: Record<string, [number, number]> = {
  'київ': [50.4501, 30.5234],
  'харків': [49.9935, 36.2304],
  'одес': [46.4825, 30.7233],
  'дніпр': [48.4647, 35.0462],
  'запоріж': [47.8388, 35.1396],
  'львів': [49.8397, 24.0297],
  'миколаїв': [46.9750, 31.9946],
  'херсон': [46.6354, 32.6169],
  'полтав': [49.5883, 34.5514],
  'сум': [50.9077, 34.7981],
  'чернігів': [51.4982, 31.2893],
  'вінниц': [49.2331, 28.4682],
  'житомир': [50.2547, 28.6587],
  'черкас': [49.4444, 32.0598],
  'кропивниц': [48.5079, 32.2623],
  'донец': [48.0159, 37.8028],
  'луганськ': [48.5740, 39.3078],
  'хмельниц': [49.4229, 26.9871],
  'рівн': [50.6199, 26.2516],
  'волин': [50.7472, 25.3254],
  'тернопіл': [49.5535, 25.5948],
  'івано-франків': [48.9226, 24.7111],
  'закарпат': [48.6208, 22.2879],
  'чернівц': [48.2921, 25.9358],
  'крим': [44.9521, 34.1024],
};

// Polling intervals
export const ACTIVE_POLLING_INTERVAL = 60_000; // 60s when tab is active
export const HIDDEN_POLLING_INTERVAL_DESKTOP = 300_000; // 5min when tab is hidden (desktop)
export const HIDDEN_POLLING_INTERVAL_MOBILE = 180_000; // 3min when tab is hidden (mobile)
export const PRESENCE_INTERVAL = 30_000; // 30s presence ping
export const MARKERS_CACHE_TTL = 30 * 60 * 1000; // 30 minutes localStorage cache

// SVG fade thresholds (Leaflet zoom levels)
export const SVG_FADE_START_ZOOM = 7;
export const SVG_FADE_END_ZOOM = 8;

// Cache version for static assets
export const CACHE_VERSION = 'v7';

// Google Analytics ID
export const GA_ID = 'G-MW867VP8WK';

// Google Play link
export const GOOGLE_PLAY_URL = 'https://play.google.com/store/apps/details?id=com.neptunalarm.neptun_alarm_app';

// Telegram links
export const TELEGRAM_CHANNEL_URL = 'https://t.me/+aBR79kExNQM1ZjZi';

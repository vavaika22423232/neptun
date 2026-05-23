import { ALL_UKRAINE_OBLAST_NAMES } from '../constants/oblastIds';

/** Flutter `_regionToTopic` slug map (without prefix). */
const REGION_TOPIC_SLUG: Record<string, string> = {
  'Вінницька область': 'vinnytska',
  'Волинська область': 'volynska',
  'Дніпропетровська область': 'dnipropetrovska',
  'Донецька область': 'donetska',
  'Житомирська область': 'zhytomyrska',
  'Закарпатська область': 'zakarpatska',
  'Запорізька область': 'zaporizka',
  'Івано-Франківська область': 'ivano_frankivska',
  'Київська область': 'kyivska',
  'Кіровоградська область': 'kirovohradska',
  'Луганська область': 'luhanska',
  'Львівська область': 'lvivska',
  'Миколаївська область': 'mykolaivska',
  'Одеська область': 'odeska',
  'Полтавська область': 'poltavska',
  'Рівненська область': 'rivnenska',
  'Сумська область': 'sumska',
  'Тернопільська область': 'ternopilska',
  'Харківська область': 'kharkivska',
  'Херсонська область': 'khersonska',
  'Хмельницька область': 'khmelnytska',
  'Черкаська область': 'cherkaska',
  'Чернівецька область': 'chernivetska',
  'Чернігівська область': 'chernihivska',
  'м. Київ': 'kyiv_city',
  Київ: 'kyiv_city',
  'АР Крим': 'crimea',
  Севастополь: 'sevastopol',
  'м. Севастополь': 'sevastopol',
};

/** Firebase topic id — Flutter returns `region_${slug}`. */
export function regionToTopic(region: string): string {
  const slug = REGION_TOPIC_SLUG[region];
  if (slug) return `region_${slug}`;
  const sanitized = region
    .toLowerCase()
    .replace(/[^a-z0-9]/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_|_$/g, '')
    .slice(0, 40);
  return `region_${sanitized}`;
}

/** All topics used for unsubscribe sweep (Flutter `_unsubscribeFromAllTopics`). */
export function allKnownRegionTopics(): string[] {
  const topics = ALL_UKRAINE_OBLAST_NAMES.map(regionToTopic);
  topics.push('all_regions');
  return topics;
}

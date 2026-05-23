/** SEO city pages — name (normalized) → slug. */
const CITY_NAME_TO_SLUG: Record<string, string> = {
  'київ': 'kyiv-city',
  'харків': 'kharkiv',
  'одеса': 'odesa',
  'дніпро': 'dnipro',
  'львів': 'lviv',
  'запоріжжя': 'zaporizhzhia',
  'миколаїв': 'mykolaiv',
  'вінниця': 'vinnytsia',
  'суми': 'sumy',
  'полтава': 'poltava',
};

const SLUG_TO_REGION: Record<string, string> = {
  'kyiv-city': 'kyiv',
  kharkiv: 'kharkivska',
  odesa: 'odeska',
  dnipro: 'dnipropetrovska',
  lviv: 'lvivska',
  zaporizhzhia: 'zaporizka',
  mykolaiv: 'mykolaivska',
  vinnytsia: 'vinnytska',
  sumy: 'sumska',
  poltava: 'poltavska',
};

export function citySlugForName(name: string): string | undefined {
  return CITY_NAME_TO_SLUG[name.trim().toLowerCase()];
}

export function regionSlugForCitySlug(slug: string): string | undefined {
  return SLUG_TO_REGION[slug];
}

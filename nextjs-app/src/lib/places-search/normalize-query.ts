/** Strip declension / prefix tokens before place lookup. */
const PREFIX_RE = /^(м\.|місто|с\.|село|смт|пгт|селище)\s+/iu;

/** Apostrophe variants users omit (Камянське → Кам'янське). */
const APOSTROPHE_RE = /[''ʼ`´]/g;

export function normalizePlaceQuery(raw: string): string {
  let q = raw.trim().toLowerCase().replace(/ё/g, 'е');
  q = q.replace(PREFIX_RE, '').trim();
  return q;
}

/** Match key without apostrophes — for DB / geojson fuzzy name match. */
export function compactPlaceQuery(raw: string): string {
  return normalizePlaceQuery(raw).replace(APOSTROPHE_RE, '').replace(/\s+/g, ' ').trim();
}

/**
 * Latin / RU shortcuts (subset of worker `ALIAS_MAP` + common typos).
 * Keys are normalized via normalizePlaceQuery before lookup.
 */
export const PLACE_QUERY_ALIASES: Record<string, string> = {
  kyiv: 'київ',
  kiev: 'київ',
  киев: 'київ',
  kharkiv: 'харків',
  kharkov: 'харків',
  харьков: 'харків',
  odesa: 'одеса',
  odessa: 'одеса',
  одесса: 'одеса',
  dnipro: 'дніпро',
  dnieper: 'дніпро',
  dnepr: 'дніпро',
  днепр: 'дніпро',
  днепропетровск: 'дніпро',
  lviv: 'львів',
  lwow: 'львів',
  львов: 'львів',
  zaporizhzhia: 'запоріжжя',
  zaporozhye: 'запоріжжя',
  запорожье: 'запоріжжя',
  vinnytsia: 'вінниця',
  винница: 'вінниця',
  sumy: 'суми',
  сумы: 'суми',
  poltava: 'полтава',
  chernihiv: 'чернігів',
  чернигов: 'чернігів',
  mykolaiv: 'миколаїв',
  николаев: 'миколаїв',
  cherkasy: 'черкаси',
  черкассы: 'черкаси',
  uzhhorod: 'ужгород',
  ужгород: 'ужгород',
  lutsk: 'луцьк',
  луцк: 'луцьк',
  rivne: 'рівне',
  ровно: 'рівне',
  ternopil: 'тернопіль',
  тернополь: 'тернопіль',
  ivano: 'івано-франківськ',
  'ивано-франковск': 'івано-франківськ',
  chernivtsi: 'чернівці',
  черновцы: 'чернівці',
  khmelnytskyi: 'хмельницький',
  хмельницкий: 'хмельницький',
  kherson: 'херсон',
  херсон: 'херсон',
  kryvyi: 'кривий ріг',
  'kryvyi rih': 'кривий ріг',
  кривой: 'кривий ріг',
  mariupol: 'маріуполь',
  мариуполь: 'маріуполь',
  donetsk: 'донецьк',
  донецк: 'донецьк',
  luhansk: 'луганськ',
  луганск: 'луганськ',
  sloviansk: 'слов\'янськ',
  slaviansk: 'слов\'янськ',
  славянск: 'слов\'янськ',
  bakhmut: 'бахмут',
  бахмут: 'бахмут',
  melitopol: 'мелітополь',
  мелитополь: 'мелітополь',
  berdiansk: 'бердянськ',
  бердянск: 'бердянськ',
  horlivka: 'горлівка',
  горловка: 'горлівка',
  горлівка: 'горлівка',
  kamianske: 'кам\'янське',
  kamenskoe: 'кам\'янське',
  каменское: 'кам\'янське',
  камянське: 'кам\'янське',
  камянское: 'кам\'янське',
  pavlohrad: 'павлоград',
  павлоград: 'павлоград',
  kramatorsk: 'краматорськ',
  краматорск: 'краматорськ',
  severodonetsk: 'сєвєродонецьк',
  северодонецк: 'сєвєродонецьк',
  izium: 'ізюм',
  изюм: 'ізюм',
  kupiansk: 'куп\'янськ',
  купянск: 'куп\'янськ',
  kremenchuk: 'кременчук',
  кременчуг: 'кременчук',
  bilaya: 'біла церква',
  'белая церковь': 'біла церква',
  brovary: 'бровари',
  бровары: 'бровари',
  irpin: 'ірпінь',
  ирпень: 'ірпінь',
  bucha: 'буча',
  буча: 'буча',
  uman: 'умань',
  умань: 'умань',
  makeevka: 'макіївка',
  макеевка: 'макіївка',
  makiivka: 'макіївка',
  alchevsk: 'алчевськ',
  алчевск: 'алчевськ',
  yenakiieve: 'єнакієве',
  енакиево: 'єнакієве',
  enakievo: 'єнакієве',
  zhdanovka: 'жданівка',
  ждановка: 'жданівка',
  snizhne: 'сніжне',
  снежное: 'сніжне',
  druzhkivka: 'дружківка',
  дружковка: 'дружківка',
  krasnyi: 'красний лиман',
  'красный лиман': 'лиман',
  'красний лиман': 'лиман',
  illichivsk: 'чорноморськ',
  ильичевск: 'чорноморськ',
  черноморск: 'чорноморськ',
  chornomorsk: 'чорноморськ',
  kirovograd: 'кропивницький',
  kropyvnytskyi: 'кропивницький',
};

export function expandPlaceQueryAliases(q: string): string[] {
  const variants = new Set<string>();
  const add = (s: string) => {
    const t = s.trim();
    if (t.length >= 2) variants.add(t);
    const c = compactPlaceQuery(t);
    if (c.length >= 2) variants.add(c);
  };

  add(q);
  const mapped = PLACE_QUERY_ALIASES[q] ?? PLACE_QUERY_ALIASES[compactPlaceQuery(q)];
  if (mapped) add(mapped);

  return [...variants];
}

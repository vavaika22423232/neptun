/**
 * Rule-based Telegram summary generator (no external AI required).
 * Wording is cautious — no fabricated precision.
 */

export type TelegramTemplateId =
  | 'short_regions'
  | 'night_summary'
  | 'active_threats'
  | 'daily_summary'
  | 'region_status'
  | 'channel_post'
  | 'website_blurb';

export type GenerateInput = {
  templateId: TelegramTemplateId;
  regionId?: string;
  regionName?: string;
  language?: 'uk' | 'ru' | 'en';
  style?: 'neutral' | 'official' | 'short' | 'detailed' | 'telegram_channel';
  activeAlerts?: number;
  threatTypes?: string[];
  periodLabel?: string;
};

export function listTelegramTemplates(): { id: TelegramTemplateId; label: string }[] {
  return [
    { id: 'short_regions', label: 'Коротко по областях' },
    { id: 'night_summary', label: 'Підсумок ночі' },
    { id: 'active_threats', label: 'Активні загрози зараз' },
    { id: 'daily_summary', label: 'Підсумок доби' },
    { id: 'region_status', label: 'Ситуація по регіону' },
    { id: 'channel_post', label: 'Текст для Telegram-каналу' },
    { id: 'website_blurb', label: 'Текст для сайту' },
  ];
}

export function generateTelegramSummary(input: GenerateInput): string {
  const lang = input.language ?? 'uk';
  const region = input.regionName || input.regionId || 'Україна';
  const threats = (input.threatTypes ?? []).join(', ') || '—';
  const active = input.activeAlerts ?? 0;
  const period = input.periodLabel ?? 'за наявними даними';

  const disclaimer =
    lang === 'ru'
      ? 'Информация обновляется; формулировки ориентировочные.'
      : lang === 'en'
        ? 'Information is updating; wording is approximate.'
        : 'Інформація оновлюється; формулювання орієнтовні.';

  switch (input.templateId) {
    case 'active_threats':
      return `⚠️ Активні загрози (${region})\nЗа наявними даними: ${active} подій. Типи: ${threats}.\n${disclaimer}`;
    case 'night_summary':
      return `🌙 Підсумок ночі — ${region}\nОрієнтовно ${period}: зафіксовано ${active} оновлень. Типи: ${threats}.\n${disclaimer}`;
    case 'daily_summary':
      return `📋 Підсумок доби — ${region}\nЗа наявними даними ${period}: ${active} подій. Можливі типи: ${threats}.\n${disclaimer}`;
    case 'region_status':
      return `📍 ${region}\nСтан: за наявними даними активність ${active > 0 ? 'підвищена' : 'стабільна'}. Типи: ${threats}.\n${disclaimer}`;
    case 'channel_post':
      return `NEPTUN · ${region}\n${period}: орієнтовно ${active} оновлень (${threats}). Слідкуйте за офіційними джерелами.\n${disclaimer}`;
    case 'website_blurb':
      return `${region}: за даними моніторингу ${active} подій ${period}. Деталі уточнюються.`;
    default:
      return `🇺🇦 Коротко: ${region} — ${active} подій; типи: ${threats}. ${disclaimer}`;
  }
}

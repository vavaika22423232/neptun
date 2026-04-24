/** Canonical site origin for share / UTM helpers (promotion analytics). */
export const SITE_ORIGIN = 'https://neptun.in.ua';

export type UtmParams = {
  source: string;
  medium: string;
  campaign: string;
  content?: string;
};

/**
 * Append UTM query params to an absolute https URL (Telegram, Play, App Store, etc.).
 */
export function withUtm(href: string, utm: UtmParams): string {
  try {
    const u = new URL(href);
    u.searchParams.set('utm_source', utm.source);
    u.searchParams.set('utm_medium', utm.medium);
    u.searchParams.set('utm_campaign', utm.campaign);
    if (utm.content) u.searchParams.set('utm_content', utm.content);
    return u.toString();
  } catch {
    return href;
  }
}

/** Main map with campaign tag (e.g. footer, blog). */
export function mapHomeUrl(campaign: string, content?: string): string {
  return withUtm(`${SITE_ORIGIN}/`, {
    source: 'neptun_site',
    medium: 'referral',
    campaign,
    content,
  });
}

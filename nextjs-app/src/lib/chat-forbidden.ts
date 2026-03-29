/**
 * Forbidden words/patterns for chat nicknames and message text.
 * Used by register-nickname and send routes.
 * Includes evasion patterns (l33t, unicode lookalikes).
 */
export const FORBIDDEN_PATTERNS = [
  /admin/i,
  /модератор/i,
  /moderator/i,
  /neptun/i,
  // Obscenities + variations
  /хуй/i,
  /хуи/i,
  /пизд/i,
  /пиzd/i,
  /бля/i,
  /бла/i,
  /ёб/i,
  /еб[аоу]/i,
  /ебау/i,
  /сук[аи]/i,
  /сука/i,
  /пид[аоер]/i,
  /пидор/i,
  /гандон/i,
  /мудак/i,
  /дебил/i,
  /лох/i,
  // Slurs
  /нигер/i,
  /niger/i,
  /nigger/i,
  /n1gg/i,
  /fuck/i,
  /f[\u0443y]ck/i,
  /shit/i,
  /bitch/i,
  // Politics
  /путин/i,
  /putin/i,
  /раш[аи]/i,
  /russia/i,
  /русня/i,
  /зеленськ/i,
  /зеленск/i,
];

export function containsForbiddenText(text: string): boolean {
  // Normalize: remove zero-width and extra spaces
  const normalized = text
    .replace(/[\u200B-\u200D\uFEFF]/g, '')
    .replace(/\s+/g, ' ');
  return FORBIDDEN_PATTERNS.some((p) => p.test(normalized));
}

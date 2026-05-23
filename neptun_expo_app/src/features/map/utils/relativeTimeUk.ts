/** Mirrors Flutter `_relativeUkrShort` in map_situation_status_strip.dart */
export function relativeTimeUk(at: Date): string {
  const now = Date.now();
  let diffMs = now - at.getTime();
  if (diffMs < 0) diffMs = 0;

  const sec = Math.floor(diffMs / 1000);
  if (sec < 15) return 'щойно';
  if (sec < 60) return `${sec} с тому`;

  const m = Math.floor(sec / 60);
  if (m < 60) return `${m} ${minuteWord(m)} тому`;

  const h = Math.floor(m / 60);
  if (h < 24) return `${h} ${hourWord(h)} тому`;

  const d = Math.floor(h / 24);
  return `${d} ${dayWord(d)} тому`;
}

function minuteWord(n: number): string {
  if (n % 100 >= 11 && n % 100 <= 14) return 'хвилин';
  if (n % 10 === 1) return 'хвилина';
  if (n % 10 >= 2 && n % 10 <= 4) return 'хвилини';
  return 'хвилин';
}

function hourWord(n: number): string {
  if (n % 100 >= 11 && n % 100 <= 14) return 'годин';
  if (n % 10 === 1) return 'година';
  if (n % 10 >= 2 && n % 10 <= 4) return 'години';
  return 'годин';
}

function dayWord(n: number): string {
  if (n % 100 >= 11 && n % 100 <= 14) return 'днів';
  if (n % 10 === 1) return 'день';
  if (n % 10 >= 2 && n % 10 <= 4) return 'дні';
  return 'днів';
}

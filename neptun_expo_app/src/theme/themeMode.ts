export type ThemeMode = 'light' | 'dark' | 'system';

const VALID: ThemeMode[] = ['light', 'dark', 'system'];

export function isThemeMode(v: string | undefined): v is ThemeMode {
  return v != null && (VALID as string[]).includes(v);
}

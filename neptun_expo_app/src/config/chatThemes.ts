export type ChatTheme = {
  id: string;
  label: string;
  bubbleTint?: string;
};

export const CHAT_THEME_DEFAULT_ID = 'classic';

export const CHAT_THEMES: ChatTheme[] = [
  { id: CHAT_THEME_DEFAULT_ID, label: 'Класична' },
  { id: 'azure', label: 'Океан', bubbleTint: '#2A6F9E' },
  { id: 'amber', label: 'Бурштин', bubbleTint: '#8A6B3A' },
  { id: 'emerald', label: 'Смарагд', bubbleTint: '#2A7A6E' },
];

export function chatThemeById(id: string | null | undefined): ChatTheme {
  return CHAT_THEMES.find((theme) => theme.id === id) ?? CHAT_THEMES[0];
}

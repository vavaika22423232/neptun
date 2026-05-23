import { useCallback, useEffect, useMemo, useState } from 'react';
import { useFocusEffect } from 'expo-router';
import { CHAT_THEME_DEFAULT_ID, chatThemeById } from '../../../config/chatThemes';
import { useAppTheme } from '../../../theme/useAppTheme';
import { chatBubblePalette } from '../theme/chatTokens';
import { storage } from '../../../services/storage';

export function useChatTheme(isPremium: boolean) {
  const { theme } = useAppTheme();
  const [themeId, setThemeId] = useState(CHAT_THEME_DEFAULT_ID);

  const refresh = useCallback(async () => {
    if (!isPremium) {
      setThemeId(CHAT_THEME_DEFAULT_ID);
      return;
    }
    const id = (await storage.getProChatThemeId()) || CHAT_THEME_DEFAULT_ID;
    setThemeId(chatThemeById(id).id);
  }, [isPremium]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useFocusEffect(
    useCallback(() => {
      void refresh();
    }, [refresh]),
  );

  const bubbles = useMemo(
    () => chatBubblePalette(themeId, isPremium, theme),
    [themeId, isPremium, theme],
  );

  return {
    themeId,
    theme: chatThemeById(isPremium ? themeId : CHAT_THEME_DEFAULT_ID),
    bubbles,
  };
}

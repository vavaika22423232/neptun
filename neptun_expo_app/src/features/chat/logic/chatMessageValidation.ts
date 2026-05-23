export const CHAT_MESSAGE_MAX_LENGTH = 2000;

export type ChatMessageValidation =
  | { ok: true; text: string }
  | { ok: false; code: 'empty' | 'too_long' | 'spam'; message: string };

const SPAM_REPEAT = /(.)\1{49,}/u;

export function validateChatMessageInput(raw: string): ChatMessageValidation {
  const text = raw.trim();
  if (!text) {
    return { ok: false, code: 'empty', message: 'Введіть повідомлення' };
  }
  if (text.length > CHAT_MESSAGE_MAX_LENGTH) {
    return {
      ok: false,
      code: 'too_long',
      message: `Максимум ${CHAT_MESSAGE_MAX_LENGTH} символів`,
    };
  }
  if (SPAM_REPEAT.test(text)) {
    return { ok: false, code: 'spam', message: 'Повідомлення виглядає як спам' };
  }
  return { ok: true, text };
}

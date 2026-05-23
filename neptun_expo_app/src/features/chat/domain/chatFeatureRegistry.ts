/** Client capability matrix — UI may ship before backend. */
export type ChatFeatureStatus = 'live' | 'partial' | 'soon';

export type ChatFeature = {
  id: string;
  title: string;
  description: string;
  status: ChatFeatureStatus;
  icon: string;
};

export const CHAT_FEATURE_GROUPS: { title: string; items: ChatFeature[] }[] = [
  {
    title: 'Повідомлення',
    items: [
      { id: 'text', title: 'Текст і відповіді', description: 'Відповідь, редагування, чернетки', status: 'live', icon: 'chatbubble' },
      { id: 'react', title: 'Реакції', description: 'Емодзі на повідомленнях', status: 'live', icon: 'heart' },
      { id: 'media', title: 'Фото та голос', description: 'Зображення й voice до 60 с', status: 'live', icon: 'mic' },
      { id: 'search', title: 'Пошук', description: 'У стрічці спільноти', status: 'live', icon: 'search' },
      { id: 'pin', title: 'Закріплення', description: 'Локально у стрічці', status: 'partial', icon: 'pin' },
      { id: 'forward', title: 'Пересилання', description: 'Share sheet', status: 'live', icon: 'arrow-redo' },
      { id: 'threads', title: 'Гілки', description: 'Відповіді як треди', status: 'partial', icon: 'link' },
      { id: 'md', title: 'Згадки та #теги', description: 'Підсвітка в тексті', status: 'partial', icon: 'at' },
      { id: 'gif', title: 'GIF і стікери', description: 'Каталог медіа', status: 'soon', icon: 'happy' },
      { id: 'polls', title: 'Опитування', description: 'Голосування в чаті', status: 'soon', icon: 'bar-chart-outline' },
      { id: 'schedule', title: 'Відкладені', description: 'Надіслати пізніше', status: 'soon', icon: 'time' },
    ],
  },
  {
    title: 'Спільнота',
    items: [
      { id: 'community', title: 'Спільнота NEPTUN', description: 'Загальний live-чат', status: 'live', icon: 'people' },
      { id: 'profile', title: 'Профілі', description: 'Аватар, PRO, модерація', status: 'partial', icon: 'person' },
    ],
  },
  {
    title: 'Розумні',
    items: [
      { id: 'ai', title: 'AI помічник', description: 'Підказки та резюме', status: 'soon', icon: 'sparkles' },
      { id: 'smart', title: 'Швидкі відповіді', description: 'Чіпи над полем вводу', status: 'partial', icon: 'flash-outline' },
      { id: 'translate', title: 'Переклад', description: 'In-place переклад', status: 'soon', icon: 'language' },
    ],
  },
];

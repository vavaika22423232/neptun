import { AppConstants } from './constants';

export type ChangelogItem = {
  icon: 'cloud-offline' | 'camera' | 'moon';
  iconColor: string;
  title: string;
  description: string;
};

/** Per-version release notes — Flutter `ChangelogDialog` content for `2.1.1`. */
export const CHANGELOG_BY_VERSION: Record<string, ChangelogItem[]> = {
  [AppConstants.appVersion]: [
    {
      icon: 'cloud-offline',
      iconColor: '#10B981',
      title: 'Офлайн-очередь повідомлень',
      description:
        'Повідомлення зберігаються при відсутності мережі та відправляються автоматично після відновлення',
    },
    {
      icon: 'camera',
      iconColor: '#3B82F6',
      title: 'Фото в чаті',
      description: 'Відправка фото з галереї та камери. Підтримка HEIC з iPhone',
    },
    {
      icon: 'moon',
      iconColor: '#6366F1',
      title: 'Покращена темна тема чату',
      description: 'Чужі повідомлення тепер добре видно на темному фоні',
    },
  ],
};

export function changelogForCurrentVersion(): ChangelogItem[] {
  return CHANGELOG_BY_VERSION[AppConstants.appVersion] ?? [];
}

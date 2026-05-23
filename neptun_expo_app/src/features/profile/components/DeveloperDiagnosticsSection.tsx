import { Platform } from 'react-native';
import { useProfileSettings } from '../hooks/useProfileSettings';
import { SettingsSection } from './settings/SettingsSection';
import { SettingsRow } from './settings/SettingsRow';

/** Dev-only push / subscription diagnostics — never shown in production builds. */
export function DeveloperDiagnosticsSection() {
  const settings = useProfileSettings();
  if (!__DEV__) return null;

  const topicsPreview =
    settings.subscribedTopics.length === 0
      ? 'Немає підписок'
      : settings.subscribedTopics.slice(0, 8).join(', ') +
        (settings.subscribedTopics.length > 8 ? '…' : '');

  return (
    <SettingsSection title="Developer" subtitle="Push-токен, топіки та діагностика збірки">
      <SettingsRow
        label="Push token"
        subtitle={settings.pushToken ? `${settings.pushToken.slice(0, 24)}…` : 'Не отримано'}
        showDivider
      />
      {Platform.OS === 'ios' ? (
        <SettingsRow
          label="APNs статус"
          subtitle={settings.pushToken ? 'Токен отримано' : 'Токен не отримано'}
          showDivider
        />
      ) : null}
      <SettingsRow label="Підписки на топіки" subtitle={topicsPreview} />
    </SettingsSection>
  );
}

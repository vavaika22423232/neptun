import { useRouter } from 'expo-router';
import { memo } from 'react';
import { View } from 'react-native';
import { useModeratorLogoTap } from '../core/moderator/useModeratorLogoTap';
import { ModeratorSecretDialog } from '../features/chat/components/ModeratorSecretDialog';
import { ProfileHeader } from '../features/profile/components/ProfileHeader';
import { useApp } from '../context/AppContext';
import { moderatorService } from '../services/moderatorService';
import { OfflineBanner } from './OfflineBanner';

function ProfileTabChromeInner() {
  const { refreshIdentity } = useApp();
  const logoTap = useModeratorLogoTap();

  return (
    <View>
      <ProfileHeader onTitlePress={logoTap.onLogoTap} />
      <OfflineBanner />
      <ModeratorSecretDialog
        visible={logoTap.showLogin}
        title="Модератор"
        confirmLabel="Увійти"
        onCancel={() => logoTap.setShowLogin(false)}
        onConfirm={async (secret) => {
          const err = await moderatorService.login(secret);
          if (!err) void refreshIdentity();
          return err;
        }}
      />
      <ModeratorSecretDialog
        visible={logoTap.showLogout}
        title="Модератор"
        confirmLabel="Вийти"
        destructive
        onCancel={() => logoTap.setShowLogout(false)}
        onConfirm={async () => {
          await moderatorService.logout();
          void refreshIdentity();
          return null;
        }}
      />
    </View>
  );
}

export const ProfileTabChrome = memo(ProfileTabChromeInner);

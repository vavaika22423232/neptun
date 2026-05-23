import { View } from 'react-native';
import { Card } from '../components/Card';
import { Text } from '../components/Text';
import { useModeratorScreenGuard } from '../core/moderator/useModeratorScreenGuard';
import { useLegacyScreenStyles } from '../theme/useLegacyScreenStyles';

export function ChatAdminScreen() {
  const isModerator = useModeratorScreenGuard();
  const styles = useScreenStyles();
  if (!isModerator) return null;
  return (
    <View style={styles.root}>
      <Card>
        <Text title>Модерація чату</Text>
        <Text muted>Адмін-сервіси підключені до тих самих API; повний список скарг буде наступним UI-модулем.</Text>
      </Card>
    </View>
  );
}

function useScreenStyles() {
  return useLegacyScreenStyles((c) => ({
    root: { flex: 1, backgroundColor: c.bg, padding: 14 },
  }));
}

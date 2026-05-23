import { useRouter } from 'expo-router';
import { StyleSheet, View } from 'react-native';
import { Text } from '../../../components/Text';
import { PrimaryButton } from '../../../components/PrimaryButton';
import { monetizationConfigService } from '../services/monetizationConfigService';
import { useEntitlements } from '../hooks/useEntitlements';
import { useThemedStyles } from '../../../theme/useAppTheme';

/**
 * Rewarded offers — PRO upsell only until AdMob Rewarded verification is wired server-side.
 * Local timer unlocks were removed (security: client-only bypass).
 */
export function RewardedAdOffers() {
  const { isPaid } = useEntitlements();
  const router = useRouter();
  const cfg = monetizationConfigService.get();

  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      card: {
        padding: 16,
        borderRadius: 12,
        backgroundColor: t.colors.surface,
        borderWidth: 1,
        borderColor: t.colors.border,
        gap: 10,
      },
      muted: { color: t.colors.textMuted },
    }),
  );

  if (isPaid || !cfg.enableRewardedAdFree) return null;

  return (
    <View style={styles.card}>
      <Text subtitle>Розширена історія та без реклами</Text>
      <Text style={styles.muted}>
        Тимчасові бонуси за рекламу будуть доступні після підключення перевірки на сервері. Зараз — лише PRO.
      </Text>
      <PrimaryButton variant="ghost" onPress={() => router.push('/premium')}>
        Оформити PRO від 69 грн/міс
      </PrimaryButton>
    </View>
  );
}

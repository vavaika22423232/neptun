import * as Linking from 'expo-linking';
import { Platform, StyleSheet, View } from 'react-native';
import { Card } from '../components/Card';
import { PrimaryButton } from '../components/PrimaryButton';
import { Text } from '../components/Text';
import { NeptunPressable } from '../design/components/NeptunPressable';
import { palette, spacing } from '../design/tokens';
import type { AppUpdateBlockPayload } from '../services/appVersionGateService';

export function AppUpdateRequiredScreen({
  payload,
  onRetry,
}: {
  payload: AppUpdateBlockPayload;
  onRetry: () => void;
}) {
  const storeUrl = Platform.OS === 'ios' ? payload.iosStoreUrl : payload.androidStoreUrl;
  return (
    <View style={styles.root}>
      <Card style={styles.card}>
        <Text title>{payload.title}</Text>
        <Text muted style={styles.message}>
          {payload.message}
        </Text>
        <PrimaryButton onPress={() => void Linking.openURL(storeUrl)}>Оновити застосунок</PrimaryButton>
        <NeptunPressable haptic={false} onPress={onRetry}>
          <Text style={styles.retry}>Перевірити ще раз</Text>
        </NeptunPressable>
      </Card>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: palette.bg,
    padding: spacing.screenH,
  },
  card: {
    width: '100%',
    maxWidth: 420,
    gap: spacing.md,
  },
  message: { lineHeight: 22 },
  retry: {
    textAlign: 'center',
    color: palette.accentSoft,
    fontWeight: '600',
    paddingTop: spacing.sm,
  },
});

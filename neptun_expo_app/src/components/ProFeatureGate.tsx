import { useRouter } from 'expo-router';
import { StyleSheet, View } from 'react-native';
import { NeptunEmptyState } from '../design/components/NeptunEmptyState';
import { NeptunLoading } from '../design/components/NeptunLoading';
import { palette } from '../design/tokens';
import { ProFeature, proFeatureNames } from '../core/pro/proGate';
import { useProGate } from '../hooks/useProGate';

type Props = {
  feature: ProFeature;
  children: React.ReactNode;
};

export function ProFeatureGate({ feature, children }: Props) {
  const { unlocked, loading } = useProGate(feature);
  const router = useRouter();

  if (loading) {
    return (
      <View style={styles.centered}>
        <NeptunLoading label="Завантаження…" />
      </View>
    );
  }

  if (!unlocked) {
    return (
      <View style={styles.centered}>
        <NeptunEmptyState
          icon="ribbon-outline"
          title="NEPTUN PRO"
          subtitle={`${proFeatureNames[feature]} доступна з підпискою PRO`}
          actionLabel="Відкрити PRO"
          onAction={() => router.push('/premium')}
        />
      </View>
    );
  }

  return <>{children}</>;
}

const styles = StyleSheet.create({
  centered: {
    flex: 1,
    backgroundColor: palette.bg,
    justifyContent: 'center',
  },
});

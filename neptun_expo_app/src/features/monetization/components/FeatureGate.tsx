import type { ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';
import { Text } from '../../../components/Text';
import { PrimaryButton } from '../../../components/PrimaryButton';
import { NeptunLoading } from '../../../design/components/NeptunLoading';
import { useProAccess } from '../../pro/hooks/useProAccess';
import { useThemedStyles } from '../../../theme/useAppTheme';
import type { PlanId } from '../types';
import { useEntitlements } from '../hooks/useEntitlements';

type Props = {
  minPlan: PlanId;
  featureName: string;
  children: ReactNode;
};

const PLAN_LABEL: Record<PlanId, string> = {
  free: 'Free',
  pro: 'PRO',
  pro_plus: 'PRO+',
  max: 'MAX',
};

export function FeatureGate({ minPlan, featureName, children }: Props) {
  const { hasPlan, plan } = useEntitlements();
  const { openPaywall } = useProAccess();
  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      root: {
        flex: 1,
        backgroundColor: t.colors.background,
        justifyContent: 'center',
        padding: 24,
        gap: 16,
      },
      title: { textAlign: 'center' },
      sub: { textAlign: 'center', color: t.colors.textMuted },
    }),
  );

  if (hasPlan(minPlan)) {
    return <>{children}</>;
  }

  return (
    <View style={styles.root}>
      <Text title style={styles.title}>
        {featureName}
      </Text>
      <Text style={styles.sub}>
        Доступно з тарифу {PLAN_LABEL[minPlan]}. Ваш план: {PLAN_LABEL[plan]}.
      </Text>
      <PrimaryButton onPress={() => openPaywall({ source: 'feature_gate' })}>
        Отримати PRO
      </PrimaryButton>
    </View>
  );
}

export function FeatureGateLoading() {
  return <NeptunLoading label="Завантаження…" />;
}

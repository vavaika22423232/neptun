import type { ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';
import { AppCard } from '../../../components/ui/AppCard';

type Props = {
  children: ReactNode;
};

/** Diia-style grouped settings list inside one card. */
export function ProfileSettingsGroup({ children }: Props) {
  return (
    <AppCard style={styles.card} elevated>
      <View style={styles.inner}>{children}</View>
    </AppCard>
  );
}

const styles = StyleSheet.create({
  card: { padding: 0, overflow: 'hidden' },
  inner: { paddingVertical: 4 },
});

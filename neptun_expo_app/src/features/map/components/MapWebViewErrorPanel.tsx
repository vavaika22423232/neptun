import { StyleSheet, View } from 'react-native';
import { NeptunEmptyState } from '../../../design/components/NeptunEmptyState';
import { palette } from '../../../design/tokens';

export function MapWebViewErrorPanel({ onRetry }: { onRetry: () => void }) {
  return (
    <View style={styles.root}>
      <NeptunEmptyState
        icon="map-outline"
        title="Не вдалося завантажити карту"
        subtitle="Перевірте з'єднання або спробуйте пізніше"
        actionLabel="Спробувати знову"
        onAction={onRetry}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: palette.bg,
    justifyContent: 'center',
    zIndex: 30,
  },
});

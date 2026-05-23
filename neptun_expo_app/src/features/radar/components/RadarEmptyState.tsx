import { StyleSheet, View } from 'react-native';
import { AppButton } from '../../../components/ui/AppButton';
import { AppEmptyState } from '../../../components/ui/AppEmptyState';
import { openNeptunTelegramChannel } from '../../../core/utils/openNeptunTelegram';
import { useThemedStyles } from '../../../theme/useAppTheme';
import { formatFetchedShort } from '../utils/radarFormatters';
import { RadarFeedCard } from './RadarFeedCard';

type Props = {
  lastFetchedAt: number | null;
  onOpenMap: () => void;
};

export function RadarEmptyState({ lastFetchedAt, onOpenMap }: Props) {
  const styles = useEmptyStyles();
  const sub =
    lastFetchedAt != null
      ? `Оновлено ${formatFetchedShort(lastFetchedAt)} тому`
      : 'Дані оновлюються автоматично';

  return (
    <RadarFeedCard>
      <View style={styles.wrap}>
        <AppEmptyState
          icon="shield-checkmark-outline"
          title="Активних загроз наразі немає"
          subtitle={sub}
        />
        <View style={styles.actions}>
          <AppButton onPress={onOpenMap}>Відкрити карту</AppButton>
          <AppButton variant="secondary" onPress={() => void openNeptunTelegramChannel('radar_empty')}>
            Telegram
          </AppButton>
        </View>
      </View>
    </RadarFeedCard>
  );
}

function useEmptyStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      wrap: {
        paddingVertical: t.spacing.xl,
        paddingHorizontal: t.radar.cardPad,
        gap: t.spacing.lg,
      },
      actions: {
        gap: t.spacing.sm,
      },
    }),
  );
}

import type { ReactNode } from 'react';
import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import { useThemedStyles } from '../../../theme/useAppTheme';

type Props = {
  children: ReactNode;
};

/** White grouped list surface — profile / iOS settings style. */
function RadarFeedCardInner({ children }: Props) {
  const styles = useCardStyles();
  return <View style={styles.card}>{children}</View>;
}

function useCardStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      card: {
        borderRadius: t.radar.cardRadius,
        backgroundColor: t.colors.card,
        overflow: 'hidden',
        shadowColor: '#000000',
        shadowOpacity: t.scheme === 'light' ? 0.05 : 0,
        shadowRadius: 10,
        shadowOffset: { width: 0, height: 2 },
        elevation: t.scheme === 'light' ? 1 : 0,
      },
    }),
  );
}

export const RadarFeedCard = memo(RadarFeedCardInner);

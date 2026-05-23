import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, View } from 'react-native';
import Animated, { FadeIn } from 'react-native-reanimated';
import { Text } from '../../../components/Text';
import { fonts } from '../../../theme/fonts';
import { useThemedStyles } from '../../../theme/useAppTheme';

type Props =
  | { variant: 'idle' }
  | { variant: 'search'; query?: string }
  | { variant: 'filter'; filterLabel?: string };

export function ChatEmptyState(props: Props) {
  const styles = useEmptyStyles();

  const icon =
    props.variant === 'search'
      ? 'search-outline'
      : props.variant === 'filter'
        ? 'funnel-outline'
        : 'chatbubble-outline';

  let title = 'Повідомлень поки немає';
  let subtitle: string | undefined = 'Будьте першим, хто напише';

  if (props.variant === 'search') {
    title = props.query ? `Нічого за «${props.query}»` : 'Нічого не знайдено';
    subtitle = undefined;
  } else if (props.variant === 'filter') {
    title = props.filterLabel ? `Порожньо · ${props.filterLabel}` : 'Порожньо';
    subtitle = undefined;
  }

  return (
    <Animated.View entering={FadeIn.duration(240)} style={styles.wrap}>
      <Ionicons name={icon} size={36} color={styles.iconColor.color} />
      <Text style={styles.title}>{title}</Text>
      {subtitle ? (
        <Text muted style={styles.subtitle}>
          {subtitle}
        </Text>
      ) : null}
    </Animated.View>
  );
}

function useEmptyStyles() {
  return useThemedStyles((t) => {
    const isDark = t.scheme === 'dark';
    return StyleSheet.create({
      wrap: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
        paddingHorizontal: 40,
        paddingVertical: 56,
        minHeight: 220,
        gap: 10,
      },
      iconColor: { color: isDark ? 'rgba(235,235,245,0.28)' : t.colors.textFaint },
      title: {
        fontFamily: fonts.semiBold,
        fontSize: 16,
        textAlign: 'center',
        color: isDark ? 'rgba(235,235,245,0.72)' : t.colors.textSecondary,
      },
      subtitle: {
        fontFamily: fonts.regular,
        fontSize: 13,
        textAlign: 'center',
        marginTop: 2,
      },
    });
  });
}

import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Text } from '../../../components/Text';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { chatChromeBridge } from '../chatChromeBridge';
import { fonts } from '../../../theme/fonts';
import { useThemedStyles } from '../../../theme/useAppTheme';
import { useApp } from '../../../context/AppContext';

const AVATAR_COLORS = ['#5856D6', '#FF9500', '#34C759', '#007AFF', '#FF2D55'];

function OnlineAvatarStack({ count }: { count: number }) {
  const styles = useStackStyles();
  const shown = Math.min(Math.max(count, 1), 3);

  return (
    <View style={styles.stack}>
      {Array.from({ length: shown }).map((_, i) => (
        <View
          key={i}
          style={[
            styles.dot,
            { backgroundColor: AVATAR_COLORS[i % AVATAR_COLORS.length], marginLeft: i === 0 ? 0 : -10 },
          ]}
        />
      ))}
    </View>
  );
}

/** Messenger-style chat header — title, online strip, actions. */
function ChatTabHeaderInner() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { onlineCount } = useApp();
  const styles = useHeaderStyles();

  const onlineLabel =
    onlineCount > 0
      ? `${onlineCount.toLocaleString('uk-UA')} онлайн`
      : 'Спільнота NEPTUN';

  return (
    <View style={[styles.shell, { paddingTop: insets.top }]}>
      <View style={styles.bar}>
        <NeptunPressable
          haptic
          style={styles.iconBtn}
          accessibilityLabel="Налаштування чату"
          onPress={() => router.push('/chat-settings')}
        >
          <Ionicons name="chevron-back" size={22} color={styles.iconColor.color} />
        </NeptunPressable>

        <NeptunPressable
          haptic={false}
          style={styles.center}
          accessibilityLabel="NEPTUN чат"
          onLongPress={() => chatChromeBridge.toggleSearch()}
        >
          <Text style={styles.title} numberOfLines={1}>
            NEPTUN чат
          </Text>
          <View style={styles.onlineRow}>
            <OnlineAvatarStack count={onlineCount} />
            <Text style={styles.online}>{onlineLabel}</Text>
          </View>
        </NeptunPressable>

        <NeptunPressable
          haptic
          style={styles.iconBtn}
          accessibilityLabel="Медіа чату"
          onPress={() => chatChromeBridge.toggleMedia()}
        >
          <Ionicons name="videocam-outline" size={22} color={styles.iconColor.color} />
        </NeptunPressable>
      </View>
    </View>
  );
}

function useHeaderStyles() {
  return useThemedStyles((t) => {
    const isDark = t.scheme === 'dark';
    return StyleSheet.create({
      shell: {
        backgroundColor: isDark ? '#000000' : t.colors.cardMuted,
      },
      bar: {
        minHeight: 52,
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 10,
        paddingBottom: 10,
        gap: 6,
      },
      iconBtn: {
        width: 40,
        height: 40,
        borderRadius: 20,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)',
      },
      iconColor: { color: t.colors.textPrimary },
      center: {
        flex: 1,
        alignItems: 'center',
        gap: 3,
        paddingHorizontal: 4,
      },
      title: {
        fontFamily: fonts.semiBold,
        fontSize: 17,
        letterSpacing: -0.2,
        color: t.colors.textPrimary,
      },
      onlineRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 7,
      },
      online: {
        fontFamily: fonts.regular,
        fontSize: 12,
        color: t.colors.textMuted,
      },
    });
  });
}

function useStackStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      stack: {
        flexDirection: 'row',
        alignItems: 'center',
      },
      dot: {
        width: 20,
        height: 20,
        borderRadius: 10,
        borderWidth: 2,
        borderColor: t.chat.bg,
      },
    }),
  );
}

export const ChatTabHeader = memo(ChatTabHeaderInner);

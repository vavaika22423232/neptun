import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import { Text } from '../../../components/Text';
import { fonts } from '../../../theme/fonts';
import { useThemedStyles } from '../../../theme/useAppTheme';

function ChatCommunityNoticeInner() {
  const styles = useNoticeStyles();

  return (
    <View style={styles.wrap}>
      <View style={styles.pill}>
        <Text style={styles.text} numberOfLines={2}>
          Поважайте спільноту. Заборонено заклики до насильства та дезінформація.
        </Text>
      </View>
    </View>
  );
}

function useNoticeStyles() {
  return useThemedStyles((t) => {
    const isDark = t.scheme === 'dark';
    return StyleSheet.create({
      wrap: {
        alignItems: 'center',
        paddingHorizontal: 24,
        paddingBottom: 8,
      },
      pill: {
        maxWidth: 320,
        paddingHorizontal: 14,
        paddingVertical: 8,
        borderRadius: 14,
        backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)',
      },
      text: {
        fontFamily: fonts.regular,
        fontSize: 11,
        lineHeight: 15,
        textAlign: 'center',
        color: isDark ? 'rgba(235,235,245,0.55)' : t.colors.textMuted,
      },
    });
  });
}

export const ChatCommunityNotice = memo(ChatCommunityNoticeInner);

import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, TextInput, View } from 'react-native';
import { Text } from '../../../components/Text';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { fonts } from '../../../theme/fonts';
import { useThemedStyles } from '../../../theme/useAppTheme';

type Props = {
  topInset: number;
  search: string;
  matchCount: number;
  totalCount: number;
  onChangeSearch: (value: string) => void;
  onClose: () => void;
};

export function ChatSearchHeader({ topInset, search, matchCount, totalCount, onChangeSearch, onClose }: Props) {
  const styles = useSearchStyles();

  return (
    <View style={[styles.wrap, { paddingTop: topInset + 8 }]}>
      <View style={styles.bar}>
        <Ionicons name="search" size={18} color={styles.mutedColor.color} />
        <TextInput
          autoFocus
          value={search}
          onChangeText={onChangeSearch}
          placeholder="Пошук у чаті"
          placeholderTextColor={styles.faintColor.color}
          style={styles.input}
        />
        <Text style={styles.count}>
          {matchCount}/{totalCount}
        </Text>
        <NeptunPressable haptic onPress={onClose} style={styles.close}>
          <Ionicons name="close" size={18} color={styles.textColor.color} />
        </NeptunPressable>
      </View>
    </View>
  );
}

function useSearchStyles() {
  return useThemedStyles((t) => {
    const isDark = t.scheme === 'dark';
    const barBg = isDark ? '#1C1C1E' : '#E9E9EB';
    return StyleSheet.create({
      wrap: {
        paddingHorizontal: 14,
        paddingBottom: 10,
        backgroundColor: t.chat.bg,
      },
      bar: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        minHeight: 44,
        paddingHorizontal: 12,
        borderRadius: 22,
        backgroundColor: barBg,
      },
      input: {
        flex: 1,
        color: t.chat.text,
        fontFamily: fonts.regular,
        fontSize: 16,
        paddingVertical: 8,
      },
      count: {
        fontFamily: fonts.medium,
        fontSize: 12,
        color: t.chat.textMuted,
      },
      close: {
        width: 30,
        height: 30,
        borderRadius: 15,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
      },
      mutedColor: { color: t.chat.textMuted },
      faintColor: { color: t.chat.textFaint },
      textColor: { color: t.chat.text },
    });
  });
}

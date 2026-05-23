import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { colors } from '../theme/colors';
import { fonts } from '../theme/fonts';
import { useLegacyScreenStyles } from '../theme/useLegacyScreenStyles';
import { Text } from './Text';

type Props = {
  contextLabel: string;
  subtitleLeadingIcon?: React.ComponentProps<typeof Ionicons>['name'];
  showSearch?: boolean;
  onSearchPress?: () => void;
  onlineCount?: number;
};

export function MainChrome({ contextLabel, subtitleLeadingIcon, showSearch, onSearchPress, onlineCount }: Props) {
  const styles = useScreenStyles();
  const insets = useSafeAreaInsets();
  return (
    <View style={[styles.root, { paddingTop: insets.top + 8 }]}>
      <View style={styles.brandRow}>
        <View style={styles.logo}>
          <Text style={styles.logoText}>N</Text>
        </View>
        <View style={styles.titleWrap}>
          <Text style={styles.title}>{contextLabel}</Text>
          <View style={styles.subtitleRow}>
            {subtitleLeadingIcon ? <Ionicons name={subtitleLeadingIcon} size={13} color={colors.muted} /> : null}
            <Text muted style={styles.subtitle}>
              {onlineCount != null ? `${onlineCount} онлайн` : 'NEPTUN live'}
            </Text>
          </View>
        </View>
        {showSearch ? (
          <Pressable onPress={onSearchPress} style={styles.iconButton}>
            <Ionicons name="search" size={20} color={colors.text} />
          </Pressable>
        ) : null}
      </View>
    </View>
  );
}


function useScreenStyles() {
  return useLegacyScreenStyles((c) => ({
  root: {
    paddingHorizontal: 16,
    paddingBottom: 12,
    backgroundColor: c.bg,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: c.border,
  },
  brandRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  logo: {
    width: 38,
    height: 38,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: c.surface2,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: c.borderStrong,
  },
  logoText: {
    fontFamily: fonts.bold,
    fontSize: 18,
    color: c.accent2,
  },
  titleWrap: {
    flex: 1,
  },
  title: {
    fontFamily: fonts.bold,
    fontSize: 18,
  },
  subtitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    marginTop: 2,
  },
  subtitle: {
    fontSize: 12,
  },
  iconButton: {
    width: 40,
    height: 40,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: c.surface,
  },
}));
}

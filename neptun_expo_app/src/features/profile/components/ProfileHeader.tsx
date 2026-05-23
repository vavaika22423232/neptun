import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { memo, type ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useApp } from '../../../context/AppContext';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { Text } from '../../../components/Text';
import { fonts } from '../../../theme/fonts';
import { useThemedStyles } from '../../../theme/useAppTheme';
import { profileTokens } from '../profileTokens';

export type ProfileHeaderProps = {
  title?: string;
  onTitlePress?: () => void;
  rightAction?: ReactNode;
};

function ProfileHeaderInner({
  title = 'Профіль',
  onTitlePress,
  rightAction,
}: ProfileHeaderProps) {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { isPremium } = useApp();
  const styles = useHeaderStyles();

  const defaultRight = (
    <NeptunPressable
      haptic
      style={styles.iconBtn}
      accessibilityLabel="NEPTUN PRO"
      onPress={() => router.push('/premium')}
    >
      <Ionicons
        name={isPremium ? 'star' : 'search-outline'}
        size={22}
        color={styles.icon.color}
      />
    </NeptunPressable>
  );

  return (
    <View style={[styles.shell, { paddingTop: insets.top }]}>
      <View style={styles.bar}>
        <View style={styles.side}>
          <View style={styles.sidePlaceholder} />
        </View>
        <NeptunPressable
          haptic={false}
          disabled={!onTitlePress}
          onPress={onTitlePress}
          style={styles.titleWrap}
        >
          <Text style={styles.title}>{title}</Text>
        </NeptunPressable>
        <View style={styles.side}>{rightAction ?? defaultRight}</View>
      </View>
    </View>
  );
}

function useHeaderStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      shell: {
        backgroundColor: t.colors.cardMuted,
      },
      bar: {
        height: 44,
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: profileTokens.insetH,
      },
      side: {
        width: profileTokens.headerBtn,
        alignItems: 'center',
        justifyContent: 'center',
      },
      sidePlaceholder: {
        width: profileTokens.headerBtn,
        height: profileTokens.headerBtn,
      },
      titleWrap: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
      },
      title: {
        fontFamily: fonts.semiBold,
        fontSize: profileTokens.type.headerTitle.fontSize,
        lineHeight: profileTokens.type.headerTitle.lineHeight,
        color: t.colors.textPrimary,
      },
      iconBtn: {
        width: profileTokens.headerBtn,
        height: profileTokens.headerBtn,
        alignItems: 'center',
        justifyContent: 'center',
      },
      icon: { color: t.colors.textPrimary },
    }),
  );
}

export const ProfileHeader = memo(ProfileHeaderInner);

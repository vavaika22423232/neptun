import type { ReactNode } from 'react';
import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import { Text } from '../../../../components/Text';
import { fonts } from '../../../../theme/fonts';
import { profileTokens } from '../../profileTokens';
import { useThemedStyles } from '../../../../theme/useAppTheme';

type Props = {
  title?: string;
  subtitle?: string;
  children: ReactNode;
};

function SettingsSectionInner({ title, subtitle, children }: Props) {
  const styles = useSectionStyles();
  return (
    <View style={styles.wrap}>
      {title ? (
        <View style={styles.header}>
          <Text style={styles.title}>{title}</Text>
          {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
        </View>
      ) : null}
      <View style={styles.list}>{children}</View>
    </View>
  );
}

function useSectionStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      wrap: {
        gap: 8,
      },
      header: {
        gap: 4,
        paddingHorizontal: profileTokens.insetH + 4,
      },
      title: {
        fontFamily: fonts.semiBold,
        fontSize: profileTokens.type.sectionLabel.fontSize,
        lineHeight: profileTokens.type.sectionLabel.lineHeight,
        color: t.colors.textPrimary,
      },
      subtitle: {
        fontFamily: fonts.regular,
        fontSize: profileTokens.type.rowSubtitle.fontSize,
        lineHeight: profileTokens.type.rowSubtitle.lineHeight,
        color: t.colors.textMuted,
      },
      list: {
        marginHorizontal: profileTokens.insetH,
        borderRadius: profileTokens.cardRadius,
        backgroundColor: t.colors.card,
        overflow: 'hidden',
        shadowColor: '#000',
        shadowOpacity: t.scheme === 'light' ? 0.04 : 0,
        shadowRadius: 8,
        shadowOffset: { width: 0, height: 2 },
        elevation: t.scheme === 'light' ? 1 : 0,
      },
    }),
  );
}

export const SettingsSection = memo(SettingsSectionInner);

import { Ionicons } from '@expo/vector-icons';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { ComponentProps, ReactNode } from 'react';
import { StyleSheet, Switch, View } from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { Text } from '../../../components/Text';
import { CHAT_THEMES } from '../../../config/chatThemes';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import type { RootStackParamList } from '../../../navigation/types';
import { paywall } from '../theme/paywallTokens';
import { fonts } from '../../../theme/fonts';

type Nav = NativeStackNavigationProp<RootStackParamList>;

type Props = {
  navigation: Nav;
  themeLabel: string;
  animAvatar: boolean;
  onThemePress: () => void;
  onAnimAvatarChange: (v: boolean) => void;
  onProfileSounds: () => void;
};

export function PremiumMemberHub({
  navigation,
  themeLabel,
  animAvatar,
  onThemePress,
  onAnimAvatarChange,
  onProfileSounds,
}: Props) {
  return (
    <Animated.View entering={FadeInDown.delay(60).duration(320)} style={styles.card}>
      <Text style={styles.heading}>Ваші можливості PRO</Text>

      <SectionLabel>Оформлення</SectionLabel>
      <MemberRow icon="color-palette-outline" title="Тема чату" subtitle={themeLabel} onPress={onThemePress} />
      <Hairline />
      <MemberRow
        icon="scan-outline"
        title="Анімована аватарка"
        subtitle={animAvatar ? 'Увімкнено' : 'Вимкнено'}
        trailing={
          <Switch
            value={animAvatar}
            onValueChange={onAnimAvatarChange}
            trackColor={{ false: paywall.border, true: paywall.accentMuted }}
            thumbColor={animAvatar ? paywall.accent : paywall.textFaint}
          />
        }
      />

      <SectionLabel>Інструменти</SectionLabel>
      <MemberRow
        icon="time-outline"
        title="Історія тривог"
        subtitle="Журнал подій"
        onPress={() => navigation.navigate('AlarmHistory')}
      />
      <Hairline />
      <MemberRow
        icon="stats-chart-outline"
        title="Аналітика"
        subtitle="Час під тривогою"
        onPress={() => navigation.navigate('PersonalAnalytics')}
      />
      <Hairline />
      <MemberRow
        icon="flame-outline"
        title="Теплова карта"
        subtitle="Активність по регіонах"
        onPress={() => navigation.navigate('Heatmap')}
      />
      <Hairline />
      <MemberRow
        icon="moon-outline"
        title="Режим сну"
        subtitle="Тихі години"
        onPress={() => navigation.navigate('SleepMode')}
      />
      <Hairline />
      <MemberRow
        icon="volume-high-outline"
        title="Звук тривоги"
        subtitle="У профілі"
        onPress={onProfileSounds}
      />

      <Text style={styles.themesHint}>
        Доступно {CHAT_THEMES.length} тем чату — оберіть у пункті «Тема чату».
      </Text>
    </Animated.View>
  );
}

function SectionLabel({ children }: { children: string }) {
  return <Text style={styles.sectionLabel}>{children.toUpperCase()}</Text>;
}

function Hairline() {
  return <View style={styles.hairline} />;
}

function MemberRow({
  icon,
  title,
  subtitle,
  onPress,
  trailing,
}: {
  icon: ComponentProps<typeof Ionicons>['name'];
  title: string;
  subtitle: string;
  onPress?: () => void;
  trailing?: ReactNode;
}) {
  const content = (
    <View style={styles.row}>
      <View style={styles.iconPlate}>
        <Ionicons name={icon} size={19} color={paywall.accentSoft} />
      </View>
      <View style={styles.rowCopy}>
        <Text style={styles.rowTitle}>{title}</Text>
        <Text style={styles.rowSub}>{subtitle}</Text>
      </View>
      {trailing ?? (onPress ? <Ionicons name="chevron-forward" size={18} color={paywall.textFaint} /> : null)}
    </View>
  );

  if (!onPress || trailing) return content;
  return (
    <NeptunPressable haptic onPress={onPress}>
      {content}
    </NeptunPressable>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: paywall.radiusCard,
    backgroundColor: paywall.surface,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: paywall.border,
    overflow: 'hidden',
    ...paywall.shadows.sm,
  },
  heading: {
    fontFamily: fonts.bold,
    fontSize: 17,
    color: paywall.text,
    paddingHorizontal: 18,
    paddingTop: 18,
    paddingBottom: 8,
  },
  sectionLabel: {
    paddingHorizontal: 18,
    paddingTop: 14,
    paddingBottom: 6,
    fontFamily: fonts.bold,
    fontSize: 11,
    letterSpacing: 1.1,
    color: paywall.textFaint,
  },
  hairline: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: paywall.divider,
    marginLeft: 62,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 14,
    gap: 12,
  },
  iconPlate: {
    width: 36,
    height: 36,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: paywall.accentMuted,
  },
  rowCopy: { flex: 1 },
  rowTitle: {
    fontFamily: fonts.semiBold,
    fontSize: 15,
    color: paywall.text,
  },
  rowSub: {
    marginTop: 2,
    fontSize: 12,
    color: paywall.textMuted,
    lineHeight: 16,
  },
  themesHint: {
    paddingHorizontal: 18,
    paddingVertical: 14,
    fontSize: 12,
    lineHeight: 18,
    color: paywall.textFaint,
    textAlign: 'center',
  },
});

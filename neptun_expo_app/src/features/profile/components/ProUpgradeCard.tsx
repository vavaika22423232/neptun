import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import Svg, { Circle, Defs, Pattern, Rect } from 'react-native-svg';
import { Text } from '../../../components/Text';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { fonts } from '../../../theme/fonts';
import { useAppTheme, useThemedStyles } from '../../../theme/useAppTheme';
import { useProAccess } from '../../pro/hooks/useProAccess';
import { profileTokens } from '../profileTokens';

type Props = {
  onPress?: () => void;
};

const PRO_GOLD = '#FACC15';
const PRO_GOLD_GLOW = 'rgba(250, 204, 21, 0.34)';

function ProBannerDotGrid({ light }: { light: boolean }) {
  return (
    <Svg width="100%" height="100%" style={StyleSheet.absoluteFill}>
      <Defs>
        <Pattern id="proDots" width={14} height={14} patternUnits="userSpaceOnUse">
          <Circle cx={1.5} cy={1.5} r={1} fill={light ? 'rgba(0,0,0,0.06)' : 'rgba(255,255,255,0.07)'} />
        </Pattern>
      </Defs>
      <Rect width="100%" height="100%" fill="url(#proDots)" />
    </Svg>
  );
}

function ProBannerIcon({ name, glowColor }: { name: 'flash' | 'star'; glowColor: string }) {
  const styles = useIconStyles();
  return (
    <View style={styles.wrap}>
      <View style={[styles.glow, { backgroundColor: glowColor }]} />
      <Ionicons name={name} size={26} color={PRO_GOLD} style={styles.icon} />
    </View>
  );
}

function ProBannerCta({ dark }: { dark: boolean }) {
  const styles = useCtaStyles(dark);
  return (
    <View style={styles.circle}>
      <Ionicons name="chevron-forward" size={18} color={dark ? '#111111' : '#5C4A00'} />
    </View>
  );
}

function ProUpgradeCardInner({ onPress }: Props) {
  const { isPaid, plan, entitlements, openPaywall } = useProAccess();
  const { theme } = useAppTheme();
  const isLight = theme.scheme === 'light';
  const styles = useCardStyles(isLight);
  const gradient = isLight
    ? (['#FFF6D6', '#FFE39A'] as const)
    : (['#151821', '#0A0C11'] as const);
  const handlePress = onPress ?? (() => openPaywall({ source: 'profile' }));

  if (isPaid) {
    const planLabel = plan === 'max' ? 'MAX' : plan === 'pro_plus' ? 'PRO+' : 'PRO';
    const status = entitlements.expiresAt
      ? `Активний до ${new Date(entitlements.expiresAt).toLocaleDateString('uk-UA')}`
      : 'Підписка активна';

    return (
      <NeptunPressable haptic onPress={handlePress} style={styles.pressWrap}>
        <LinearGradient
          colors={gradient}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={styles.banner}
        >
          <ProBannerDotGrid light={isLight} />
          <View style={styles.radialGlow} />
          <View style={styles.row}>
            <ProBannerIcon name="star" glowColor="rgba(250, 204, 21, 0.28)" />
            <View style={styles.copy}>
              <Text style={styles.title}>NEPTUN PRO · {planLabel}</Text>
              <Text style={styles.status}>{status}</Text>
            </View>
            <ProBannerCta dark={!isLight} />
          </View>
        </LinearGradient>
      </NeptunPressable>
    );
  }

  return (
    <NeptunPressable haptic onPress={handlePress} style={styles.pressWrap}>
      <LinearGradient
        colors={gradient}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={styles.banner}
      >
        <ProBannerDotGrid light={isLight} />
        <View style={styles.radialGlow} />
        <View style={styles.row}>
          <ProBannerIcon name="flash" glowColor={PRO_GOLD_GLOW} />
          <View style={styles.copy}>
            <Text style={styles.title}>NEPTUN PRO</Text>
          </View>
          <ProBannerCta dark={!isLight} />
        </View>
      </LinearGradient>
    </NeptunPressable>
  );
}

function useCardStyles(isLight: boolean) {
  return useThemedStyles((t) =>
    StyleSheet.create({
      pressWrap: {
        marginHorizontal: profileTokens.insetH,
        borderRadius: 24,
        overflow: 'hidden',
        shadowColor: '#000000',
        shadowOpacity: isLight ? 0.08 : 0.28,
        shadowRadius: isLight ? 10 : 16,
        shadowOffset: { width: 0, height: isLight ? 4 : 8 },
        elevation: isLight ? 2 : 8,
      },
      banner: {
        minHeight: 76,
        paddingHorizontal: 18,
        paddingVertical: 16,
        borderRadius: 24,
        overflow: 'hidden',
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: isLight ? 'rgba(92,74,0,0.12)' : 'rgba(255,255,255,0.06)',
      },
      radialGlow: {
        position: 'absolute',
        left: 8,
        top: '50%',
        width: 88,
        height: 88,
        marginTop: -44,
        borderRadius: 44,
        backgroundColor: isLight ? 'rgba(255,255,255,0.35)' : 'rgba(255,255,255,0.04)',
      },
      row: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 14,
      },
      copy: {
        flex: 1,
        minWidth: 0,
        justifyContent: 'center',
      },
      title: {
        fontFamily: fonts.bold,
        fontSize: 18,
        lineHeight: 22,
        color: isLight ? t.colors.premiumDeep : '#FFFFFF',
        letterSpacing: -0.2,
      },
      status: {
        marginTop: 4,
        fontFamily: fonts.regular,
        fontSize: 13,
        lineHeight: 18,
        color: isLight ? 'rgba(92,74,0,0.72)' : 'rgba(235,235,245,0.62)',
      },
    }),
  );
}

function useIconStyles() {
  return useThemedStyles(() =>
    StyleSheet.create({
      wrap: {
        width: 44,
        height: 44,
        alignItems: 'center',
        justifyContent: 'center',
      },
      glow: {
        position: 'absolute',
        width: 38,
        height: 38,
        borderRadius: 19,
      },
      icon: {
        textShadowColor: PRO_GOLD_GLOW,
        textShadowOffset: { width: 0, height: 0 },
        textShadowRadius: 10,
      },
    }),
  );
}

function useCtaStyles(dark: boolean) {
  return useThemedStyles(() =>
    StyleSheet.create({
      circle: {
        width: 40,
        height: 40,
        borderRadius: 20,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: dark ? '#FFFFFF' : 'rgba(255,255,255,0.88)',
      },
    }),
  );
}

export const ProUpgradeCard = memo(ProUpgradeCardInner);

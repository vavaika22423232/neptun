import { Ionicons } from '@expo/vector-icons';
import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import { Text } from '../../../components/Text';
import { useThemedStyles } from '../../../theme/useAppTheme';
import { fonts } from '../../../theme/fonts';
import { getPaywallTokens, usePaywallTheme } from '../../premium/theme/paywallTokens';
import { LOCKED_FEATURES, PRO_HERO_BENEFITS, type LockedFeatureId } from '../utils/proFeatures';

type Props = {
  lockedFeature?: string;
};

function ProPaywallContextInner({ lockedFeature }: Props) {
  const paywall = usePaywallTheme();
  const styles = usePaywallContextStyles();
  const spec =
    lockedFeature && lockedFeature in LOCKED_FEATURES
      ? LOCKED_FEATURES[lockedFeature as LockedFeatureId]
      : null;

  return (
    <View style={styles.root}>
      <Text style={styles.title}>NEPTUN PRO</Text>
      <Text style={styles.sub}>
        Менше реклами. Більше контролю. Швидші сповіщення.
      </Text>

      {spec ? (
        <View style={styles.lockBox}>
          <Ionicons name="lock-open-outline" size={18} color={paywall.accent} />
          <View style={styles.lockCopy}>
            <Text style={styles.lockTitle}>{spec.label}</Text>
            <Text style={styles.lockSub}>{spec.subtitle}</Text>
          </View>
        </View>
      ) : null}

      <View style={styles.grid}>
        {PRO_HERO_BENEFITS.map((b) => (
          <View key={b.text} style={styles.cell}>
            <Ionicons name={b.icon} size={18} color={paywall.accent} />
            <Text style={styles.cellText}>{b.text}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}

function usePaywallContextStyles() {
  return useThemedStyles((t) => {
    const pw = getPaywallTokens(t);
    return StyleSheet.create({
      root: { gap: 12, marginBottom: 8 },
      title: {
        fontFamily: fonts.bold,
        fontSize: 26,
        color: pw.text,
        letterSpacing: -0.3,
      },
      sub: {
        fontFamily: fonts.medium,
        fontSize: 15,
        lineHeight: 22,
        color: pw.textMuted,
      },
      lockBox: {
        flexDirection: 'row',
        alignItems: 'flex-start',
        gap: 10,
        padding: 12,
        borderRadius: pw.radiusCard,
        backgroundColor: pw.accentMuted,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: pw.border,
      },
      lockCopy: { flex: 1, gap: 2 },
      lockTitle: {
        fontFamily: fonts.semiBold,
        fontSize: 14,
        color: pw.text,
      },
      lockSub: {
        fontFamily: fonts.regular,
        fontSize: 13,
        color: pw.textMuted,
      },
      grid: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        gap: 8,
      },
      cell: {
        width: '48%',
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        padding: 10,
        borderRadius: 12,
        backgroundColor: pw.surface,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: pw.border,
      },
      cellText: {
        flex: 1,
        fontFamily: fonts.medium,
        fontSize: 12,
        color: pw.textSoft,
      },
    });
  });
}

export const ProPaywallContext = memo(ProPaywallContextInner);

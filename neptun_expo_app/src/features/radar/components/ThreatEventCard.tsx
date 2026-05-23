import { Ionicons } from '@expo/vector-icons';
import { memo } from 'react';
import { voidHapticImpact } from '../../../utils/lazyExpoNative';
import { Pressable, StyleSheet, View } from 'react-native';
import { Text } from '../../../components/Text';
import { radarThreatIconName } from '../domain/radarThreatIcon';
import { formatRelativeTime } from '../utils/radarFormatters';
import type { ThreatEvent, ThreatSeverity } from '../types/radar.types';
import { useAppTheme, useThemedStyles } from '../../../theme/useAppTheme';
import { fonts } from '../../../theme/fonts';

type Props = {
  event: ThreatEvent;
  onPress: () => void;
  isLast?: boolean;
};

function ThreatEventCardInner({ event, onPress, isLast }: Props) {
  const { theme } = useAppTheme();
  const r = theme.radar;

  const severityColor = (s: ThreatSeverity): string => {
    switch (s) {
      case 'critical':
        return theme.colors.threatCritical;
      case 'high':
        return theme.colors.threatHigh;
      case 'medium':
        return theme.colors.threatMedium;
      default:
        return theme.colors.threatLow;
    }
  };

  const color = severityColor(event.severity);
  const sourceLabel =
    event.source === 'telegram'
      ? 'Telegram'
      : event.source === 'official'
        ? 'Офіційно'
        : event.source === 'userReport'
          ? 'Звіт'
          : 'Система';
  const subtitle =
    event.locations.length > 0
      ? event.locations[0]
      : event.relatedMessages[0]?.trim() || 'Локація уточнюється';

  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      pressPressed: { opacity: 0.72 },
      row: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
        paddingHorizontal: t.radar.cardPad,
        paddingVertical: 12,
        borderBottomWidth: isLast ? 0 : StyleSheet.hairlineWidth,
        borderBottomColor: t.colors.divider,
      },
      iconBox: {
        width: 40,
        height: 40,
        borderRadius: 12,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: t.scheme === 'light' ? '#F2F2F7' : 'rgba(255,255,255,0.08)',
      },
      body: { flex: 1, minWidth: 0 },
      titleRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
      title: {
        fontFamily: fonts.semiBold,
        fontSize: 15,
        lineHeight: 20,
        color: t.colors.textPrimary,
        flexShrink: 1,
      },
      subtitle: {
        fontFamily: fonts.regular,
        fontSize: 14,
        lineHeight: 19,
        color: t.colors.textSecondary,
        marginTop: 2,
      },
      meta: {
        fontFamily: fonts.regular,
        fontSize: 12,
        lineHeight: 16,
        color: t.colors.textMuted,
        marginTop: 4,
      },
      badge: {
        paddingHorizontal: 6,
        paddingVertical: 2,
        borderRadius: 6,
      },
      badgeText: {
        fontFamily: fonts.semiBold,
        fontSize: 10,
        letterSpacing: 0.2,
      },
      chevron: {
        width: 28,
        height: 28,
        borderRadius: 14,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: t.scheme === 'light' ? '#F2F2F7' : 'rgba(255,255,255,0.08)',
      },
    }),
  );

  return (
    <Pressable
      onPress={() => {
        voidHapticImpact('light');
        onPress();
      }}
      style={({ pressed }) => [pressed && styles.pressPressed]}
    >
      <View style={styles.row}>
        <View style={styles.iconBox}>
          <Ionicons name={radarThreatIconName(event.categoryKey)} size={20} color={color} />
        </View>
        <View style={styles.body}>
          <View style={styles.titleRow}>
            <Text style={styles.title} numberOfLines={1}>
              {event.title}
            </Text>
            {event.isNew ? <Badge label="NEW" color={r.live} styles={styles} /> : null}
            {event.isFollowed ? <Ionicons name="bookmark" size={13} color={theme.colors.textMuted} /> : null}
          </View>
          <Text style={styles.subtitle} numberOfLines={1}>
            {subtitle}
          </Text>
          <Text style={styles.meta} numberOfLines={1}>
            {formatRelativeTime(event.updatedAt)}
            {event.signalCount > 1 ? ` · ${event.signalCount} сигн.` : ''}
            {' · '}
            {sourceLabel}
            {event.confidence != null ? ` · ${event.confidence}%` : ''}
          </Text>
        </View>
        <View style={styles.chevron}>
          <Ionicons name="chevron-forward" size={16} color={theme.colors.textMuted} />
        </View>
      </View>
    </Pressable>
  );
}

function Badge({
  label,
  color,
  styles,
}: {
  label: string;
  color: string;
  styles: { badge: object; badgeText: object };
}) {
  return (
    <View style={[styles.badge, { backgroundColor: color + '22' }]}>
      <Text style={[styles.badgeText, { color }]}>{label}</Text>
    </View>
  );
}

function propsAreEqual(prev: Props, next: Props): boolean {
  const a = prev.event;
  const b = next.event;
  return (
    prev.isLast === next.isLast &&
    a.id === b.id &&
    a.updatedAt === b.updatedAt &&
    a.signalCount === b.signalCount &&
    a.isNew === b.isNew &&
    a.isFollowed === b.isFollowed &&
    a.title === b.title &&
    a.locations.join('|') === b.locations.join('|')
  );
}

export const ThreatEventCard = memo(ThreatEventCardInner, propsAreEqual);

import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { voidHapticImpact } from '../../../utils/lazyExpoNative';
import { useRouter } from 'expo-router';
import { Share, StyleSheet, View } from 'react-native';

type IonName = ComponentProps<typeof Ionicons>['name'];
import { NeptunBottomSheet } from '../../../components/NeptunBottomSheet';
import { PrimaryButton } from '../../../components/PrimaryButton';
import { Text } from '../../../components/Text';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { formatRelativeTime } from '../utils/radarFormatters';
import type { ThreatEvent } from '../types/radar.types';
import { fonts } from '../../../theme/fonts';
import { useAppTheme, useThemedStyles } from '../../../theme/useAppTheme';
import { useEntitlements } from '../../monetization/hooks/useEntitlements';

type Props = {
  event: ThreatEvent | null;
  visible: boolean;
  onClose: () => void;
  onFollow: () => void;
  onMute: () => void;
};

export function ThreatDetailsSheet({ event, visible, onClose, onFollow, onMute }: Props) {
  const router = useRouter();
  const { features, hasPlan } = useEntitlements();
  const { theme } = useAppTheme();
  const r = theme.radar;
  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      header: { marginBottom: 12 },
      title: { fontFamily: fonts.bold, fontSize: 20, color: t.radar.text },
      sub: { fontFamily: fonts.medium, fontSize: 14, color: t.radar.textSecondary, marginTop: 4 },
      badges: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 16 },
      chip: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        paddingHorizontal: 10,
        paddingVertical: 6,
        borderRadius: 12,
        backgroundColor: t.colors.primaryMuted,
      },
      chipText: { fontFamily: fonts.semiBold, fontSize: 12, color: t.radar.textSecondary },
      timeline: { marginBottom: 16 },
      sectionTitle: {
        fontFamily: fonts.bold,
        fontSize: 13,
        color: t.radar.textMuted,
        letterSpacing: 0.4,
        marginBottom: 8,
      },
      timelineRow: { marginBottom: 12 },
      timelineTime: { fontFamily: fonts.semiBold, fontSize: 11, color: t.radar.textMuted },
      timelineTitle: {
        fontFamily: fonts.semiBold,
        fontSize: 13,
        color: t.radar.text,
        marginTop: 2,
      },
      timelineBody: { fontFamily: fonts.medium, fontSize: 13, color: t.radar.textSecondary, marginTop: 2 },
      actions: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 16 },
      actionBtn: {
        alignItems: 'center',
        justifyContent: 'center',
        minWidth: 72,
        padding: 10,
        borderRadius: 14,
        backgroundColor: t.radar.card,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.radar.border,
      },
      actionLabel: { fontFamily: fonts.semiBold, fontSize: 11, color: t.radar.textSecondary, marginTop: 4 },
    }),
  );

  if (!event) return null;

  const shareBody = `${event.title}\n${event.locations.join(', ')}\n${formatRelativeTime(event.updatedAt)}`;

  return (
    <NeptunBottomSheet visible={visible} onClose={onClose} maxHeightRatio={0.72}>
      <View style={styles.header}>
        <Text style={styles.title}>{event.title}</Text>
        <Text style={styles.sub}>{event.locations.join(', ') || '—'}</Text>
      </View>

      <View style={styles.badges}>
        <MetaChip icon="time-outline" label={formatRelativeTime(event.updatedAt)} styles={styles} muted={r.textMuted} />
        {event.signalCount > 1 ? (
          <MetaChip icon="pulse-outline" label={`${event.signalCount} точок треку`} styles={styles} muted={r.textMuted} />
        ) : null}
        {event.confidence != null ? (
          <MetaChip icon="shield-checkmark-outline" label={`${event.confidence}%`} styles={styles} muted={r.textMuted} />
        ) : null}
      </View>

      {features.extendedThreatCard && hasPlan('pro_plus') ? (
        <View style={styles.timeline}>
          <Text style={styles.sectionTitle}>Розширена картка (PRO+)</Text>
          <Text style={styles.timelineBody}>
            За наявними даними можливий напрямок руху уточнюється. Інформація оновлюється.
          </Text>
          {event.locations.length > 1 ? (
            <Text style={styles.timelineBody}>Пов’язані регіони: {event.locations.join(', ')}</Text>
          ) : null}
        </View>
      ) : null}

      {event.timeline.length > 0 ? (
        <View style={styles.timeline}>
          <Text style={styles.sectionTitle}>
            {event.timeline.length > 1 ? 'Хронологія' : 'Деталі'}
          </Text>
          {[...event.timeline]
            .sort((a, b) => (b.at ?? 0) - (a.at ?? 0))
            .slice(0, features.extendedThreatCard && hasPlan('pro_plus') ? 24 : 8)
            .map((item) => (
              <View key={item.id} style={styles.timelineRow}>
                <Text style={styles.timelineTime}>{item.time}</Text>
                <Text style={styles.timelineTitle} numberOfLines={1}>
                  {item.title}
                </Text>
                {item.description ? (
                  <Text style={styles.timelineBody} numberOfLines={3}>
                    {item.description}
                  </Text>
                ) : null}
              </View>
            ))}
        </View>
      ) : null}

      <View style={styles.actions}>
        <ActionBtn
          icon="map-outline"
          label="Показати на карті"
          styles={styles}
          muted={r.textSecondary}
          onPress={() => {
            onClose();
            router.push('/(tabs)');
          }}
        />
        <ActionBtn
          icon={event.isFollowed ? 'bookmark' : 'bookmark-outline'}
          label={event.isFollowed ? 'Стежу' : 'Стежити'}
          styles={styles}
          muted={r.textSecondary}
          onPress={() => {
            voidHapticImpact('medium');
            onFollow();
          }}
        />
        <ActionBtn
          icon="notifications-outline"
          label="Сповістити мене"
          styles={styles}
          muted={r.textSecondary}
          onPress={() => {
            onClose();
            router.push('/(tabs)/regions');
          }}
        />
        <ActionBtn icon="volume-mute-outline" label="Заглушити" styles={styles} muted={r.textSecondary} onPress={onMute} />
      </View>

      {!features.extendedThreatCard && !hasPlan('pro_plus') ? (
        <PrimaryButton variant="secondary" onPress={() => router.push('/premium')}>
          Розширена картка — PRO+
        </PrimaryButton>
      ) : null}

      <PrimaryButton onPress={() => void Share.share({ message: shareBody })}>Поділитися</PrimaryButton>
    </NeptunBottomSheet>
  );
}

function MetaChip({
  icon,
  label,
  styles,
  muted,
}: {
  icon: IonName;
  label: string;
  styles: { chip: object; chipText: object };
  muted: string;
}) {
  return (
    <View style={styles.chip}>
      <Ionicons name={icon} size={14} color={muted} />
      <Text style={styles.chipText}>{label}</Text>
    </View>
  );
}

function ActionBtn({
  icon,
  label,
  onPress,
  styles,
  muted,
}: {
  icon: IonName;
  label: string;
  onPress: () => void;
  styles: { actionBtn: object; actionLabel: object };
  muted: string;
}) {
  return (
    <NeptunPressable haptic onPress={onPress} style={styles.actionBtn}>
      <Ionicons name={icon} size={20} color={muted} />
      <Text style={styles.actionLabel}>{label}</Text>
    </NeptunPressable>
  );
}

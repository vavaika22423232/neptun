import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { memo, useCallback } from 'react';
import { Platform, Pressable, StyleSheet, View } from 'react-native';
import { useRouter } from 'expo-router';
import { NeptunBottomSheet } from '../../../components/NeptunBottomSheet';
import { AppText } from '../../../components/ui/AppText';
import { ProFeature, ProGate } from '../../../core/pro/proGate';
import { useApp } from '../../../context/AppContext';
import { useAppTheme, useThemedStyles } from '../../../theme/useAppTheme';
import { useMapStore } from '../state/mapStore';

const MAP_ENGINE = (process.env.EXPO_PUBLIC_MAP_ENGINE ?? 'embed').toLowerCase();
const showNativeLayers = MAP_ENGINE === 'native' && Platform.OS !== 'web';

type LayerRowProps = {
  icon: ComponentProps<typeof Ionicons>['name'];
  label: string;
  hint?: string;
  active: boolean;
  locked?: boolean;
  onPress: () => void;
};

function LayerRow({ icon, label, hint, active, locked, onPress }: LayerRowProps) {
  const { theme } = useAppTheme();
  const styles = useLayerRowStyles();

  return (
    <Pressable
      onPress={onPress}
      style={[styles.row, active && styles.rowActive]}
      accessibilityRole="switch"
      accessibilityState={{ checked: active }}
    >
      <View style={[styles.iconWrap, active && { backgroundColor: theme.colors.primaryMuted }]}>
        <Ionicons
          name={icon}
          size={20}
          color={active ? theme.colors.primary : theme.colors.textMuted}
        />
      </View>
      <View style={styles.copy}>
        <AppText variant="cardTitle">{label}</AppText>
        {hint ? (
          <AppText variant="meta" muted>
            {hint}
          </AppText>
        ) : null}
      </View>
      {locked ? (
        <AppText variant="meta" accent>
          PRO
        </AppText>
      ) : (
        <Ionicons
          name={active ? 'checkmark-circle' : 'ellipse-outline'}
          size={22}
          color={active ? theme.colors.primary : theme.colors.textMuted}
        />
      )}
    </Pressable>
  );
}

function MapLayerSheetInner() {
  const router = useRouter();
  const { isPremium } = useApp();
  const styles = useSheetStyles();

  const visible = useMapStore((s) => s.layerSheetVisible);
  const setVisible = useMapStore((s) => s.setLayerSheetVisible);
  const counts = useMapStore((s) => s.counts);
  const visibleThreatTypes = useMapStore((s) => s.visibleThreatTypes);
  const showOblastAlarms = useMapStore((s) => s.showOblastAlarms);
  const showTrajectories = useMapStore((s) => s.showTrajectories);
  const toggleThreatType = useMapStore((s) => s.toggleThreatType);
  const toggleOblastAlarms = useMapStore((s) => s.toggleOblastAlarms);
  const toggleTrajectories = useMapStore((s) => s.toggleTrajectories);

  const onClose = useCallback(() => setVisible(false), [setVisible]);

  const onToggleTrajectories = useCallback(() => {
    if (!showTrajectories && !ProGate.isUnlockedSync(ProFeature.Trajectories, isPremium)) {
      onClose();
      router.push('/premium');
      return;
    }
    toggleTrajectories();
  }, [showTrajectories, isPremium, router, toggleTrajectories, onClose]);

  const threatTypes = Object.keys(counts).length > 0 ? Object.keys(counts) : Object.keys(visibleThreatTypes);

  return (
    <NeptunBottomSheet visible={visible} onClose={onClose} maxHeightRatio={0.55}>
      <AppText variant="sectionTitle" style={styles.title}>
        Шари карти
      </AppText>
      <AppText variant="meta" muted style={styles.subtitle}>
        Оберіть, що показувати на карті
      </AppText>

      {showNativeLayers ? (
        <View style={styles.group}>
          <AppText variant="meta" muted style={styles.groupLabel}>
            Регіони
          </AppText>
          <LayerRow
            icon="map-outline"
            label="Тривоги областей"
            hint="Підсвітка областей з активною тривогою"
            active={showOblastAlarms}
            onPress={toggleOblastAlarms}
          />
          <LayerRow
            icon="git-branch-outline"
            label="Траєкторії"
            hint="Прогнозовані маршрути загроз"
            active={showTrajectories}
            locked={!ProGate.isUnlockedSync(ProFeature.Trajectories, isPremium)}
            onPress={onToggleTrajectories}
          />
        </View>
      ) : null}

      <View style={styles.group}>
        <AppText variant="meta" muted style={styles.groupLabel}>
          Типи загроз
        </AppText>
        {threatTypes.map((type) => {
          const active = visibleThreatTypes[type] ?? true;
          const count = counts[type] ?? 0;
          return (
            <LayerRow
              key={type}
              icon="radio-button-on-outline"
              label={type}
              hint={count > 0 ? `${count} на карті` : undefined}
              active={active}
              onPress={() => toggleThreatType(type)}
            />
          );
        })}
      </View>
    </NeptunBottomSheet>
  );
}

function useSheetStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      title: { marginBottom: 4 },
      subtitle: { marginBottom: t.spacing.lg },
      group: { gap: 8, marginBottom: t.spacing.lg },
      groupLabel: {
        textTransform: 'uppercase',
        letterSpacing: 0.6,
        marginBottom: 4,
      },
    }),
  );
}

function useLayerRowStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      row: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
        padding: 12,
        borderRadius: t.radii.lg,
        backgroundColor: t.colors.surfaceSoft,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.colors.border,
      },
      rowActive: {
        borderColor: t.colors.primary + '55',
        backgroundColor: t.colors.primarySoft,
      },
      iconWrap: {
        width: 40,
        height: 40,
        borderRadius: 12,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: t.colors.surfaceHighlight,
      },
      copy: { flex: 1, gap: 2 },
    }),
  );
}

export const MapLayerSheet = memo(MapLayerSheetInner);

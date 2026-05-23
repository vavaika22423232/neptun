import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Linking,
  Modal,
  Pressable,
  StyleSheet,
  View,
} from 'react-native';
import { Text } from '../components/Text';
import { SHELTER_CITY_COORDINATES } from '../features/shelters/constants/cityCoordinates';
import {
  getShelterCurrentPosition,
  isShelterLocationAvailable,
  requestShelterForegroundPermission,
} from '../features/shelters/services/shelterLocation';
import {
  fetchNearbyShelters,
  formatShelterDistance,
  shelterMapsDirectionsUrl,
  type Shelter,
} from '../features/shelters/services/shelterOverpassService';
import { colors, radii, spacing } from '../theme/colors';
import { fonts } from '../theme/fonts';
import { useLegacyScreenStyles } from '../theme/useLegacyScreenStyles';

const SHELTER_ICON: Record<Shelter['type'], ComponentProps<typeof Ionicons>['name']> = {
  shelter: 'home',
  bunker: 'shield',
  metro: 'train',
  transit: 'bus',
};

/** Flutter `SheltersPage`. */
export function SheltersScreen() {
  const styles = useScreenStyles();
  const [shelters, setShelters] = useState<Shelter[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cityName, setCityName] = useState<string | null>(null);
  const [origin, setOrigin] = useState<{ lat: number; lon: number } | null>(null);
  const [cityPicker, setCityPicker] = useState(false);

  const loadAt = useCallback(async (lat: number, lon: number) => {
    setLoading(true);
    setError(null);
    setOrigin({ lat, lon });
    try {
      const list = await fetchNearbyShelters(lat, lon);
      setShelters(list);
    } catch (e) {
      setShelters([]);
      setError(e instanceof Error ? e.message : 'Помилка завантаження укриттів');
    } finally {
      setLoading(false);
    }
  }, []);

  const initGps = useCallback(async () => {
    setLoading(true);
    setError(null);
    setCityName(null);
    if (!isShelterLocationAvailable()) {
      setError(
        'Геолокація недоступна. Перезберіть dev client: npx expo prebuild --clean && npx expo run:ios --device',
      );
      setLoading(false);
      return;
    }
    try {
      const perm = await requestShelterForegroundPermission();
      if (perm.unavailable) {
        setError('Геолокація недоступна в цій збірці');
        setLoading(false);
        return;
      }
      if (!perm.granted) {
        setError('Для пошуку укриттів потрібен доступ до геолокації');
        setLoading(false);
        return;
      }
      const pos = await getShelterCurrentPosition();
      if (pos.unavailable) {
        setError('Геолокація недоступна в цій збірці');
        setLoading(false);
        return;
      }
      await loadAt(pos.lat, pos.lon);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не вдалося отримати позицію');
      setLoading(false);
    }
  }, [loadAt]);

  useEffect(() => {
    void initGps();
  }, [initGps]);

  const searchCity = (name: string) => {
    const coords = SHELTER_CITY_COORDINATES[name];
    if (!coords) return;
    setCityName(name);
    setCityPicker(false);
    void loadAt(coords.lat, coords.lon);
  };

  const openDirections = (shelter: Shelter) => {
    if (!origin) return;
    const url = shelterMapsDirectionsUrl(origin.lat, origin.lon, shelter.latitude, shelter.longitude);
    void Linking.openURL(url);
  };

  const title = cityName ? `Укриття: ${cityName}` : 'Укриття поруч';

  return (
    <View style={styles.root}>
      <View style={styles.toolbar}>
        <Text style={styles.toolbarTitle}>{title}</Text>
        <View style={styles.toolbarActions}>
          <Pressable onPress={() => setCityPicker(true)} style={styles.iconBtn}>
            <Ionicons name="business" size={22} color={colors.text} />
          </Pressable>
          <Pressable onPress={() => void initGps()} style={styles.iconBtn}>
            <Ionicons name="refresh" size={22} color={colors.text} />
          </Pressable>
        </View>
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator color={colors.accent} size="large" />
          <Text muted style={styles.statusText}>
            Шукаємо укриття поруч...
          </Text>
        </View>
      ) : error && shelters.length === 0 ? (
        <View style={styles.center}>
          <Ionicons name="alert-circle" size={48} color={colors.warning} />
          <Text style={styles.errorText}>{error}</Text>
          <Pressable onPress={() => setCityPicker(true)} style={styles.retryBtn}>
            <Text style={styles.retryText}>Обрати місто</Text>
          </Pressable>
          <Pressable onPress={() => void initGps()} style={styles.retryBtn}>
            <Text style={styles.retryText}>Спробувати GPS</Text>
          </Pressable>
        </View>
      ) : (
        <FlatList
          data={shelters}
          keyExtractor={(item) => `${item.latitude}_${item.longitude}_${item.name}`}
          contentContainerStyle={styles.list}
          renderItem={({ item }) => (
            <Pressable onPress={() => openDirections(item)} style={({ pressed }) => [styles.row, pressed && styles.pressed]}>
              <View style={styles.rowIcon}>
                <Ionicons name={SHELTER_ICON[item.type]} size={22} color={colors.accent} />
              </View>
              <View style={styles.flex}>
                <Text style={styles.rowTitle}>{item.name}</Text>
                <Text muted style={styles.rowSub}>
                  {formatShelterDistance(item.distanceM)}
                </Text>
              </View>
              <Ionicons name="navigate" size={20} color={colors.accent2} />
            </Pressable>
          )}
          ListEmptyComponent={
            <Text muted style={styles.statusText}>
              Укриття не знайдено
            </Text>
          }
        />
      )}

      <Modal visible={cityPicker} animationType="slide" transparent onRequestClose={() => setCityPicker(false)}>
        <Pressable style={styles.modalBackdrop} onPress={() => setCityPicker(false)}>
          <View style={styles.citySheet}>
            <Text style={styles.cityTitle}>Оберіть місто для пошуку укриттів</Text>
            <FlatList
              data={Object.keys(SHELTER_CITY_COORDINATES)}
              keyExtractor={(n) => n}
              renderItem={({ item }) => (
                <Pressable onPress={() => searchCity(item)} style={styles.cityRow}>
                  <Ionicons name="location" size={18} color={colors.accent} />
                  <Text style={styles.cityName}>{item}</Text>
                </Pressable>
              )}
            />
          </View>
        </Pressable>
      </Modal>
    </View>
  );
}


function useScreenStyles() {
  return useLegacyScreenStyles((c) => ({
  root: { flex: 1, backgroundColor: c.bg },
  toolbar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: c.border,
  },
  toolbarTitle: { flex: 1, fontFamily: fonts.bold, fontSize: 18, color: c.text },
  toolbarActions: { flexDirection: 'row', gap: 4 },
  iconBtn: { padding: 8 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32, gap: 12 },
  statusText: { marginTop: 8, textAlign: 'center' },
  errorText: { textAlign: 'center', color: c.text, fontFamily: fonts.semiBold },
  retryBtn: { marginTop: 8, paddingVertical: 10, paddingHorizontal: 16 },
  retryText: { color: c.accent, fontFamily: fonts.bold },
  list: { padding: spacing.md, gap: 10 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 14,
    borderRadius: radii.md,
    backgroundColor: c.surface,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: c.border,
  },
  pressed: { opacity: 0.9 },
  rowIcon: {
    width: 40,
    height: 40,
    borderRadius: 10,
    backgroundColor: 'rgba(76,201,240,0.12)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  flex: { flex: 1 },
  rowTitle: { fontFamily: fonts.semiBold, fontSize: 15 },
  rowSub: { fontSize: 13, marginTop: 2 },
  modalBackdrop: { flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(0,0,0,0.5)' },
  citySheet: {
    maxHeight: '70%',
    backgroundColor: c.surface,
    borderTopLeftRadius: radii.xl,
    borderTopRightRadius: radii.xl,
    padding: spacing.lg,
  },
  cityTitle: { fontFamily: fonts.bold, fontSize: 16, marginBottom: 12 },
  cityRow: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 12 },
  cityName: { fontSize: 16 },
}));
}

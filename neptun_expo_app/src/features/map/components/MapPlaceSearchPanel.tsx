import { Ionicons } from '@expo/vector-icons';
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  StyleSheet,
  TextInput,
  View,
} from 'react-native';
import { Text } from '../../../components/Text';
import { fonts } from '../../../theme/fonts';
import { useThemedStyles } from '../../../theme/useAppTheme';
import { useMapStore } from '../state/mapStore';
import {
  flyToZoomForPlaceType,
  popularPlaces,
  searchPlaces,
  type PlaceSearchResult,
} from '../services/placeSearchService';

type Props = {
  open: boolean;
  onClose: () => void;
};

export function MapPlaceSearchPanel({ open, onClose }: Props) {
  const inputRef = useRef<TextInput>(null);
  const requestFocusPlace = useMapStore((s) => s.requestFocusPlace);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<PlaceSearchResult[]>([]);
  const [recent, setRecent] = useState<PlaceSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const styles = useStyles();

  const trimmed = query.trim();
  const visibleResults = useMemo(
    () => (trimmed.length >= 2 ? results : recent),
    [recent, results, trimmed.length],
  );

  useEffect(() => {
    if (!open) return;
    const t = setTimeout(() => inputRef.current?.focus(), 80);
    void popularPlaces().then(setRecent).catch(() => undefined);
    return () => clearTimeout(t);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    if (trimmed.length < 2) {
      setResults([]);
      setError(null);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);
    const t = setTimeout(() => {
      void searchPlaces(trimmed)
        .then((items) => {
          if (!cancelled) setResults(items);
        })
        .catch((err: Error) => {
          if (!cancelled) {
            setResults([]);
            setError(err.message || 'Пошук недоступний');
          }
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }, 240);

    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [open, trimmed]);

  function goToPlace(place: PlaceSearchResult) {
    setRecent((prev) => [place, ...prev.filter((item) => item.id !== place.id)].slice(0, 8));
    setQuery(place.name);
    requestFocusPlace({
      lat: place.lat,
      lng: place.lng,
      zoom: flyToZoomForPlaceType(place.placeType),
      duration: 1400,
      label: place.name,
    });
    onClose();
  }

  if (!open) return null;

  return (
    <View style={styles.panel}>
      <View style={styles.inputShell}>
        <Ionicons name="search-outline" size={18} color={styles.muted.color} />
        <TextInput
          ref={inputRef}
          value={query}
          onChangeText={setQuery}
          placeholder="Місто або населений пункт"
          placeholderTextColor={styles.muted.color}
          returnKeyType="search"
          autoCorrect={false}
          style={styles.input}
        />
        {loading ? <ActivityIndicator size="small" color={styles.muted.color} /> : null}
        {query.length > 0 ? (
          <Pressable accessibilityLabel="Очистити пошук" onPress={() => setQuery('')} style={styles.iconButton}>
            <Ionicons name="close-circle" size={18} color={styles.muted.color} />
          </Pressable>
        ) : null}
        <Pressable accessibilityLabel="Закрити пошук" onPress={onClose} style={styles.closeButton}>
          <Text style={styles.closeText}>Готово</Text>
        </Pressable>
      </View>

      {error ? <Text style={styles.message}>{error}</Text> : null}

      <FlatList
        keyboardShouldPersistTaps="handled"
        data={visibleResults}
        keyExtractor={(item) => item.id}
        style={styles.list}
        contentContainerStyle={visibleResults.length ? styles.listContent : styles.emptyContent}
        ListEmptyComponent={
          loading ? null : (
            <Text style={styles.message}>
              {trimmed.length >= 2 ? 'Нічого не знайдено' : 'Почніть вводити назву міста або села'}
            </Text>
          )
        }
        renderItem={({ item }) => (
          <Pressable onPress={() => goToPlace(item)} style={({ pressed }) => [styles.resultRow, pressed && styles.pressed]}>
            <View style={styles.resultIcon}>
              <Ionicons name="location-outline" size={17} color={styles.iconColor.color} />
            </View>
            <View style={styles.resultText}>
              <Text style={styles.resultTitle} numberOfLines={1}>
                {item.name}
              </Text>
              <Text style={styles.resultSub} numberOfLines={1}>
                {item.subtitle}
              </Text>
            </View>
            <Ionicons name="navigate-outline" size={18} color={styles.muted.color} />
          </Pressable>
        )}
      />
    </View>
  );
}

function useStyles() {
  return useThemedStyles((t) => {
    const isDark = t.scheme === 'dark';
    return StyleSheet.create({
      panel: {
        width: '100%',
        gap: 10,
        paddingTop: 10,
      },
      inputShell: {
        minHeight: 46,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 9,
        borderRadius: 16,
        paddingLeft: 12,
        paddingRight: 6,
        backgroundColor: t.colors.input,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.colors.border,
      },
      input: {
        flex: 1,
        minWidth: 0,
        height: 44,
        color: t.colors.textPrimary,
        fontFamily: fonts.medium,
        fontSize: 15,
        paddingVertical: 0,
      },
      iconButton: {
        width: 30,
        height: 30,
        alignItems: 'center',
        justifyContent: 'center',
      },
      closeButton: {
        minHeight: 34,
        justifyContent: 'center',
        paddingHorizontal: 10,
        borderRadius: 12,
        backgroundColor: t.colors.surfaceHighlight,
      },
      closeText: {
        fontFamily: fonts.semiBold,
        fontSize: 13,
        color: t.colors.textPrimary,
      },
      list: {
        maxHeight: 292,
      },
      listContent: {
        borderRadius: 18,
        overflow: 'hidden',
        backgroundColor: t.colors.card,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.colors.border,
      },
      emptyContent: {
        minHeight: 48,
        justifyContent: 'center',
      },
      resultRow: {
        minHeight: 58,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
        paddingHorizontal: 12,
        paddingVertical: 9,
        borderBottomWidth: StyleSheet.hairlineWidth,
        borderBottomColor: t.colors.divider,
      },
      pressed: {
        opacity: 0.78,
      },
      resultIcon: {
        width: 34,
        height: 34,
        borderRadius: 17,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.05)',
      },
      resultText: {
        flex: 1,
        minWidth: 0,
      },
      resultTitle: {
        fontFamily: fonts.semiBold,
        fontSize: 15,
        lineHeight: 20,
        color: t.colors.textPrimary,
      },
      resultSub: {
        marginTop: 1,
        fontFamily: fonts.regular,
        fontSize: 12,
        lineHeight: 16,
        color: t.colors.textMuted,
      },
      message: {
        paddingHorizontal: 4,
        paddingVertical: 10,
        fontFamily: fonts.medium,
        fontSize: 13,
        color: t.colors.textMuted,
      },
      muted: { color: t.colors.textMuted },
      iconColor: { color: t.colors.textSecondary },
    });
  });
}

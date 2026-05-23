import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { DISTRICTS_BY_OBLAST, UKRAINE_OBLASTS } from '../../../data/ukraineRegions';
import { PrefsKeys } from '../../../config/prefsKeys';
import { persistentStorage } from '../../../services/persistentStorage';
import { notificationService } from '../../../services/notificationService';

const SAVE_DEBOUNCE_MS = 800;

/** Flutter `AlertsPage` / `messages_page.dart` state + autosave */
export function useRegionSelection() {
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [expandedOblast, setExpandedOblast] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const savingRef = useRef(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    void persistentStorage.hydrateFromAsyncStorage().then(() => {
      const list = persistentStorage.getStringList(PrefsKeys.selectedRegions);
      setSelected(new Set(list));
      setLoading(false);
    });
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  const scheduleSave = useCallback(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      void (async () => {
        if (savingRef.current) return;
        savingRef.current = true;
        try {
          const list = [...selected];
          persistentStorage.setStringList(PrefsKeys.selectedRegions, list);
          await notificationService.updateRegions(list);
        } finally {
          savingRef.current = false;
        }
      })();
    }, SAVE_DEBOUNCE_MS);
  }, [selected]);

  const toggleOblast = useCallback(
    (oblast: string) => {
      setSelected((prev) => {
        const next = new Set(prev);
        if (next.has(oblast)) {
          next.delete(oblast);
          for (const d of DISTRICTS_BY_OBLAST[oblast] ?? []) next.delete(d);
        } else {
          next.add(oblast);
        }
        return next;
      });
      scheduleSave();
    },
    [scheduleSave],
  );

  const toggleDistrict = useCallback(
    (district: string, oblast: string) => {
      setSelected((prev) => {
        const next = new Set(prev);
        if (next.has(district)) {
          next.delete(district);
          const districts = DISTRICTS_BY_OBLAST[oblast] ?? [];
          if (!districts.some((d) => next.has(d))) next.delete(oblast);
        } else {
          next.add(district);
        }
        return next;
      });
      scheduleSave();
    },
    [scheduleSave],
  );

  const selectAll = useCallback(() => {
    const next = new Set<string>();
    for (const o of UKRAINE_OBLASTS) {
      next.add(o.name);
      for (const d of DISTRICTS_BY_OBLAST[o.name] ?? []) next.add(d);
    }
    setSelected(next);
    scheduleSave();
  }, [scheduleSave]);

  const clearAll = useCallback(() => {
    setSelected(new Set());
    scheduleSave();
  }, [scheduleSave]);

  const filteredOblasts = useMemo(() => {
    if (!searchQuery.trim()) return UKRAINE_OBLASTS;
    const q = searchQuery.toLowerCase();
    return UKRAINE_OBLASTS.filter((o) => {
      if (o.name.toLowerCase().includes(q)) return true;
      return (DISTRICTS_BY_OBLAST[o.name] ?? []).some((d) => d.toLowerCase().includes(q));
    });
  }, [searchQuery]);

  const selectedOblastCount = useMemo(
    () => UKRAINE_OBLASTS.filter((o) => selected.has(o.name)).length,
    [selected],
  );

  return {
    loading,
    selected,
    expandedOblast,
    setExpandedOblast,
    searchQuery,
    setSearchQuery,
    filteredOblasts,
    selectedOblastCount,
    toggleOblast,
    toggleDistrict,
    selectAll,
    clearAll,
    reload: async () => {
      const list = persistentStorage.getStringList(PrefsKeys.selectedRegions);
      setSelected(new Set(list));
    },
  };
}

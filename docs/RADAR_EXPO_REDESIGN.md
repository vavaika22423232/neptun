# Radar tab — Expo (React Native) redesign

## Entry

- Tab: `app/(tabs)/radar.tsx` → `src/screens/radar/RadarScreen.tsx`
- Data: `useRadarFeedState` (React Query + cache + SSE alarm count)
- UI state: `src/features/radar/store/radarStore.ts` (Zustand + MMKV prefs)

## Architecture

| Layer | Files |
|-------|--------|
| Screen | `RadarScreen.tsx` — FlatList feed, pull-to-refresh |
| Types | `types/radar.types.ts` |
| Theme | `constants/radarTheme.ts` |
| Build | `utils/buildThreatEvents.ts`, `utils/buildRadarSections.ts` |
| Components | `RadarHeader`, `TelegramChannelCard`, `RadarFilterChips`, `RadarSearchBar`, `ThreatEventCard`, `ThreatDetailsSheet`, `RadarEmptyState`, `RadarNewUpdatesPill`, `RadarConnectionBadge` |

## Behaviour

- Opens with cached React Query `placeholderData`
- Filters/search/follow/mute persisted via `persistentStorage`
- Telegram promo dismiss → compact row (`PrefsKeys.telegramRadarBannerDismissed`)
- Card tap → `ThreatDetailsSheet` (map tab, follow, mute, share)
- New markers → floating pill + scroll to top

## Not a map

Map remains `app/(tabs)/index`. Radar only links to map tab on demand.

# Radar tab — premium live monitoring redesign

## 1. Screen layout (not a map)

```
┌ App chrome (Dron Alerts, online, Telegram, PRO, theme) ─┐
├ RadarLiveStatusBar (pulse, live/SSE, counts, last fetch) ┤
├ TelegramChannelCard (glass CTA → compact after dismiss) ┤
├ Search (collapsed chip → expanded field)                 ┤
├ RadarFilterChips (horizontal, one-hand)                 ┤
├ Sections: Активні зараз / Нові / Висока увага / …      ┤
│  └ ThreatEventCard × N (grouped by threat type)        ┤
└ Floating: RadarNewUpdatesPill                          ┘
```

Tap card → existing `ThreatDetailSheet` (timeline, coords, trajectory).  
«Карта» from empty state → `AppShellState.switchToMap()` (Map tab, not embedded map).

## 2. Flutter widget tree

| Widget | Role |
|--------|------|
| `RadarTab` | `CustomScrollView` + `RefreshIndicator`, keeps tab alive |
| `RadarLiveStatusBar` | Connection phase, event/alarm counts, stale hint |
| `TelegramChannelCard` | Dismissible promo / compact link |
| `RadarFilterChips` | `RadarQuickFilter` chips |
| `ThreatEventCard` | Grouped threat row, opens detail sheet |
| `RadarEmptyState` | Calm zero-threat state + Telegram + Map CTA |
| `RadarNewUpdatesPill` | Scroll-to-top on new data |
| `ThreatDetailSheet` | Existing bottom sheet (extend actions later) |

State:

| Provider | Role |
|----------|------|
| `radarFeedProvider` | REST snapshot, cache, stale banner, widget sync |
| `radarUiProvider` | Filter, search, Telegram dismiss, new-update count |
| `radarMapHistoryMinutesProvider` | PRO history window |

Domain:

| Model | Role |
|-------|------|
| `ThreatEvent` | Grouped card model (type cluster) |
| `ThreatSeverity` | low / medium / high / critical |
| `RadarFeedSectionKind` | Section headers for feed |
| `RadarQuickFilter` | Chip filters incl. my regions / high priority |

## 3. Data flow

1. `RadarTab` mounts → `radarFeedProvider.refresh()` (disk cache first via repository).
2. SSE updates alarm oblast count via `applyAlarmStreamSnapshot`.
3. Markers → `buildThreatEvents()` → `buildSectionedRadarFeed()`.
4. New markers bump `radarUiProvider.newUpdatesCount` → pill.
5. Filter/search persisted in `radarUiProvider` (filter in-memory; Telegram dismiss in prefs).

## 4. Design tokens (`radar_tokens.dart`)

- Background `#070B12`, card `#121A29`, accent `#7DD3FC`, live `#34D399`
- Screen pad 20, card radius 24, chip pill 999, section gap 22

## 5. Animation plan

| Element | Animation |
|---------|-----------|
| Live dot | Scale pulse when SSE live |
| New pill | Fade/slide (future: `AnimatedSwitcher`) |
| Cards | `RepaintBoundary` + InkWell scale (Material) |
| List insert | Optional `SliverAnimatedList` phase 2 |
| Telegram dismiss | `AnimatedSize` phase 2 |
| Shimmer | Loading skeleton only |

## 6. Interaction plan

- Pull-to-refresh → `refresh()`
- Tap card → threat detail sheet
- Tap «Карта» (empty) → Map tab
- Dismiss Telegram → compact row, saved pref
- Search toggle → expand field, filter feed live
- Filter chip → instant regroup
- New updates pill → scroll top + clear counter

## 7. Implementation phases

**Done (this pass)**

- `radar_tab.dart` rewrite
- Domain: `threat_event.dart`, `radar_feed_section.dart`, extended `radar_quick_filter.dart`
- UI: tokens, cards, chips, status bar, empty state, pill, `radar_ui_provider.dart`

**Next**

- `ThreatDetailsSheet`: follow/mute/share/map deep link
- `RadarSearchSheet` with recent/saved regions
- `RadarTimelineView` alternate mode toggle
- PRO row: AI summary, extended history gate
- `SliverAnimatedList` for insert animations
- Persist filter in prefs

## 8. File-by-file refactor map

| File | Action |
|------|--------|
| `lib/pages/tabs/radar_tab.dart` | **Rewritten** — dashboard scroll |
| `lib/features/radar/presentation/radar_tokens.dart` | **New** |
| `lib/features/radar/domain/threat_event.dart` | **New** |
| `lib/features/radar/domain/radar_feed_section.dart` | **New** |
| `lib/features/radar/domain/radar_quick_filter.dart` | **Extended** |
| `lib/features/radar/presentation/providers/radar_ui_provider.dart` | **New** |
| `lib/features/radar/presentation/widgets/*` | **New** cards/chips/status |
| `lib/pages/tabs/widgets/radar_tab_feed.dart` | Legacy; can deprecate |
| `lib/features/radar/presentation/widgets/radar_overview_strip.dart` | Optional merge into status bar |
| `lib/features/map/presentation/threat_detail_sheet.dart` | Add map/follow actions |
| `test/radar_quick_filter_test.dart` | Extend for new filters |

Expo mirror (`neptun_expo_app`): align `RadarScreen.tsx` with same sectioning using existing `buildRadarFeed.ts` / `groupThreatMarkers.ts`.

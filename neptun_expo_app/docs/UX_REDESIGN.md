# NEPTUN Expo — product structure & UX redesign

## 1. Structure audit (before)

| Problem | Impact |
|--------|--------|
| Three parallel header systems (map overlay, `RadarHeaderDashboard`, `SimpleScreenHeader`) | Inconsistent hierarchy, duplicated actions |
| Map “Шари” opened PRO radar dashboard, not map layers | Wrong mental model on map tab |
| Telegram CTA in radar header **and** bottom strip on Chat/Profile | Visual noise, not map-first |
| Theme toggle on Map/Radar/Chat headers | Settings scattered; Profile should own appearance |
| Radar feed = single section | Feed feels flat vs “live monitoring” product role |
| Legacy unused chrome (`MainTabChrome`, `RadarTopPanel`, …) | Confusion for contributors |
| Dual token entry (`theme/tokens`, `design/tokens`, `colors.ts`) | Inconsistent styling |

## 2. Information architecture (target)

| Tab | Purpose | Belongs here | Moved out |
|-----|---------|--------------|-----------|
| **Карта** | Where is it happening? | Status pill, map-only controls, marker sheet, alert summary | Telegram banner, theme, large PRO, tool menus |
| **Радар** | What is happening now? | Live summary, filters, sectioned feed, Telegram CTA, event sheet | Map, theme, account settings |
| **Чат** | Community discussion | Messages, composer, moderation gates | PRO sell, Telegram strip (optional) |
| **Профіль** | My settings & control | PRO card, theme, notifications, regions, support, legal | Map/radar CTAs |

## 3. Implementation plan (executed)

1. **Design system** — `src/design/system/` canonical tokens + `AppText`, `AppSection`, `AppListItem`, `TabScreenHeader`
2. **Map** — map-only control cluster (regions, notifications, radar feed, more menu); compact status unchanged
3. **Radar** — `RadarLiveHeader`, `RadarStatusSummary`, multi-section feed, in-feed `RadarTelegramCard`
4. **Chat / Profile** — slim headers; theme only in Profile appearance section
5. **Global chrome** — Telegram strip only on Radar tab; cleaner tab bar
6. **PRO** — unchanged logic; contextual locks + profile card (prior work)

## 4. Screen-by-screen summary

### Map
- Full-screen map, `MapTopOverlay` (status + controls + optional alert pill + compact PRO)
- Controls: регіони, сповіщення, радар, ще (history/safety/shelters)

### Radar
- Compact `RadarLiveHeader` (title, live, search, moderator)
- `RadarStatusSummary` card
- Toolbar: search, filters, PRO chips
- Feed sections: Висока увага → Активні → Нові оновлення → Спостереження
- `RadarTelegramCard` at feed bottom

### Chat
- `TabScreenHeader`: Чат + search/settings only

### Profile
- `TabScreenHeader` + scroll sections via `AppSection`
- `ProfileAppearanceSection` (системна / світла / темна)
- PRO card, account, notifications, tools, support, legal

## 5. Files changed (main)

- `src/design/system/*`
- `src/components/ui/AppText.tsx`, `AppSection.tsx`, `AppListItem.tsx`, `TabScreenHeader.tsx`
- `src/features/map/components/MapControlsCluster.tsx`
- `src/features/radar/components/RadarLiveHeader.tsx`, `RadarStatusSummary.tsx`, `RadarTelegramCard.tsx`
- `src/features/radar/utils/buildRadarSections.ts`
- `src/features/radar/components/RadarTabChrome.tsx`, `RadarScreen.tsx`, `RadarFeedToolbar.tsx`
- `src/features/profile/components/ProfileAppearanceSection.tsx`
- `src/screens/ProfileScreen.tsx`
- `src/components/ChatTabChrome.tsx`, `ProfileTabChrome.tsx`, `NeptunTabBar.tsx`
- `app/(tabs)/_layout.tsx`

## 6. Phase 2 (profile / chat / radar polish)

- **Profile** — Diia-style `AppSection` + `ProfileSettingsGroup` + `AppListItem`; sections: регіони → тема → звук → інструменти → підтримка → legal
- **Chat** — `ChatCommunityNotice`, wider list/composer padding (20px), calmer composer radius
- **Radar** — `RadarHistoryLink`, event cards show source + time; detail sheet: map / follow / notify / mute
- **Map controls** — location / notifications / **layers** / more (radar moved to «Ще»)
- **Design system** — `AppIconButton` alias, `AppBadge` exported from `components/ui/index.ts`

## 7. Manual QA checklist

- [ ] Map: no large header/banner; controls work; marker sheet opens
- [ ] Radar: sections populate with live data; Telegram card opens channel
- [ ] Chat: keyboard safe area; gates still work
- [ ] Profile: theme changes apply; PRO purchase/restore works
- [ ] Light/dark/system theme
- [ ] PRO users: no ads, no lock chips
- [ ] Navigation: regions, history, premium, stack screens
- [ ] No placeholder buttons

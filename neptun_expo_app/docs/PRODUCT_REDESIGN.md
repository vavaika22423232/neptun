# NEPTUN Expo — product redesign (deliverable)

Structured premium Ukrainian live-monitoring app. **Expo / TypeScript only**; purchase, API, chat, and map logic preserved.

---

## 1. Product structure audit

| Issue (before) | Resolution |
|----------------|------------|
| Map carried Telegram, theme, PRO, wrong “layers” CTA | Map-first overlay only: status, 4 controls, compact PRO, alert pill |
| Radar flat / decorative | Sectioned live feed + summary + filters + Telegram card |
| Profile mixed with map CTAs | Control center: PRO, regions, theme, sound, tools, support, legal |
| 3 header systems | `TabScreenHeader` on Radar/Chat/Profile; Map has no stack header |
| Neon cyan + loud PRO gold | Graphite palette, `#4A8DFF` / `#2563EB`, muted `pro` gold |
| Glass everywhere | Solid `card` surfaces; glass only on map floats + tab bar |

---

## 2. Information architecture

| Tab | Purpose | Primary UI |
|-----|---------|------------|
| **Карта** | Where? | Full-screen map, status pill, controls, marker sheet |
| **Радар** | What now? | Summary, filters, sections, event cards, details sheet, Telegram |
| **Чат** | Community | Messages, composer, moderation notice, gates |
| **Профіль** | Control | PRO card, theme, notifications, regions, support, legal |

**Moved off Map:** Telegram banner, theme toggle, giant PRO, tool sprawl.  
**Telegram:** Radar feed card + Profile support + optional bottom strip (Radar tab only).  
**PRO:** Profile card (main) + contextual locks + compact map pill + ads CTA.

---

## 3. Visual identity / palette

- **Base:** graphite / soft gray (not pure black/white)
- **Accent:** one blue (`primary`)
- **PRO:** muted gold (`pro` / `proSoft`) only
- **Danger:** controlled red (`danger` / `dangerSoft`)
- **Live/success:** green only (`success` / `live`)

See `docs/COLOR_SYSTEM.md` and `src/theme/darkTheme.ts` / `lightTheme.ts`.

---

## 4. Theme system

- Modes: `light` | `dark` | `system` via `ThemeProvider`
- Persists: `themeStorage.ts` + `PrefsKeys.themeMode`
- Semantic tokens: `pro`, `telegram`, `successSoft`, `warningSoft`, etc.
- Status bar + navigation follow resolved scheme
- Profile: `ProfileThemeSelector` with Ukrainian copy per spec

---

## 5. Shared components

| Component | Path |
|-----------|------|
| AppScreen, AppCard, AppButton, AppIconButton, AppBadge | `src/components/ui/` |
| AppText, AppSection, AppListItem | `src/components/ui/` |
| AppEmptyState, AppLoadingState, AppErrorState | `src/components/ui/` |
| TabScreenHeader | `src/components/ui/TabScreenHeader.tsx` |
| ProfileSettingRow, ProfileProCard, ProfileThemeSelector | `src/features/profile/components/` |
| ProEntryPill, ProCard, ProPaywall, ProFeatureLock | `src/features/pro/` |

---

## 6. Map

- `MapTopOverlay`, `MapStatusPill` (~56px), `MapControlsCluster` (location, notifications, layers, more)
- `MapAlertSummaryPill` when needed
- `MapThreatMarkerSheet` / alias `MapEventBottomSheet`
- `ProEntryPill` — non-PRO only, muted gold
- No tab header, no Telegram banner on map

---

## 7. Radar

- `RadarLiveHeader`, `RadarStatusSummary`
- `RadarFeedToolbar` + `RadarProUpsellRow`
- Sections: high attention → new → active → watch (`buildRadarSections.ts`)
- `ThreatEventCard` / alias `RadarEventCard`
- `ThreatDetailsSheet` (map, follow, notify, share)
- `RadarTelegramCard`, `RadarHistoryLink`, `RadarEmptyState`

---

## 8. Chat

- `TabScreenHeader` + search/settings
- `ChatCommunityNotice` (rules reminder)
- Wider padding, solid composer card
- Flat bubbles from theme (no cyan gradients)
- Existing gates, SSE, composer logic unchanged

---

## 9. Profile

- Hero + `ProCard` (NEPTUN PRO benefits)
- `ProfileThemeSelector` (system / light / dark + descriptions)
- Regions & notifications (`ProfileAccountCard`, smart notifications row)
- Sound settings (`SettingsSection`)
- Tools / support / legal via `ProfileSettingsGroup` + `AppListItem`

---

## 10. PRO / paywall / ads

- `useProAccess` → `/premium` with analytics params
- `ProPaywallContext` + existing `PremiumTierPaywall` (real IAP)
- Ads: `AdBannerSlot` hidden for PRO; `AdRemoveProCta` above tab bar
- No fake features; locks use `LOCKED_FEATURES` + real `PlanId`

---

## 11. Functionality preserved

- Expo Router tabs and stack screens
- Map WebView / native map, marker sheet, ballistic overlays
- Radar feed, filters, search, follow/mute, details sheet
- Chat auth gates, messages, voice, moderation flows
- Profile settings, regions, premium purchase/restore
- Entitlements, ads, notifications, Telegram deep links
- Theme persistence

---

## 12. Remaining risks / manual QA

- [ ] Purchase/restore on device (StoreKit / Play)
- [ ] Map embed vs native engine overlays
- [ ] Radar with live API data (sections populate)
- [ ] Chat keyboard + long threads performance
- [ ] Light/dark/system theme after cold start
- [ ] PRO user: no ads, no lock chips
- [ ] Legacy unused files (`RadarTopPanel`, `MainTabChrome`) — safe to delete after QA

---

## 13. Key file index

```
docs/COLOR_SYSTEM.md
docs/UX_REDESIGN.md
src/theme/{darkTheme,lightTheme,theme,tokens,ThemeProvider,themeStorage}.ts
src/components/{NeptunTabBar,ChatTabChrome,ProfileTabChrome}.tsx
src/features/map/components/Map*.tsx
src/features/radar/components/Radar*.tsx
src/features/pro/
src/screens/{MapScreen,radar/RadarScreen,ChatConversationScreen,ProfileScreen,PremiumScreen}.tsx
app/(tabs)/_layout.tsx
```

**Target:** One calm, trustworthy product — Map = location, Radar = live feed, Chat = community, Profile = control.

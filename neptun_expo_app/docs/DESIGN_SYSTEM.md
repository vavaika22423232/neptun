# Neptun Design System (Expo)

Premium dark UI — Apple / Linear / Revolut inspired. **No tactical or military visual language.**

## Tokens (`src/design/tokens.ts`)

| Category | Keys |
|----------|------|
| `palette` | bg, surfaces, text, accent, premium, semantic map colors |
| `radii` | xs → sheet (28), pill |
| `spacing` | 2px grid, `screenH` / `screenV` |
| `typography` | display → micro |
| `shadows` | sm, md, sheet, glowAccent |
| `motion` | 120 / 220 / 360 ms |
| `profile` | profile-tab aliases |

Legacy: `src/theme/colors.ts` re-exports tokens.

## Primitives

| Component | Role |
|-----------|------|
| `NeptunSurface` | Glass cards |
| `NeptunPressable` | Scale + haptic |
| `NeptunEmptyState` | Empty / error |
| `NeptunLoading` | Spinner |
| `NeptunScreen` | Screen canvas |
| `NeptunBootSplash` | Font / gate boot |

## Rollout status

| Area | Status |
|------|--------|
| Tokens + primitives | ✅ |
| Boot splash | ✅ |
| Tab bar, shell chrome, cards, sheets, buttons, text | ✅ |
| Onboarding (4 pages) | ✅ |
| Profile tab | ✅ |
| Radar feed + shimmer + empty/error | ✅ |
| Premium paywall tokens | ✅ |
| Chat composer, menus, dividers | ✅ (partial — bubbles use chat themes) |
| Map status strip + layer chips + threat sheet | ✅ |
| Modals (offline, battery, changelog gradient) | ✅ |
| Stack transitions | ✅ `fade_from_bottom` |
| Map native markers / trajectories | 🔲 engine layer |
| Chat bubbles (per-theme) | 🔲 intentional |
| Regions, alarm history, sleep mode, app update gate | ✅ |
| Map ballistic banners, region sheet, web error | ✅ |
| PRO gate empty state | ✅ |
| Heatmap, analytics, shelters, safety, chat settings | 🔲 partial (colors via theme) |
| iOS widgets | 🔲 native |

## Usage

```ts
import { palette, spacing, NeptunSurface, NeptunEmptyState } from '../design';
```

## Map guidelines

- Status: glass pill, calm green = live
- Sheets: `NeptunBottomSheet` + soft meta chips
- Markers: rounded, thin ring, no HUD corners
- Trajectories: 2px, ~40% opacity

## Motion

- Press: `NeptunPressable`
- Boot logo: subtle pulse
- Lists: prefer `FadeIn` 220–280ms (radar stale banner pattern)

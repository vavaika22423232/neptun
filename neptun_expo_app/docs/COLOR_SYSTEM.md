# NEPTUN color system

Mature, calm palette for a Ukrainian digital service — not cyberpunk / neon SaaS.

## Semantic tokens (`theme.colors`)

| Token | Role |
|-------|------|
| `background` / `backgroundSecondary` | App canvas |
| `surface` / `card` | Solid panels (prefer over glass) |
| `primary` | Single accent — links, active tab, CTAs |
| `primarySoft` / `primaryMuted` | Tinted backgrounds only |
| `pro` / `proSoft` | PRO badges and paywall only |
| `telegram` | Telegram CTAs (= `primary`) |
| `success` / `live` | Online, positive |
| `warning` | Caution, drone-class threats |
| `danger` / `dangerSoft` | Alerts and high threats |
| `premium*` | Aliases of `pro*` for legacy code |

## Rules

1. One blue accent — no cyan (`#38BDF8` removed).
2. PRO uses muted gold — not `#FACC15` neon.
3. Red only for danger; green only for live/success.
4. Cards use opaque `colors.card`, not heavy glass.
5. Shadows are soft gray — no `glowAccent` halos.

## Sources of truth

- `src/theme/darkTheme.ts`
- `src/theme/lightTheme.ts`
- Derived: `src/theme/theme.ts` (chat, radar, profile, shadows)

Map overlays: `mapGlassTokens()` reads active theme.

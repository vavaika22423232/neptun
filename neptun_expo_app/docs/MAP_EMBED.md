# Map embed (WebView) — Flutter parity

Production map tab uses **`https://neptun.in.ua/?embed=1&theme=dark`** inside `react-native-webview`, same as Flutter `map_tab.dart`.

## Architecture

| Layer | File |
|-------|------|
| Tab screen | `src/screens/MapScreen.tsx` |
| WebView | `src/features/map/components/EmbedMapWebView.tsx` |
| Bridge / resize | `src/features/map/utils/mapWebViewInject.ts` |
| Recovery on focus | `src/features/map/hooks/useMapWebViewRecovery.ts` |
| Native engine (optional) | `EXPO_PUBLIC_MAP_ENGINE=native` → `TacticalMap.tsx` |

## Moderator

- Flutter may load `/api/admin/auth/embed` with `X-Auth-Secret`.
- **RN uses public embed URL** + inject `window.__ADMIN_SECRET` after `onLoadEnd` (bootstrap 401 was breaking WebView).

## Troubleshooting

1. **Safari works, app does not**
   - Clear moderator: 7× tap logo → logout.
   - `npx expo start --dev-client --clear`
   - Do not set `EXPO_PUBLIC_MAP_ENGINE=native` without Mapbox token + dev build.

2. **Blank dark area, no error**
   - Wait for `neptun_map_ready` (resize kicks run ~6s).
   - Switch tab away and back (triggers `useMapWebViewRecovery`).

3. **GeoJSON native layers**
   - `npm run sync:map-geo` copies `assets/geo/*.geojson` → `src/features/map/data/*.json`.

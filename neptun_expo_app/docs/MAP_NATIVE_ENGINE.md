# Native MapLibre engine (`EXPO_PUBLIC_MAP_ENGINE=native`)

Production default remains **WebView embed** (`embed`). Enable native tactical rendering for dev/benchmark:

```bash
EXPO_PUBLIC_MAP_ENGINE=native npx expo run:ios
```

Requires `EXPO_PUBLIC_MAPBOX_ACCESS_TOKEN` and dev client rebuild (`@rnmapbox/maps`).

## Phase 2 capabilities (this slice)

| Feature | Implementation |
|---------|----------------|
| SSE `track_update` | `mapStore.patchTrack` → `applyMarkerPatch` |
| Smooth interpolation | `markerMotionEngine` (rAF, cubic ease-out) |
| Distance-based duration | `applyTrackMotion` + `haversineKm` |
| Bearing arrow | `TacticalMap` SymbolLayer `▲` rotated by `course_bearing` |
| Clustering | Mapbox `ShapeSource` cluster (radius 44, max zoom 8) |
| Oblast alarm fills | `buildOblastAlarmGeoJson` |
| District alarm fills | `buildDistrictAlarmGeoJson` (alarm-only polygons) |
| District borders (z≥7.5) | `buildDistrictBorderGeoJson` + LineLayer |
| Alarm pulse | `useAlarmPulse` — oblast/district fill opacity 2s loop (Flutter `PulseAlarmLayer`) |
| Trajectories | `trajectoriesToFeatureCollection` (AI + track history) |
| Glow layers | Circle blur under threat dots |
| Viewport culling | `useMapViewportBounds` + `cullMarkersInViewport` (12% pad) |
| Performance cap | `cullMarkersForDisplay` — viewport then newest 2000 |

## Architecture

```
SSE track_update
  → mapStore.patchTrack
  → scheduleMarkerMotion
  → markerMotionEngine (60fps)
  → useMarkerMotionOverlay
  → mergeMotionIntoMarkers
  → markersToFeatureCollection
  → MapLibre ShapeSource layers
```

Embed map (`EmbedMapWebView`) keeps motion/geometry in Next.js — no change.

## Performance notes

- Shape sources only — no per-marker React views
- Motion updates bypass React Query; only `TacticalMap` re-memoizes GeoJSON when overlay Map changes
- Culling prevents bridge overload when API returns 2000+ markers

## Geo sync

After editing `assets/geo/*.geojson`:

```bash
npm run sync:map-geo
```

## Not yet (native)

- Skia threat icons / prediction radius glow
- Parity with embed moderator tools

## Tests

```bash
npx tsx src/features/map/engine/markerMotionEngine.test.ts
```

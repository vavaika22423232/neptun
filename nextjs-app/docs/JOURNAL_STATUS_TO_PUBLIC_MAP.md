# Admin feed status → public map

The admin **Лента** (`/api/admin/feed`) records pipeline events from the Telegram worker. Only a subset of rows correspond to markers that can appear on the public map after [`buildMarkers`](../../src/lib/build-markers.ts) filtering.

**Feed vs public map**

- The feed is a **full pipeline journal**: every processed/skipped event is logged for operators. It is **not** filtered by `corroboration_pending` or the dual-channel map gate.
- The **public map** (and SSE to clients) applies [`buildMarkers`](../../src/lib/build-markers.ts), TTL, confidence, placement suppressions, and **corroboration**: when `dualSourceMapGate` is on, markers stay hidden until two distinct `channel_name` values appear in observations (except `channel_priority <= 1`). **Synthetic phantom avia** markers (`resolve_status` containing `phantom_avia`) use the **same** two-source requirement **even when** `dualSourceMapGate` is off.

**Phantom avia feed rows**

- When the worker detects KAB and spawns a tactical airfield pin, the admin feed row uses **`place`** for the airfield label (coords match that airfield) and optional **`impact_place`** for the KAB geocode/target text from the parent message. This avoids mixing one label with the other’s coordinates.

| Feed `status` | Meaning | Public map |
|---------------|---------|------------|
| `processed` | Worker accepted at least one entity and (for threats) ingested a marker | Yes, if the marker passes TTL, bounds, `minConfidence`, and is not `suppressed_*` placement. |
| `dropped` | No usable entities (e.g. both parsers empty, unknown after merge) | No |
| `skipped` | Intentionally not mapped (pre-filter, negation-only, `alert` shown as regional SVG, spam/summary) | No — air-raid **alarms** use the SVG layer, not a point marker for raw `alert` rows. |
| `error` | Processing failure | No |

**Notes**

- Journal **parser** field (`gpt`, `regex`, `both_empty`) describes extraction, not map eligibility.
- **Ланцюг** (chain) updates should share one `track_id` / spatial merge so the map shows one pin with trail updates, not many pins in the same area.
- Server-side **Spatial Correlator** in [`markers-store.ts`](../../src/lib/markers-store.ts) may merge nearby same-group threats before ingest duplicates accumulate.

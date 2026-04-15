# Allclear (`відбій`) and markers on the map

## Product behavior (implemented)

1. **Immediate removal (region-scoped)** When the worker parses an `allclear` entity **with a resolved oblast**, it calls `POST /api/ingest/clear-region` with:
   - `region`: oblast name (same string the worker uses for markers in that area),
   - optional `threat_types`: narrowed to `cleared_threat_type` when present,
   - optional `place_contains`: e.g. Kherson channel microdistrict hints.

   [`deleteByRegion`](../../src/lib/markers-store.ts) removes matching rows from the store; SSE notifies clients. This is **not** TTL-only: matching markers disappear as soon as the worker sends the clear.

2. **No oblast on allclear**  
   If the message is classified as allclear but **no oblast** is inferred, the worker logs and **does not** call clear-region. Existing markers age out via normal **TTL** (`monitorPeriod` / `ttlEnabled` in admin settings) and pruning in the store.

3. **Allclear still ingested as an event**  
   The worker publishes a feed row with `threat_type=allclear` for visibility; it does not need to remain as a map pin for end users.

## Related code

- Worker: `_clear_region_markers` → `CLEAR_REGION_URL` (`worker/worker.py`)
- API: [`src/app/api/ingest/clear-region/route.ts`](../../src/app/api/ingest/clear-region/route.ts)
- Store: `deleteByRegion`

## Future tweaks (optional)

- Broaden oblast inference for short «відбій» posts so clear-region fires more often.
- Tie allclear to **track_id** for surgical clears (current model is oblast ± type ± place substring).

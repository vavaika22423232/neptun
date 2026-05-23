# Worker geocode pipeline (short reference)

- **Resolver:** [`worker/geo/resolver.py`](../worker/geo/resolver.py) — gazetteer → external geocoders → scoring → oblast bbox gate (`oblast_gate_hint`).
- **Homonyms:** [`disambiguate_homonym_place`](../worker/geo/place_normalize.py) applies **oblast-scoped** rewrites (e.g. Київська область + «Васильківка» → **Васильків** city) before candidate lookup.
- **«На X» / direction:** the `direction` field is geocoded as a separate candidate family (resolver §3b) so movement toward a settlement can surface coords distinct from `place_name` when the parser fills both.

Public map **display** of uncertainty (`display_class`, rings, corridor) is computed in Next.js — it does not change which coordinates the worker emits.

## UI place search (map header)

- **API:** `GET /api/places/search?q=…` reads `settlements.db` (same gazetteer as the worker) via `better-sqlite3`, with fallback rows from `public/ukraine_settlements.geojson`.
- **DB path:** `DATA_DIR/settlements.db` on VPS, else `worker/geo/data/settlements.db`.
- **FTS:** `places_fts` is rebuilt by `worker/geo/data/build_gazetteer.py` (`ensure_places_fts`). After changing the builder, run `REBUILD_GAZETTEER=1` deploy or `bash deploy/rebuild-gazetteer.sh` on the server.

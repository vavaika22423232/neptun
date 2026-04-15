# Worker geocode pipeline (short reference)

- **Resolver:** [`worker/geo/resolver.py`](../worker/geo/resolver.py) — gazetteer → external geocoders → scoring → oblast bbox gate (`oblast_gate_hint`).
- **Homonyms:** [`disambiguate_homonym_place`](../worker/geo/place_normalize.py) applies **oblast-scoped** rewrites (e.g. Київська область + «Васильківка» → **Васильків** city) before candidate lookup.
- **«На X» / direction:** the `direction` field is geocoded as a separate candidate family (resolver §3b) so movement toward a settlement can surface coords distinct from `place_name` when the parser fills both.

Public map **display** of uncertainty (`display_class`, rings, corridor) is computed in Next.js — it does not change which coordinates the worker emits.

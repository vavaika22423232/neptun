# Agent / contributor notes

## LLM text analysis (markers / trajectory hints)

- **Entry point:** `nextjs-app/worker/ai_message_analyzer.py` — `analyze_message` / `_call_ai` calls a pluggable backend to extract `target_city`, `origin`, speed, `flight_phase`, sea route, etc.
- **Prompt + JSON contract:** `nextjs-app/worker/domain_llm/schema.py` (`ANALYSIS_SCHEMA_VERSION`, `build_user_prompt`, field descriptions). Few-shot examples: `nextjs-app/worker/domain_llm/fewshots.json`.
- **Backends:** `nextjs-app/worker/domain_llm/backend.py` — `DOMAIN_LLM_BACKEND=openai` (default, uses `OPENAI_API_KEY` and `OPENAI_ANALYZER_MODEL`) or `http` for an OpenAI-compatible server (`DOMAIN_LLM_HTTP_URL`, `DOMAIN_LLM_HTTP_MODEL`, optional `DOMAIN_LLM_HTTP_KEY`).
- **Safety:** Do not trust model-emitted coordinates. Origins are resolved via `resolve_origin_coords`; speeds are clamped; map placement still goes through the normal geo pipeline and bounds checks in `worker.py`.

## Trajectory and map behavior

- **Trajectory build:** `nextjs-app/worker/worker.py` — `_build_trajectory` (direction, `target_city`, learned targets, AI fallback). This is separate from the LLM JSON: geometry and ticker logic stay server-side.
- **Public map:** Next.js Leaflet code under `nextjs-app/src/components/Map/`; marker motion in `nextjs-app/src/lib/markers-store.ts`.

## Next.js ingest → public map (single publication policy)

- **Overview:** `docs/NEPTUN_DATA_FLOW.md` (repo root).
- **Who may appear on `/api/data` vs SSE broadcast:** `nextjs-app/src/lib/marker-publication.ts` (`markerPassesPublicMapRawFilter`, `ingestShouldBroadcastMarker`). `build-markers.ts` uses the same filter; do not duplicate gating logic elsewhere.
- **Geo fixes on ingest:** `nextjs-app/src/lib/ukraine-oblast-validate.ts`, `nextjs-app/src/lib/declared-non-ua-origin-normalize.ts`. Counters surface on `GET /api/health` under `pipeline`.

## Dataset export (metrics / RAG / fine-tune)

- **Audit log:** `NEPTUN_GEO_AUDIT_LOG` → NDJSON via `nextjs-app/worker/geo/geo_audit_log.py` (appended from `worker.py` when processing messages).
- **Export script:** `nextjs-app/worker/scripts/export_domain_dataset.py` writes flat JSONL (text, channel, coords, `resolve_status`, etc.).
- **Fine-tuning notes:** `nextjs-app/worker/domain_llm/FINETUNE.md`.

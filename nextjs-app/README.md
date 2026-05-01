# Neptun Web/API

Next.js application for the public map, admin UI, JSON APIs, chat, and ingest endpoints. The
Python Telegram worker lives in `worker/` inside this app directory because it posts directly to
`/api/ingest`.

## Common Commands

```bash
cd nextjs-app
npm ci
npm run dev
npm run lint
npm run test:domain
```

Worker tests:

```bash
cd nextjs-app/worker
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Legacy parser and push smoke scripts are in `worker/manual_checks/` and are not part of CI.

## Pointers

- Root project overview: `../README.md`
- Map and ingest flow: `../docs/NEPTUN_DATA_FLOW.md`
- Deploy runbook: `../deploy/README.md`
- Worker LLM/parser notes: `../AGENTS.md`

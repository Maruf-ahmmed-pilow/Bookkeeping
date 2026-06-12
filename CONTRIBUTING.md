# Contributing

Thanks for your interest in improving the Bookkeeping AI Control Tower. This
document covers local setup, the quality gates CI enforces, and conventions.

## Project layout

```
.
├── backend/            FastAPI + SQLAlchemy service
│   ├── app/            application code (routers, services, models, AI agent)
│   └── tests/          pytest suite (runs offline on in-memory SQLite)
├── frontend/           React + Vite + TypeScript single-page app
├── docker-compose.yml  Postgres (default) + full-stack profile
└── Makefile            common dev tasks — run `make help`
```

## Local setup

Prerequisites: Python 3.11+, Node 20+, Docker (for Postgres).

```bash
make db                 # start Postgres on host port 5433
make backend-install    # pip install -r backend/requirements-dev.txt
make backend-seed       # load Chart of Accounts + sample transactions
make backend-run        # http://localhost:8000  (docs at /docs)

make frontend-install
make frontend-run       # http://localhost:5173
```

Set `ANTHROPIC_API_KEY` in `backend/.env` to use the real Claude classifier;
without it the app falls back to the deterministic rule-based engine.

## Quality gates

CI runs on every pull request. Reproduce it locally before pushing:

```bash
make lint               # ruff (backend) + eslint & typecheck (frontend)
make test               # pytest

cd frontend && npm run format:check   # prettier
```

- **Backend** — `ruff` for lint/format/import-order, `pytest` for tests. The
  test suite runs entirely offline (no Postgres, no API key).
- **Frontend** — `eslint` (flat config), `prettier`, and `tsc` strict mode.

Optionally install the git hooks: `pre-commit install`.

## Conventions

- Keep new code consistent with the surrounding style; the linters are the
  source of truth for formatting.
- Add or update tests for behavioural changes. Every AI decision and human
  action is expected to remain auditable (`ai_runs` / `audit_logs`).
- Money flows through balanced double-entry journal entries — preserve the
  invariant that debits equal credits and the balance sheet balances.
- Conventional commit messages (`feat:`, `fix:`, `docs:`, `chore:`…) are
  appreciated but not enforced.

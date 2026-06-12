# Bookkeeping AI Control Tower — Core MVP

![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Node](https://img.shields.io/badge/node-20%2B-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

> Replace `OWNER/REPO` in the CI badge above once the repository is pushed to GitHub.

A runnable vertical slice of the Enterprise AI-Assisted Bookkeeping Platform from the SRS.
It implements the most important end-to-end flow:

```
Bank transaction intake
   → AI transaction classification (Claude) with a confidence score
   → Human-in-the-Loop review/approval (low-confidence items are escalated)
   → Double-entry journal posting to the general ledger
   → Profit & Loss and Balance Sheet reports
```

Every AI decision is recorded (`ai_runs`) and every human action is audit-logged
(`audit_logs`), matching the SRS's traceability requirements (FR-HITL-1).

## Stack

| Layer    | Tech                                                        |
| -------- | ----------------------------------------------------------- |
| Frontend | React + Vite + TypeScript                                   |
| Backend  | FastAPI + SQLAlchemy                                        |
| Database | PostgreSQL (Docker)                                         |
| AI       | Claude API (`claude-opus-4-8`) via structured outputs       |

The AI Classification Agent calls Claude when `ANTHROPIC_API_KEY` is set, and
**falls back to a deterministic rule-based engine** when it isn't — so the app
runs fully offline for demos. The active engine is shown in the UI header.

## SRS coverage

| SRS reference                       | Where                                            |
| ----------------------------------- | ------------------------------------------------ |
| F2 / FR-TRAN-1 Classify transactions| `backend/app/ai/classifier.py`, `services.py`    |
| FR-HITL-1 Approval for critical actions | `backend/app/routers/approvals.py`           |
| Quality Control escalation (<95% conf) | `CONFIDENCE_THRESHOLD` gate in `services.py`  |
| F8 / FR-RPT-1,2 P&L + Balance Sheet | `backend/app/routers/reports.py`                 |
| Journal Entries (debits = credits)  | `services.post_journal_entries`                  |
| AI Runs / Audit Logs                | `backend/app/models.py`                          |
| Chart of Accounts                   | `backend/app/seed.py`                            |

## Project layout

```
.
├── backend/            FastAPI + SQLAlchemy service
│   ├── app/            routers, services, models, and the AI classification agent
│   └── tests/          pytest suite (runs offline on in-memory SQLite)
├── frontend/           React + Vite + TypeScript single-page app
├── docker-compose.yml  Postgres (default) + full-stack `full` profile
├── Makefile            common dev tasks — run `make help`
└── .github/workflows/  CI: lint, typecheck, test, build
```

## Quick start

The fastest path uses the `Makefile` (`make help` lists every target). The steps
below spell out the same commands.

### 1. Start Postgres

```bash
docker compose up -d        # or: make db
```

(Compose maps Postgres to host port **5433** to avoid clashing with a local Postgres.)

### 2. Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # optionally add your ANTHROPIC_API_KEY
python -m app.seed            # loads the Chart of Accounts + 12 sample transactions
python -m uvicorn app.main:app --reload # http://localhost:8000  (docs at /docs)
```

To use the real Claude classifier, put your key in `backend/.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

## Demo walk-through

1. Open the **Transaction Queue** — 12 seeded bank transactions sit in `new`.
2. Click **Classify all new**. Each transaction gets a suggested account + confidence.
   Clear ones (AWS, Gusto payroll, rent) land in `classified`; ambiguous ones
   (e.g. `AMZN MKTPLACE`) drop below the threshold and become `needs_review`.
3. For each item, accept the suggestion or override the account, then
   **Approve & post** — this writes the balanced journal entries.
4. Open **Financial Reports** — the P&L and Balance Sheet now reflect posted entries,
   and the Balance Sheet shows `✓ balanced`.
5. The **Dashboard** summarises revenue, expenses, net income, cash, and the
   pending-review count.

## API

Interactive docs at `http://localhost:8000/docs`. Key endpoints:

- `POST /api/transactions/{id}/classify` — run the classification agent
- `POST /api/transactions/classify-all` — batch-classify all `new` transactions
- `POST /api/transactions/{id}/approve` — HITL approve → post to ledger
- `POST /api/transactions/{id}/reject` — HITL reject
- `GET  /api/reports/profit-and-loss`, `/balance-sheet`, `/dashboard`

## Run the whole stack in Docker

To build and run Postgres, the API, and the web app together:

```bash
ANTHROPIC_API_KEY=sk-ant-...  docker compose --profile full up --build
```

The backend seeds itself on start; the app is served at `http://localhost:5173`
(nginx proxies `/api` to the backend). The `ANTHROPIC_API_KEY` is optional.

## Testing & quality

| Stack    | Lint / format        | Types        | Tests                    |
| -------- | -------------------- | ------------ | ------------------------ |
| Backend  | `ruff check .`       | —            | `pytest`                 |
| Frontend | `npm run lint` / `format:check` | `npm run typecheck` | build via `npm run build` |

```bash
make lint     # ruff + eslint + tsc
make test     # pytest (offline: no Postgres or API key needed)
```

The backend test suite spins up an in-memory SQLite database and exercises the
rule-based classifier plus the full intake → classify → approve → report flow,
asserting that journal entries stay balanced. CI (GitHub Actions) runs all of
the above on every pull request. Optionally enable git hooks with
`pre-commit install`.

## Notes / scope

This is the core slice, not the full SRS. Out of scope for this MVP: OCR document
intake, bank reconciliation matching, AP/AR workflows, payroll/tax modules,
multi-tenant auth/RBAC, and the chat assistant. The data model and AI-agent
seam (`app/ai/`) are structured so those can be layered on without rework.

See [CONTRIBUTING.md](CONTRIBUTING.md) for development workflow and
[CHANGELOG.md](CHANGELOG.md) for release notes.

## License

Released under the [MIT License](LICENSE).

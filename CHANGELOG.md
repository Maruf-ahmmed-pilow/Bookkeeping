# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Backend test suite (`pytest`) covering the rule-based classifier and the full
  intake → classify → approve → report API flow, running offline on SQLite.
- Tooling: `ruff` + `pytest` config (`backend/pyproject.toml`), ESLint flat
  config, Prettier, and per-stack `requirements-dev.txt`.
- Dockerfiles for the backend (uvicorn) and frontend (nginx), plus a `full`
  Docker Compose profile to run the whole stack.
- GitHub Actions CI (lint, typecheck, test, build), a `Makefile`, and a
  `pre-commit` configuration.
- Project hygiene: `LICENSE` (MIT), `CONTRIBUTING.md`, `.editorconfig`, this
  changelog, and a favicon.

### Changed
- Models now use portable column types (native `uuid`/`jsonb` on PostgreSQL,
  degrading to `varchar`/`json` elsewhere) so the suite can run on SQLite.
- Refreshed the UI shell: branded header, AI-engine status indicator, sticky
  navigation, and a footer.

## [0.1.0]

### Added
- Core MVP: bank transaction intake, AI classification (Claude with a
  rule-based fallback), human-in-the-loop approval, double-entry ledger
  posting, and P&L / Balance Sheet / dashboard reporting.

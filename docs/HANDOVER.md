# Handover

## Current phase

`PHASE 0 — FOUNDATION + REAL BITGET VERIFICATION`

## Completed

- Standalone Git repository initialized on `main`.
- Monorepo foundation, strict Python schemas/client, capability model, verification CLI, minimal API,
  minimal web shell, deterministic tests, and CI created.
- Read-only historical Reality export publishes validated, canonical JSONL atomically under the
  Git-ignored `artifacts/` runtime directory.
- Official Agent Hub CLI and Codex skill installed; no credentials configured.

## Verified

- Official UTA v3 and Reality documentation reviewed on 2026-09-12.
- Public Reality instruments, ticker, current candles, and historical candles accessed without auth.
- Dedicated Reality depth and fills reject unauthenticated calls and are documented as gated.
- Direct API and `bgc --read-only` results agree for the selected symbol.
- Historical export discovery, retrieval, normalization, UTC ordering, provenance, nullable volume
  and turnover, and fail-closed behavior are covered by deterministic tests and an opt-in live test.

## Failed

- No acceptance check is failing. One initial dependency attempt selected a Pydantic release
  without Python 3.14 support; pins and the hashed lock were corrected before verification.

## Outstanding

- All Phase 1+ data persistence, providers, research, models, backtesting, product UI, and execution.

## Known constraints

- Reality pre-2026-07-09 volume/turnover may be missing; a tested sample happened to contain both.
- Reality depth and platform fills require authentication and whitelist access.
- Capability evidence is a dated Phase 0 observation, not continuous monitoring.
- Separate export runs have distinct ingestion timestamps, and Bitget may revise returned history;
  deterministic serialization does not imply stronger reproducibility than the upstream data.
- No persistent database or production deployment exists.

## Current services

- FastAPI: `/health`, `/api/v1/capabilities`, `/api/v1/markets`.
- Next.js: minimal API capability-status shell.
- Collector: read-only verification and canonical historical JSONL export entry points only.

## Environment requirements

- Python 3.12+
- Node.js 20+
- npm

Verified workstation snapshot: macOS 26.6.2 arm64; Git 2.55.0; Node 24.20.0; npm 11.19.0;
Python 3.14.7; pip 26.2.1 globally and 25.2 in the project environment for `pip-tools`
compatibility; Docker unavailable; GitHub CLI 2.98.0; VS Code 1.134.0.

## Required env vars

No secret env vars are required. Local runtime uses `SESSIONZERO_API_URL`; production will require
explicit service URLs and exact CORS origins; see `.env.example`.

## Test counts

23 deterministic tests passed with two live tests deselected; the separate opt-in live suite passed
with 23 deterministic tests deselected. No TypeScript test suite exists in Phase 0.

## Deployment URLs

`NOT DEPLOYED — PHASE 0`

## Latest commit

`feat(data): add reproducible Reality history export` (new Phase 0 follow-up commit).

## Next exact task

Confirm the Phase 0 historical-export acceptance evidence. No Phase 1 work has started.

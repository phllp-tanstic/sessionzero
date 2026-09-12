# Handover

## Current phase

`PHASE 1 — DATA PLANE (POSTGRESQL PERSISTENCE FOUNDATION SLICE)`

## Completed

- Phase 0 foundation and reproducible JSONL history export remain intact.
- PostgreSQL-only environment configuration, SQLAlchemy persistence package, Alembic migration,
  ingestion-run audit rows, raw JSONB observations, normalized decimal candles, and one-shot live
  Bitget history ingestion are implemented.
- Database uniqueness makes normalized ingestion idempotent; revised upstream payloads remain raw
  evidence without silently replacing the initial normalized candle.

## Verified

- Alembic upgrade, current revision, downgrade, and restored upgrade against PostgreSQL 17.11.
- PostgreSQL integration coverage for run finalization, raw/normalized inserts, direct uniqueness,
  repeated ingestion, UTC, decimal precision, nullable quantities, revision behavior, and rollback.
- Real dynamically validated `RAALUSDT` `1H` range `[2026-06-10T00:00:00Z,
  2026-06-10T06:00:00Z)`: first attempt wrote 6 normalized rows, second wrote 0; final state is 2
  successful runs, 12 raw rows, 6 normalized rows, and 0 duplicate identities.

## Failed

- An initial real query against a different dynamically selected symbol/window returned no rows and
  failed closed before creating a persistence run. The verified window above succeeded.

## Outstanding

- Broader ingestion/backfills, a collector loop, scheduling, native-equity/cross-asset/event
  providers, data-quality rules, retention, models, backtesting, API expansion, and product UI.

## Known constraints

- Raw rows intentionally repeat across separate runs to preserve attempt-level evidence.
- Upstream revisions are not promoted into normalized values; a versioning policy is required.
- A process killed after run creation can leave `RUNNING`; stale-run reconciliation is future work.
- The command handles one upstream response (maximum 100 historical rows), not pagination/backfill.
- No managed production database, database backup policy, or deployment exists.

## Current services

- Existing FastAPI and Next.js Phase 0 surfaces are unchanged.
- One-shot CLI: `sessionzero-ingest-bitget-history`.
- Migration CLI: `alembic upgrade head`.
- No daemon, worker loop, or scheduler exists.

## Required env vars

- `DATABASE_URL`: required for migrations, persistence, and PostgreSQL tests; PostgreSQL/psycopg
  only. Use separate development, test, and production databases.
- Existing public Bitget and web/API settings remain as documented in `.env.example`.

## Test counts

- 30 deterministic non-live/non-PostgreSQL tests.
- 6 direct PostgreSQL integration tests.
- Live Bitget verification remains opt-in.

## Deployment URLs

`NOT DEPLOYED`

## Latest commit

`feat(data): add PostgreSQL market persistence foundation` (this handover's commit).

## Next exact task

Implement bounded historical pagination and explicit candle gap/ordering quality checks on top of
the accepted persistence contract; do not add scheduling yet.

# Handover

## Current phase

`PHASE 1 — DATA PLANE (BOUNDED BITGET HISTORY + CANDLE QUALITY SLICE)`

## Completed

- Phase 0 export and accepted PostgreSQL persistence remain compatible.
- Bitget history now supports bounded backward time pagination for UTC `[start, end)` ranges of up
  to 90 days, with configurable page size and maximum-page guard.
- Typed quality reports cover gaps, duplicates, order, spacing, boundaries, OHLC, price/quantity
  signs, empty results, page overlap, and stalled pagination without creating synthetic candles.
- Migration `20260912_02` adds request range, interval, page count, and quality status to ingestion
  runs while retaining older rows.

## Verified

- Official Bitget history documentation and read-only boundary/order probes were checked on
  2026-09-12.
- Final real-data/database verification completed at `2026-09-12T22:12:16Z`.
- Real metadata-validated `RAALUSDT` `1H` ingestion over
  `[2026-06-10T00:00:00Z, 2026-06-24T00:00:00Z)` used 3 API pages.
- Each attempt received 216 unique candles versus 336 regular UTC timestamps. The report exposed
  120 missing timestamps and 2 unexpected spacings as `WARN`, with no duplicates or invalid OHLC.
- Re-ingestion added zero normalized candles. Final verification state: 2 runs, 432 raw rows, 216
  normalized rows, and zero duplicate normalized identities.

## Failed

- No acceptance check is currently failing. Real weekend-like closures remain visible warnings
  because a trading calendar is intentionally outside this slice.

## Outstanding

- Trading-calendar-aware expected intervals, broader backfills, continuous collection/scheduling,
  native-equity/cross-asset/event providers, models, backtesting, API expansion, and product UI.

## Known constraints

- One request is limited to 90 days by the documented Bitget endpoint contract.
- `max_pages` defaults to 100; high-frequency ranges may require an explicit higher bounded value.
- Every regular UTC interval is currently expected, so known exchange closures are not distinguished
  from unexplained data gaps.
- Full quality reports are emitted by the command but only their summary fields are stored on the
  ingestion run.
- `FAIL` datasets are rejected before the raw/normalized transaction; their machine report is not
  durably stored in this slice.
- No daemon, scheduler, managed database, or deployment exists.

## Current services

- Existing FastAPI and Next.js surfaces are unchanged.
- One-shot CLI: `sessionzero-ingest-bitget-history`.
- Migration CLI: `alembic upgrade head`.

## Required env vars

- `DATABASE_URL`: required for migrations, persistence, and PostgreSQL tests.
- Existing public Bitget and web/API settings remain in `.env.example`.

## Test counts

- 42 deterministic non-live/non-PostgreSQL tests.
- 7 direct PostgreSQL integration tests.
- 2 opt-in live Bitget tests.

## Deployment URLs

`NOT DEPLOYED`

## Latest commit

`feat(data): add bounded history pagination and quality checks` (this handover's commit).

## Next exact task

Add a verified trading-calendar provider and use it to distinguish expected closures from true
missing-candle anomalies without altering stored observations.

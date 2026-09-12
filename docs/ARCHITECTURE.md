# Architecture

## Current runtime

```text
Next.js web shell
        |
        | GET /api/v1/capabilities
        v
FastAPI service
        |
        | public HTTPS, strict timeout/retry policy
        v
Bitget UTA v3 public market API

One-shot history ingestion
        |
        +-- raw provider row (JSONB) --------+
        |                                    |
        +-- validated MarketCandle ----------+--> PostgreSQL
                                                   ingestion_runs
                                                   raw_market_observations
                                                   normalized_market_candles
```

Python is the authoritative quantitative and market-data environment. The browser does not call
Bitget directly. `bgc` is an independent development verification surface and is never invoked by
production code.

## Components

- `packages/schemas`: strict internal Pydantic market and capability contracts.
- `packages/config`: validated environment configuration.
- `packages/bitget`: read-only UTA v3 client, normalization, errors, capabilities, verification CLI.
- `packages/database`: PostgreSQL engine boundary, mapped persistence tables, transactional write
  service, and one-shot ingestion CLI.
- `services/api`: FastAPI health, capability, and discovered-market routes.
- `services/collector`: Phase 0 entry point for the same read-only verification path.
- `apps/web`: minimal status shell; no product dashboard or synthetic market cards.

## Failure boundary

Provider HTTP, network, provider-code, empty-result, and schema failures become structured errors.
The `/api/v1/markets` route returns HTTP 502 for upstream failure and cannot read test fixtures.
Retry is bounded to network errors, HTTP 429, and server errors. All internal times are UTC.
Database commands require an explicit PostgreSQL URL and verify connectivity. Alembic owns schema
changes; the application does not auto-create tables. An ingestion-run row is committed first.
Raw and normalized records plus successful finalization then commit atomically. On a database
write error that transaction rolls back and the run is finalized `FAILED` separately with zero
records written.

## Planned after this narrow Phase 1 slice

Persistent collection loops, native-equity providers, calendars, backfills, data-quality
processing, API expansion, and research remain unbuilt. No queue, cache, scheduler, orchestration
system, ML stack, or deployment workflow has been introduced.

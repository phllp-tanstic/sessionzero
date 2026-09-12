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

Bounded one-shot history ingestion
        |
        +-- bounded backward page traversal
        +-- raw provider rows
        +-- existing MarketCandle normalization
        +-- SourceSessionProvider (Bitget, point-in-time evidence)
        +-- deterministic quality gate
        |       +-- FAIL: report, no data commit
        |       +-- PASS/WARN
        +----------------------------------------> PostgreSQL
                                                   ingestion_runs
                                                   raw_market_observations
                                                   normalized_market_candles

Temporal classification
        |
        +-- TradingCalendarProvider --> XNYS cash sessions
        +-- SourceSessionProvider ----> Bitget source availability
        +-- SessionZeroContext -------> ACTIVE / INACTIVE / UNKNOWN
```

Python is the authoritative quantitative and market-data environment. The browser does not call
Bitget directly. `bgc` is an independent development verification surface and is never invoked by
production code.

## Components

- `packages/schemas`: strict internal Pydantic market, capability, and quality contracts.
- `packages/config`: validated environment configuration.
- `packages/bitget`: read-only UTA v3 client, normalization, errors, capabilities, verification CLI.
  Its history module owns bounded time pagination and candle-series quality evaluation.
- `packages/market_data`: separate reference-calendar and source-session protocols, the pinned XNYS
  adapter, curated Bitget capability provenance, and non-model Session Zero temporal primitives.
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

Historical retrieval validates dataset-level quality before persistence. Critical timestamp,
pagination, OHLC, sign, duplicate, or empty-result defects produce `FAIL` and no raw/normalized
data transaction. Missing timestamps are evaluated through `SourceSessionProvider`: known closures
are informational, absences while known open are warnings, and unknown historical eligibility stays
an explicit warning. Identical page overlap also warns. No quality path synthesizes a candle.

`TradingCalendarProvider` answers only reference U.S. cash-market questions. It cannot decide
whether a Bitget instrument traded. `SourceSessionProvider` answers only source availability from
effective-dated evidence. `SessionZeroContext` combines their typed outputs without producing fair
value, state-model, signal, or strategy output.

## Planned after this narrow Phase 1 slice

Persistent collection loops, native-equity price providers, complete historical Bitget rollout
coverage, API expansion, and research remain unbuilt. No queue, cache, scheduler, orchestration
system, ML stack, or deployment workflow has been introduced.

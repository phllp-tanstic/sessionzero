# Architecture

## Alpaca implementation — current Phase 1 state

The earlier native-provider implementation gate below is superseded for private/local work by
ADR-021. `NativeEquityProvider` now separates native instrument/candle/session/health concepts
from the Alpaca adapter. Existing Bitget mappings, actions, and source-session evidence remain
primary. XNYS supplies exact date-based sessions. Migration `20260919_08` adds raw native pages
and immutable normalized candle versions. The CLI consumes the accepted persisted universe and
existing cohort derivation; no research or public route consumes native prices.
See [full architecture and contract](ALPACA_NATIVE_EQUITY.md). Bounded runtime acceptance passed; see the linked verification results.

`BitgetReferenceDataProvider` is a narrow public, read-only boundary beside the candle client. It
uses explicit `stock-info.code` mappings and normalizes supplemental actions plus Bitget
source-session metadata. It neither implements `NativeEquityProvider` nor changes
`TradingCalendarProvider`/`SourceSessionProvider`; XNYS remains the cash-session authority and no
candle is adjusted here. Persistence is `raw envelope -> validated typed record -> versioned
normalized table`, with per-run raw evidence and immutable normalized versions.

Universe construction is a separate control-plane slice over the same public clients. One
instrument discovery envelope and one `stock-info` envelope produce a canonically sorted snapshot.
The snapshot hash addresses normalized membership plus schema/transformation version; repeated
observations retain new raw envelopes without duplicating logical members. A historical manifest
selects the first N eligible members, invokes the existing bounded pagination, source-session,
quality, and candle-persistence path per symbol, and records every result independently. An
isolated failure does not erase successful peers or masquerade as coverage.

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

Metadata-derived universe --> universe_snapshots / universe_snapshot_members
        |                     universe_discovery_observations (raw envelopes)
        +-- first N eligible --> existing bounded history path
                              --> historical_ingestion_manifests / entries

Accepted universe version --> bounded 60-90 day coverage evaluation
                          --> existing pagination + session-aware quality
                          --> historical_coverage_profiles / members

Temporal classification
        |
        +-- TradingCalendarProvider --> XNYS cash sessions
        +-- typed source evidence ----> deterministic precedence / conflict resolution
        +-- SourceSessionProvider ----> Bitget source availability + provenance
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

The curated source dataset stores one record per official source-level assertion, including clean
symbol sets for batch announcements. `bitget_source_sessions.v2` filters records by explicit scope
and `[effective_from, effective_to)`, then resolves suspension, batch-addition, dated-status-list,
and general-rule evidence in deterministic order. Same-rank contradictory outcomes return
`CONFLICT`; absent, ambiguous-scope, and present-day-only records return no historical assertion.
Every resolved assessment carries evidence IDs/URLs and the transformation version. Current
`stock-info` fields remain universe observation metadata and never enter this historical resolver.

Historical coverage profiling is a separate read-only evaluation path. It loads an accepted
`universe_version` from PostgreSQL, takes the first N technically eligible members in canonical
order, and evaluates exact observations in a fixed UTC window through the existing history and
quality boundaries. It does not write candles or duplicate manifest storage. The root profile and
per-symbol results are content-addressed and idempotent; operational timestamps and retry counters
do not perturb logical identity. The source-evidence expansion changes classification semantics,
so the corrected evidence-qualified profiler output is versioned as
`reality_historical_coverage.v4`; older persisted profiles retain their original semantics.

The evidence-qualified audit derives its cohort from explicit, effective-dated, symbol-scoped
schedule records that cover the entire locked window. Membership also requires presence in the
accepted universe, a native ticker mapping, and no conflict at any evidence-resolution segment.
The derivation never reads a handwritten production list. Its content address binds the universe,
source-evidence and derivation versions, window, interval, and canonical members. The audit then
reuses the existing history client, pagination, normalization, and quality evaluator for every
derived member.

Coverage v4 classifies every expected hourly boundary, including observed boundaries, as known
open, known closed, or source unknown. Known-open observations and missing intervals share the
same explicit denominator; unknown fractions use the complete interval grid. Holiday-qualified
unknown timestamps are retained in full, and an observed start equal to the evaluation start is
stored as left-censored rather than interpreted as launch time.

Structural validity is independent from those completeness metrics. Verified Bitget pre-start
spillover is clipped and retained as warning telemetry. Only objective schema, normalization,
canonical timestamp, OHLC/sign, timestamp-leakage, or pagination failures make structural quality
fail. Duration and final-OOS feasibility are separate booleans using the locked 60-day span and the
deterministic `evaluation_end - 30 days` boundary. `SUFFICIENT_MINIMUM_HISTORY` expresses only
these data-plane chronology requirements, never future research eligibility.

The profiler defaults to 10 serial symbols, rejects more than 20 unless `--full-universe` is
explicit, caps pages/retries, paces requests at no more than the documented 20 requests/second,
honors numeric `Retry-After`, and records requests, retries, and rate-limit responses. There is no
daemon, scheduler, or infinite polling.

Durable lineage is complete from accepted universe through cohort evidence and coverage summary:
profile rows retain the universe, cohort, evidence, transformation, window, interval, and Git
versions, while member rows retain evidence IDs, request telemetry, normalized quality counts, and
coverage decisions. The audit itself remains read-only and therefore does not persist its fetched
request envelopes, raw candle arrays, or normalized candle rows. That request/raw/normalized-to-
profile linkage is intentionally documented as broken rather than falsely inferred; the normal
ingestion workflow remains the only writer of raw and normalized market observations.

## Native-equity provider boundary

`NativeEquityProvider` is implemented with an Alpaca adapter beside the Bitget package. XNYS
supplies exact regular-session boundaries. Native raw pages and normalized immutable versions
have separate provider-neutral tables; they do not enter Bitget `normalized_market_candles`.
The private verifier can reload the accepted persisted universe or reverify its cohort identity
from official membership evidence plus live Bitget mappings without writing a replacement snapshot.
The public API has no native-price path. Bounded runtime acceptance passed; full history,
historical as-known availability, and public-product rights remain separate work.

## Planned after this narrow Phase 1 slice

Persistent collection loops, complete native/Reality historical coverage, API expansion, and
research remain unbuilt. No queue, cache, scheduler, orchestration
system, ML stack, or deployment workflow has been introduced.

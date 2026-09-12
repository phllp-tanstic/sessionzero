# Architecture

## Phase 0 runtime

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
```

Python is the authoritative quantitative and market-data environment. The browser does not call
Bitget directly. `bgc` is an independent development verification surface and is never invoked by
production code.

## Components

- `packages/schemas`: strict internal Pydantic market and capability contracts.
- `packages/config`: validated environment configuration.
- `packages/bitget`: read-only UTA v3 client, normalization, errors, capabilities, verification CLI.
- `services/api`: FastAPI health, capability, and discovered-market routes.
- `services/collector`: Phase 0 entry point for the same read-only verification path.
- `apps/web`: minimal status shell; no product dashboard or synthetic market cards.

## Failure boundary

Provider HTTP, network, provider-code, empty-result, and schema failures become structured errors.
The `/api/v1/markets` route returns HTTP 502 for upstream failure and cannot read test fixtures.
Retry is bounded to network errors, HTTP 429, and server errors. All internal times are UTC.

## Planned after Phase 0 review

PostgreSQL, persistent collection, native-equity providers, calendars, historical ingestion, and
data-quality processing belong to Phase 1. No queue, cache, orchestration system, ML stack, or
deployment workflow has been introduced.


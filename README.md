# SessionZero

Inspect public Reality reference metadata with
`sessionzero-ingest-bitget-reference [--symbol RAAPLUSDT]`; add `--persist` only with an approved
PostgreSQL `DATABASE_URL`. This is supplemental mapping/corporate-action evidence, not native-stock
OHLC or proof of complete coverage or display rights.

Build a metadata-derived, versioned Reality snapshot and a deliberately small bounded-history
manifest with `sessionzero-build-reality-manifest --start ... --end ... --subset-size 3`. The subset
is the first N technically eligible symbols in canonical order; it is not selected using returns or
model results. This command requires PostgreSQL and does not fetch native-equity data.

Price discovery for the market session that did not exist before 24/7 equities.

When the U.S. cash market closes, tokenized equities keep trading while new information continues
to arrive. SessionZero will estimate the next cash-market fair value, determine whether continuous
markets are genuinely discovering that price, and act only when the remaining edge survives
uncertainty and execution costs.

## Current status

`PHASE 1 — DATA PLANE (NATIVE EQUITY PROVIDER ACCESS GATED)`

- **BUILT:** the Phase 0 adapter/export/API/web foundation plus Alembic migrations, PostgreSQL raw
  observation and normalized-candle persistence, ingestion-run audit metadata, and a one-shot
  idempotent bounded history ingestion, machine-readable candle quality, an XNYS reference
  calendar, and evidence-backed point-in-time Bitget source-session semantics.
- **VERIFIED:** unauthenticated instrument, ticker, current-candle, and historical-candle access on
  2026-09-12. Reality depth and platform fills are gated.
- **GATED:** native-equity implementation. Massive is the preferred technical candidate, but no
  provider credential or project-appropriate non-display/public-product license is present. Alpaca
  Basic's IEX-only feed is insufficient as the reference close; Twelve Data also requires resolved
  tier and licensing terms. No speculative adapter or fixture-backed live claim was added.
- **PLANNED:** broader ingestion, collectors, and all quantitative layers after this gate clears.
- **NOT BUILT:** fair value, state, confidence, gap, conviction, backtesting, and execution.

The locked eventual pipeline is `SENSE → FAIR VALUE → STATE → GAP → CONVICTION → EXECUTE`.

## Requirements

- Python 3.12+
- Node.js 20+
- npm 10+

## Setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements.lock
.venv/bin/python -m pip install --no-deps -e .
npm ci
cp .env.example .env
```

No Bitget credentials are required for these public read-only paths. Database commands require an
explicit PostgreSQL `DATABASE_URL`; they never fall back to SQLite or memory.

Create separate development and test databases, then migrate each explicitly:

```bash
export DATABASE_URL=postgresql+psycopg://sessionzero:password@127.0.0.1:5432/sessionzero_development
.venv/bin/alembic upgrade head
.venv/bin/alembic current
```

## Run

```bash
.venv/bin/uvicorn sessionzero_api.main:app --host 127.0.0.1 --port 8000
npm run dev:web
```

The host is configurable; production must set `SESSIONZERO_API_URL` to its deployed
HTTPS API rather than relying on a local address.

Read-only live verification:

```bash
.venv/bin/sessionzero-verify-bitget --interval 1H --limit 5
```

The command discovers the Reality universe from metadata and never falls back to fixtures.

Export a discovered Reality symbol's normalized historical candles:

```bash
.venv/bin/sessionzero-export-bitget-history \
  --symbol RAALUSDT \
  --interval 1H \
  --start 2026-06-10T00:00:00Z \
  --end 2026-06-16T00:00:00Z \
  --limit 100 \
  --output artifacts/raalusdt-2026-06-10_2026-06-16-1h.jsonl
```

Omit `--symbol` to choose the lexicographically first online Reality instrument discovered from
live Bitget metadata. Output is canonical UTF-8 JSONL ordered by UTC `event_time`; each line is one
validated `MarketCandle`. The command fails before publishing on discovery, provider, schema, or
empty-range errors and refuses to replace an existing file unless `--overwrite` is explicit.
Generated files under `artifacts/` are runtime data and are ignored by Git.

Persist a bounded, dynamically validated Reality history window across multiple pages:

```bash
.venv/bin/sessionzero-ingest-bitget-history \
  --symbol RAALUSDT \
  --interval 1H \
  --start 2026-06-10T00:00:00Z \
  --end 2026-06-24T00:00:00Z \
  --page-limit 100 \
  --max-pages 10
```

The command is one-shot, not a collector. It enforces a UTC `[start, end)` range of at most 90
days, walks backward with an explicit maximum-page guard, clips provider boundary spillover, sorts
and deduplicates the result, and prints a structured quality report. Repeating it creates another
run and raw audit records, but the database uniqueness constraint prevents duplicate normalized
candles. Missing timestamps are reported and never filled or interpolated. Missing intervals are
classified as verified source closure, missing while expected open, or unknown source availability;
the current instrument universe is never assumed to have inherited present-day 24/7 support.

Reference cash sessions and Bitget source availability are separate. The XNYS reference calendar
uses pinned `exchange-calendars==4.13.2` for DST, holidays, early closes, previous closes, and next
opens. A version-controlled provenance dataset supplies only cited Bitget capability periods.
Session Zero is `ACTIVE` only while cash is closed and at least one qualifying source is known to
be available; uncertainty remains `UNKNOWN`.

## Checks

```bash
.venv/bin/ruff format --check .
.venv/bin/ruff check .
.venv/bin/pytest -m "not live and not postgres"
npm run lint
npm run typecheck
npm run build
```

Live tests are opt-in: `SESSIONZERO_RUN_LIVE_TESTS=1 .venv/bin/pytest -m live`.
PostgreSQL tests are separate and require a disposable database whose name contains `test`:
`DATABASE_URL=...sessionzero_test .venv/bin/pytest -m postgres`.

See [docs/DATA.md](docs/DATA.md) for provider evidence and [docs/HANDOVER.md](docs/HANDOVER.md)
for the exact current state.

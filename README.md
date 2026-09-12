# SessionZero

Price discovery for the market session that did not exist before 24/7 equities.

When the U.S. cash market closes, tokenized equities keep trading while new information continues
to arrive. SessionZero will estimate the next cash-market fair value, determine whether continuous
markets are genuinely discovering that price, and act only when the remaining edge survives
uncertainty and execution costs.

## Current status

`PHASE 1 — DATA PLANE (POSTGRESQL PERSISTENCE FOUNDATION)`

- **BUILT:** the Phase 0 adapter/export/API/web foundation plus Alembic migrations, PostgreSQL raw
  observation and normalized-candle persistence, ingestion-run audit metadata, and a one-shot
  idempotent Bitget history ingestion command.
- **VERIFIED:** unauthenticated instrument, ticker, current-candle, and historical-candle access on
  2026-09-12. Reality depth and platform fills are gated.
- **PLANNED:** broader ingestion, collectors, reference providers, and all quantitative layers.
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

Persist a small real, dynamically validated Reality history window:

```bash
.venv/bin/sessionzero-ingest-bitget-history \
  --symbol RAALUSDT \
  --interval 1H \
  --start 2026-06-10T00:00:00Z \
  --end 2026-06-10T06:00:00Z \
  --limit 10
```

The command is one-shot, not a collector. Repeating it creates another run and raw audit records,
but the database uniqueness constraint prevents duplicate normalized candles.

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

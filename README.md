# SessionZero

Price discovery for the market session that did not exist before 24/7 equities.

When the U.S. cash market closes, tokenized equities keep trading while new information continues
to arrive. SessionZero will estimate the next cash-market fair value, determine whether continuous
markets are genuinely discovering that price, and act only when the remaining edge survives
uncertainty and execution costs.

## Current status

`PHASE 0 — FOUNDATION + REAL BITGET VERIFICATION`

- **BUILT:** strict typed Bitget UTA v3 public-market adapter, Reality discovery, ticker and candle
  normalization, explicit capability states, minimal FastAPI routes, verification CLI, test suite,
  minimal Next.js system shell, and secret-free CI.
- **VERIFIED:** unauthenticated instrument, ticker, current-candle, and historical-candle access on
  2026-09-12. Reality depth and platform fills are gated.
- **PLANNED:** the data plane and all quantitative layers after Phase 0 review.
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

No Bitget credentials are required or used in Phase 0.

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

## Checks

```bash
.venv/bin/ruff format --check .
.venv/bin/ruff check .
.venv/bin/pytest -m "not live"
npm run lint
npm run typecheck
npm run build
```

Live tests are opt-in: `SESSIONZERO_RUN_LIVE_TESTS=1 .venv/bin/pytest -m live`.

See [docs/DATA.md](docs/DATA.md) for provider evidence and [docs/HANDOVER.md](docs/HANDOVER.md)
for the exact current state.

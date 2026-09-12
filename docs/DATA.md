# Data Verification

Status labels in this document mean `BUILT`, `VERIFIED`, `PLANNED`, `BLOCKED`, or `UNVERIFIED`.
All runtime observations below were unauthenticated, read-only, and made on 2026-09-12.

## Official documentation reviewed

| Capability | Official documentation URL | Documented endpoint | Documented access | Observed access | Observed UTC timestamp | Notes |
|---|---|---|---|---|---|---|
| Reality guide and identification | https://www.bitget.com/docs/uta/reality-trading-guide | Reuses instruments; `isReality` flag | Capability table says public | **VERIFIED** public | 2026-09-12T13:45:47Z | `isReality=yes` is the canonical filter. The symbol prefix is descriptive, not used as authority. |
| Instruments | https://www.bitget.com/docs/catalog/market-market-data/market-instruments | `GET /api/v3/market/instruments` | Public, 20 requests/s/IP | **VERIFIED** public; code `00000` | 2026-09-12T13:45:47Z | `category=SPOT` returned 1,173 Reality instruments. Older `/api/v3/public/instruments` returned `40404`. |
| Ticker | https://www.bitget.com/docs/catalog/market/market-data | `GET /api/v3/market/tickers` | Public | **VERIFIED** public; code `00000` | 2026-09-12T13:46:14Z | Dynamically selected `RAALUSDT`; returned ticker timestamp and non-empty price/volume fields. |
| Current candles | https://www.bitget.com/docs/catalog/market/market-data | `GET /api/v3/market/candles` | Public in capability table | **VERIFIED** public; code `00000` | 2026-09-12T13:46:14Z | `1H`, `market`, five rows. Unsupported `3m` returned `48001`. |
| Historical candles | https://www.bitget.com/docs/catalog/market/market-data | `GET /api/v3/market/history-candles` | Public in capability table | **VERIFIED** public; code `00000` | 2026-09-12T13:46:33Z | Pre-2026-07-09 sample returned 100 rows. Volume/turnover were present in this sample; docs say they *may* be empty, so schemas preserve missing values. |
| Reality depth | https://www.bitget.com/api-doc/uta/public/Reality-OrderBook | `GET /api/v3/account/reality-orderbook` | API key plus whitelist | **GATED**; unauthenticated code `40006` | 2026-09-12T13:47:00Z | No synthetic fallback. |
| Reality platform fills | https://www.bitget.com/api-doc/uta/public/Reality-Fills | `GET /api/v3/account/reality-fills` | API key plus whitelist | **GATED**; unauthenticated code `40006` | 2026-09-12T13:47:00Z | No synthetic fallback. |

## Documentation contradiction

The Reality guide's capability table labels instruments, ticker, and candles public, but a broad
note says Reality market-data endpoints are only open to whitelisted users. The endpoint-specific
depth and fills pages require both authentication and whitelisting. Runtime evidence resolves the
safe Phase 0 behavior: the four reused market endpoints are currently public; the two dedicated
`/api/v3/account/reality-*` endpoints are gated. Capability states reflect both documentation and
observation, not the broad note alone.

## Reality candle contract

- Type: `market` only. Other documented types may silently fall back, so SessionZero sends only
  `market`.
- Intervals: `1m`, `5m`, `15m`, `1H`, `4H`, `1D` only.
- Before 2026-07-09, volume and turnover may be empty. Empty strings, absent columns, and nulls are
  normalized to `null`, never zero.
- Current endpoint maximum: 1,000 rows. Historical endpoint maximum: 100 rows and at most 90 days
  per requested range.

## Direct API / Agent Hub cross-check

Official Agent Hub source: https://github.com/Bitget-AI/agent-cli

At 2026-09-12T13:50Z, `bgc --read-only` used the same four `/api/v3/market/*` paths for
`RAALUSDT`. Instrument identity (`SPOT`, `isReality=yes`), ticker value/timestamp, and two `1H`
candle rows matched direct API behavior. `bgc` is useful for independent development verification;
the application has no runtime dependency on it.

### Agent Hub installation record

- Official repositories/docs: https://github.com/Bitget-AI/agent_hub and
  https://github.com/Bitget-AI/agent-cli
- CLI installation: `npm install -g @bitget-ai/bitget-agent-cli@3.0.0`.
- CLI package: `@bitget-ai/bitget-agent-cli` 3.0.0; `bgc --version` reports
  `bitget-agent-sdk` 3.1.0.
- Skill installation: `npx --yes @bitget-ai/bitget-agent-skill@3.2.1 --target codex`.
- Codex skill status: **VERIFIED INSTALLED** at the user Codex skill location.
- `bgc discover`: seven domains (`market`, `trade`, `account`, `funds`, `subaccount`, `loan`,
  `tax`) plus raw/auth/discovery meta tools. The market verb fronts 16 public read operations,
  including instruments, tickers, current/history candles, ordinary order books, and fills.
- Phase 0 market cross-check: **VERIFIED** with `--read-only`; no credentials.
- Agentic Account authorization: **NO — PLANNED, NOT AUTHORIZED**.

## Provenance and retention

Normalized records include source, market/category, symbol, UTC event time where the provider
supplies one, UTC ingestion time, and raw/derived status. Durable persistence, dataset versioning,
availability timestamps, duplicate/gap checks, and point-in-time replay are **PLANNED** for Phase 1.

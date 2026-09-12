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

### Historical pagination verification — 2026-09-12

The current official history documentation defines `startTime` as data after the start, `endTime`
as data before the end, a maximum/default limit of 100, and a maximum 90-day query range. It warns
that an `endTime` even 1 ms beyond an interval boundary can round the calculation and return an
additional earlier interval. It does not document response ordering or a cursor.

Read-only `RAALUSDT` probes established the behavior used by this adapter: responses were ascending,
`limit` selected the newest rows before the requested end, an aligned start timestamp was included,
an aligned end timestamp was excluded, and a non-aligned start could be rounded down. These are
dated observations rather than a stronger provider guarantee. SessionZero therefore paginates
backward by setting the next `endTime` to the oldest returned event time, rejects non-progress,
enforces a caller-controlled maximum page count, and independently clips the final dataset to UTC
`[start, end)`.

## Reference and source-session verification — 2026-09-12

Reference cash-market sources:

- NYSE official hours and holidays: https://www.nyse.com/trade/hours-calendars. Core trading is
  9:30 a.m.–4:00 p.m. Eastern. The 2026 calendar marks June 19 as closed and November 27 and
  December 24 as 1:00 p.m. Eastern early closes.
- Nasdaq official U.S. holiday schedule:
  https://www.nasdaq.com/market-activity/stock-market-holiday-schedule. It independently confirms
  the 2026 Juneteenth closure, 9:30 a.m.–4:00 p.m. Eastern regular hours, and the November 27 and
  December 24 early closes.
- Maintained implementation: https://pypi.org/project/exchange-calendars/ at pinned version
  `4.13.2`, using its `XNYS` calendar. Deterministic checks match the official dates above and
  verify the U.S. DST shift from a 14:30 UTC open on March 6, 2026 to 13:30 UTC on March 9.

Bitget source-session evidence:

- The official rToken trading-hours article, published `2026-06-23 07:39`, states a general 24/5
  extended schedule and warns that weekend and U.S. holiday access may be limited:
  https://www.bitget.com/support/articles/12560603887176. SessionZero conservatively uses its
  publication timestamp as the earliest supported evidence boundary and does not project it back.
- The official rollout published `2026-07-17 03:40` adds 22 named rTokens, including `rMRNA`, to
  weekend/24/7 trading and explains DST-aware weekend operation:
  https://www.bitget.com/support/articles/12560603889487. It establishes an effective transition
  for `RMRNAUSDT`; it does not establish RAAL eligibility or retroactively cover earlier dates.
- Bitget's current campaign page says rTokens are now 24/7, but it has no symbol-level historical
  effective dates: https://www.bitget.com/campaigns/bitget-rtoken. It is current marketing evidence,
  not authority for historical eligibility.

The curated capability records live in
`packages/market_data/sessionzero_market_data/data/bitget_source_sessions.json`. Each record has
symbol, effective bounds, session mode, source, evidence URL, verification timestamp, and notes.
Wildcard 24/5 evidence cannot prove that an unlisted symbol lacked a separate weekend exception;
such weekend assessments remain `UNKNOWN`. Holiday availability also remains unknown unless an
announcement explicitly establishes it.

### Historical window reinterpretation

The real `RAALUSDT` `1H` window `[2026-06-10T00:00:00Z, 2026-06-24T00:00:00Z)` still contains 216
candles over 336 interval boundaries. All 120 absent hours predate the earliest RAAL-applicable
cited session evidence. They are now `SOURCE_SESSION_UNKNOWN`: 0 proven expected closures, 0 proven
missing-while-open intervals, and 120 unknown. Their alignment with weekends and Juneteenth is
not promoted into a source-closure claim.

For comparison, the evidenced post-rollout `RMRNAUSDT` weekend
`[2026-07-18T00:00:00Z, 2026-07-20T00:00:00Z)` has 48 expected 24/7 hourly intervals. The live API
returned 48 rows but only 2 were inside the requested range (`2026-07-18T13:00:00Z` and
`2026-07-19T14:00:00Z`); 46 boundary-spillover rows were clipped. The quality result therefore
reports 46 `MISSING_WHILE_EXPECTED_OPEN` intervals and `FAIL`. An independent read-only `bgc`
request reproduced the same provider rows. A documented ability to trade does not guarantee an
hourly candle when no qualifying trade prints.

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
supplies one, UTC ingestion time, and raw/derived status.

### Historical export contract

Run the production exporter with an explicit UTC half-open range `[start, end)`:

```bash
.venv/bin/sessionzero-export-bitget-history \
  --symbol RAALUSDT \
  --interval 1H \
  --start 2026-06-10T00:00:00Z \
  --end 2026-06-16T00:00:00Z \
  --limit 100 \
  --output artifacts/raalusdt-2026-06-10_2026-06-16-1h.jsonl
```

The command always discovers the Reality universe through `GET /api/v3/market/instruments` and
accepts a requested symbol only when current metadata identifies it as an online Reality
instrument. With no `--symbol`, it deterministically selects the lexicographically first online
Reality symbol. It then requests real `market` candles from
`GET /api/v3/market/history-candles`, normalizes every row through `MarketCandle`, filters to the
requested half-open range, rejects duplicate event times, sorts ascending by `event_time`, and
atomically publishes only a complete non-empty result. Fixtures and synthetic records are not
production inputs.

The format is canonical UTF-8 JSON Lines with one compact, key-sorted object and one LF terminator
per normalized candle. Every object contains `source`, `symbol`, `market`, `event_time`,
`ingestion_time`, `raw_or_derived`, `interval`, `open`, `high`, `low`, `close`, `volume`, and
`turnover`. Times serialize in UTC. Decimal values serialize as strings to preserve decimal
meaning. Missing provider volume or turnover serializes as JSON `null`, never zero.

For identical upstream observations and a fixed ingestion clock, record ordering and serialized
bytes are deterministic. In normal operation `ingestion_time` intentionally records the current
ingestion run, so exports from separate runs are not expected to be byte-identical; tests compare
market-record content independently of that field. Bitget may revise upstream observations, and
the historical endpoint returns at most 100 records for a request of at most 90 days, so this
exporter makes no stronger replay or completeness guarantee than that upstream response permits.

Exports belong under `artifacts/`, which is ignored by Git. They must not be committed or mixed
with deterministic test fixtures. Dataset versioning, availability timestamps, gap checks, and
point-in-time replay remain outside this slice.

## PostgreSQL persistence contract

Alembic revision `20260912_01` creates:

- `ingestion_runs`: one row per persistence attempt. `records_received` is the number of validated
  upstream observations presented to persistence; `records_written` is newly inserted normalized
  candles.
- `raw_market_observations`: the original Bitget candle array in JSONB plus endpoint, UTA version,
  source identity, UTC event/ingestion times, and owning run. Its per-run unique constraint prevents
  duplicate raw inserts inside one attempt while retaining each separate attempt as audit evidence.
- `normalized_market_candles`: exact arbitrary-precision PostgreSQL `NUMERIC` OHLC, nullable
  volume/turnover, UTC `TIMESTAMPTZ`, and a database uniqueness constraint on source, symbol,
  market, interval, and event time.

The boundary is `raw provider row → existing MarketCandle validation → normalized row`. Both data
rows are written in one transaction. An identical/retried candle leaves the existing normalized
row unchanged, including its original ingestion time. If Bitget revises a candle, the new raw row
preserves that evidence but the normalized row is conservatively not overwritten. A future
versioned revision model must be designed before revisions can replace canonical values.

PostgreSQL `TIMESTAMPTZ` stores instants independent of display timezone. SessionZero connections
set their session timezone to UTC, and tests verify UTC-aware round trips. Decimal input is never
routed through binary floating point.

## Bounded history quality contract

The one-shot workflow accepts at most a 90-day interval and a historical page size from 1 through
100. Pages are bounded by `max_pages`; empty responses terminate, and stale/non-progressing cursors
or an exhausted page budget fail explicitly. Identical records repeated across adjacent pages are
deduplicated deterministically and reported as a warning. Conflicting or same-series duplicates,
out-of-order timestamps, boundary spillover, empty datasets, impossible OHLC relationships,
non-positive prices, and negative volume/turnover are failures.

Expected timestamps are regular UTC multiples of the requested interval within `[start, end)`.
Each absent timestamp is classified through point-in-time source evidence:
`EXPECTED_SOURCE_CLOSURE` is informational and not a gap; `MISSING_WHILE_EXPECTED_OPEN` is a
warning; and `SOURCE_SESSION_UNKNOWN` is a warning that cannot be silently resolved either way.
Totals and at most ten examples are emitted per class. There is no forward fill, interpolation, or
synthetic zero-volume record. Null volume or turnover remains valid because Bitget documents those
fields as possibly absent for older Reality history.

Quality validation occurs before persistence. `FAIL` datasets are returned as structured evidence
and do not enter the raw/normalized transaction. `PASS` and `WARN` datasets persist through the
accepted transaction and idempotency contract. Migration `20260912_02` adds nullable request start,
request end, interval, page count, and quality status to ingestion runs while preserving older rows.

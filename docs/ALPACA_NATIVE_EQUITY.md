# Alpaca native-equity implementation — 2026-09-19

Phase 1 only. Implementation is available for private/local evaluation. The bounded runtime acceptance gate **PASSED**; this is not a complete native history dataset. No model, return calculation, full backfill, public output, or deployment.

## Current official contract

Reviewed 2026-09-19 using official sources:

- [Single-symbol bars](https://docs.alpaca.markets/us/reference/stockbarsingle-1):
  `GET https://data.alpaca.markets/v2/stocks/{symbol}/bars`, `timeframe=1Min`, explicit `feed=sip`,
  `adjustment=raw`, ascending order, RFC3339 bounds. Provider bounds are inclusive; our output is
  clipped to `[start,end)`. Pages allow 1–10,000 rows and require following `next_page_token`,
  including after short pages. Available adjustment modes include raw, split, dividend, spin-off,
  and all. `asof=-` disables provider rename stitching; it is not a historical database vintage.
  HTTP 400 denotes bad input, 401 authentication, 403 forbidden, 429 throttling, and 500 server
  failure. Rate-limit response headers guide throttling. Redirects are not followed.
- [Plans/authentication](https://docs.alpaca.markets/us/docs/about-market-data-api): Trading API
  authentication uses `APCA-API-KEY-ID` and `APCA-API-SECRET-KEY`. Basic historical requests are
  limited to 200/minute; Plus documents 10,000/minute. Technical plan access does not clear rights.
- [FAQ](https://docs.alpaca.markets/us/docs/market-data-faq): historical SIP on Basic is accessible
  when `end` is at least 15 minutes old. The adapter adds a five-second safety margin and never
  retries using IEX. The current FAQ defines minute timestamps as the left edge of the interval,
  aggregating by SIP trade timestamp. Price-update eligibility depends on trade conditions, so
  minute OHLC need not equal the first/last trade of every condition. The older participant-time
  explanation is not used as authority. The runtime checks below confirm minute alignment and boundary selection, not auction equivalence.
- [Request IDs](https://docs.alpaca.markets/us/docs/getting-started-with-alpaca-market-data): retain
  `X-Request-ID`. Absence remains absence, not a fabricated identifier.
- [Historical auctions](https://docs.alpaca.markets/us/reference/stockauctions-1): Alpaca exposes
  a separate SIP auction-price endpoint. Auction prices are **not proven unavailable**. Account
  access, venue interpretation, and cohort coverage have not been tested. The
  [historical trades endpoint](https://docs.alpaca.markets/us/reference/stocktradesingle-1) provides
  an additional verification route; neither surface is integrated as a target or fallback here.
- [24/5 documentation](https://docs.alpaca.markets/us/docs/245-trading-for-trading-api): the free
  plan lists delayed historical BOATS bars/quotes/trades via `feed=boats`; the end must be old
  enough. Record only **AVAILABLE_SUPPLEMENTAL_FUTURE_SOURCE**. No BOATS request or feature exists.

## Target contract: native_equity_minute.v1

`FIRST_1M_BAR_OPEN` is the open field of the bar timestamped exactly at the XNYS scheduled open.
`LAST_1M_BAR_CLOSE` is the close field of the bar timestamped exactly one minute before the XNYS
scheduled close. On a normal summer session these timestamps are 13:30Z and 19:59Z. An early close
uses its actual calendar boundary. A holiday is rejected rather than rolled forward implicitly.

These are observable consolidated minute-bar targets, **not OFFICIAL_AUCTION_PRINT**, and not
unqualified first/last SIP trade prices. The last regular minute excludes a print timestamped
exactly at the close. A close-timestamp bar may contain extended-hours activity and is excluded.
XNYS is the schedule convention; it does not assert every cohort member is NYSE-listed.

Missing boundary minutes produce `MISSING_BOUNDARY_MINUTE` and a null price. No neighboring
minute, daily bar, IEX bar, zero, interpolation, or synthetic trade replaces them. Empty valid
history is structurally valid. Invalid payloads, OHLC, order, duplicates, pagination, and
post-normalization leakage fail structurally. This explicitly adopts the observable definition
allowed by the current task, superseding selection V2's requirement to reject every non-auction
proxy. Future modeling must retain this definition or separately approve/version a target change.

## Provider and mapping boundary

`NativeEquityProvider` exposes instrument lookup, bounded candles, session open/close, and health.
`AlpacaNativeEquityProvider` implements it in `packages/market_data`; business/research consumers
need not import Alpaca. `NATIVE_EQUITY_PROVIDER=alpaca` selects the adapter explicitly.
`TradingCalendarProvider.session_on` returns an exact dated XNYS session. Corporate actions remain
in the existing Bitget ingestion path.

Instrument lookup consumes the existing `EvidenceQualifiedCohort`, whose native ticker comes
from accepted Bitget universe metadata. It does not fetch an alternative symbol master, strip
prefixes, or claim a permanent identifier. The normal CLI reloads the accepted universe and reruns the existing evidence-cohort derivation.
The authorized alternative `--evidence-record bitget.2026-06-12.weekend-batch-21` obtains membership
from that record and resolves every ticker through `BitgetReferenceDataProvider.get_mapping`.
Both modes check the supplied cohort hash and exactly 21 members. The alternative references the
original universe hash for verification only; it does not create a replacement universe snapshot. Missing accepted evidence fails closed; fresh metadata must not be silently
relabeled as the old accepted universe. `asof=-` avoids hidden rename remapping; effective-dated
security identity and ticker reuse remain limitations.

## Authentication, capabilities, and requests

Only `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` environment variables supply credentials. There are
no credential constructor arguments, persisted auth headers, provider-body error messages, or
credential logs. Health reports `GATED` before access is verified or if credentials are missing;
valid retrieval makes it `AVAILABLE`. Auth/entitlement failure is `GATED`, transient exhaustion
`DEGRADED`, and structural/provider failure `UNAVAILABLE`. Missing targets are separate from health.

The synchronous adapter paces requests at least 0.31 seconds apart, including retries, with at
most three retries by default (configuration capped at five), 100 pages by default (cap 1,000),
and a maximum 90-day range. Repeated tokens, empty nonterminal pages, duplicate timestamps, and
backward order fail. Numeric and HTTP-date `Retry-After` are honored; a throttle reset timestamp
is used when supplied. A server-required delay above 60 seconds stops the operation instead of
retrying early. Without server guidance retries use bounded exponential delay. There is no
claim that Retry-After is guaranteed by Alpaca. Request/rate-limit/retry counts and safe response
metadata remain available, including for failed attempts. Multiple processes sharing one key
still require coordination; this slice is serial, one-shot, and not a distributed collector.

## Persistence and point-in-time limits

Migration `20260919_08` adds provider-neutral `raw_native_equity_observations` and
`normalized_native_equity_candles`. Raw pages retain exact decoded JSON text, preserving numeric
lexemes, plus safe response headers, endpoint, request parameters/bounds, source, ticker, Reality
symbol, universe/cohort versions, ingestion time, page index, and ingestion-run linkage. Header
retention is allowlisted. Normalization parses JSON decimal numbers directly as Decimal.

Normalized identity is source, native ticker, interval, event time, feed, adjustment, and a
content hash. Numeric-equivalent decimal encodings deduplicate. OHLCV, count, VWAP, New York date,
UTC event/ingestion timestamps, transformation version, and first raw-page linkage are retained.
PostgreSQL uses NUMERIC and TIMESTAMPTZ. Repeated retrievals append raw evidence while identical
normalized versions deduplicate. Changed provider content appends a distinct immutable version.
Reversion to old content reuses that version while the new raw page proves reobservation. No
implicit latest/canonical revision wins. Raw/normalized writes and successful run finalization
are atomic; a failed write rolls back data and leaves a separately finalized failed run.

There is no provider revision ID or original publication-time proof. Retrieval time is when this
system observed a version, not when it first existed historically. Raw adjustment prevents future
split/dividend restatement, but cannot recover historical as-known bars. These observations must
not be silently introduced as prediction-time features; next opens can only become subsequent
outcome labels in separately authorized research. No feature or label dataset is constructed here.
`session_date` on generic candles is their New York date, not evidence of regular-session membership.

## Private verification command

Load credentials into the command's environment without printing them. Supply the database
containing the accepted universe, then run:

```sh
NATIVE_EQUITY_PROVIDER=alpaca .venv/bin/python -m sessionzero_database.native_cli \
  --universe-version "$NATIVE_UNIVERSE_VERSION" \
  --cohort-version "$NATIVE_COHORT_VERSION" \
  --output artifacts/native-equity-verification.json --persist
```

For the evidence/live-mapping mode, add `--evidence-record bitget.2026-06-12.weekend-batch-21`.
The **full original** universe hash is still required to reproduce the accepted cohort hash.
Omit `--persist` to run without DATABASE_URL; no universe snapshot is created in that mode.
Run Alembic upgrade first when persisting. `--persist` adds PostgreSQL writes; without it the provider/DB reads
are read-only and complete successful raw histories are retained in the private report. Reports
are created exclusively with mode 0600, refuse overwrite, and belong only in ignored local
`artifacts/`. Console output contains counts/status, never prices. No web/API route exposes them.

The probe first requests AAPL/NVDA/TSLA with two rows/page over five opening minutes. It then
checks boundary targets for every accepted member without replacement. Finally it selects the
first five canonical cohort symbols and five evenly spaced scheduled sessions in the accepted
window, reporting same-session opening/closing targets plus the next session's opening target.
Selection depends on the calendar and cohort only, not observed prices or success. Every failure
remains explicit. No 90-day backfill, returns, alpha, or BOATS feature is calculated.

Opt-in integration test: `SESSIONZERO_RUN_LIVE_ALPACA=1` plus credentials, provider selection,
DATABASE_URL, NATIVE_UNIVERSE_VERSION, and NATIVE_COHORT_VERSION. Ordinary CI needs none of these.

## Runtime gate and licensing

Credentials were successfully loaded from the owner-supplied ignored `.env.alpaca.local` without
printing or recording their contents. The database-independent membership path derived the 21
members from `bitget.2026-06-12.weekend-batch-21` and resolved all tickers through live Bitget
metadata. All pairs matched the owner's cross-check. No hardcoded production list was introduced.

The owner supplied the complete original universe reference:
`e0580746df9d0581bbd629e0a07dde94ce6ff04e973718fb8a1c3a103e81bd06`.
Recomputing the existing identity contract produced the exact accepted cohort hash:
`a69d8c427abac466e8b4088f109e55640bc9e5172011ec6b70919b1874176f32`.
The live run repeated that check before any Alpaca request. No old identity was assigned to a new
snapshot; the verification database contains zero universe snapshots.

The bounded run started at **2026-09-19T20:12:35.798747Z** and passed:

- AAPL, NVDA, TSLA: five raw SIP 1Min observations each, three pages each with a two-row page
  limit. Observed timestamps were 2026-06-16 13:30Z through 13:34Z. The provider's inclusive-end
  observation was retained raw and clipped from the half-open result.
- All **21/21** accepted symbols had both exact opening and closing minutes on June 16; no
  replacement or exclusion. This is bounded availability evidence, not full-window completeness.
- **25/25** deterministic rows passed: AAOI, AAPL, AMD, AMZN, ASTS across June 16, July 9,
  July 30, August 20, and September 11. Each row includes that session's open/close and the next
  session's open. XNYS bounds were 13:30Z–20:00Z; selected closing bar timestamps were 19:59Z.
  Following sessions were June 17, July 10, July 31, August 21, and September 14 (weekend crossed).
- 126 Alpaca requests, zero retries, zero rate-limit responses; request IDs present on all 126
  pages and `X-RateLimit-Limit=200` throughout. This is Basic-consistent historical SIP behavior;
  the account subscription itself was not queried. Runtime does not prove trade-level aggregation
  or official auction identity; those remain explicitly outside the minute observable definition.
- 120 successful history persistence runs retained 126 raw pages, 132 in-window candle
  observations, and 119 unique normalized versions. A three-page live AAPL repeat appended
  three raw pages and **zero** normalized versions. Final database totals: 121 runs, 129 raw
  pages, 119 normalized versions, zero universe snapshots. No correction was observed in that
  repeat; correction handling is verified by deterministic PostgreSQL tests.

Private mode-0600 artifacts (ignored, never committed or published):
`artifacts/native-mapping-verification.json` retains 42 mapping response envelopes;
`artifacts/native-equity-verification.json` retains the complete run, 42 fresh mapping envelopes,
raw Alpaca pages, normalized observations, target values, request metadata, and run IDs;
`artifacts/native-equity-target-pairs.json` contains the 25 reviewable rows with event/ingestion
and request bounds, request IDs, and links into the source report. These files contain raw prices
and must stay local. A separate repeat summary records only counts and a run ID.

Local evidence database: `sessionzero_native_verification` on loopback port 55439, isolated from
`sessionzero_native_test`. Both use `/tmp/sessionzero-native-test-pg`; this temporary local cluster
is not managed durable production storage. Retain/backup private evidence under the eventual
agreed retention policy before deleting it. No full 90-day backfill was performed.

Verification: 136 deterministic non-live/non-PostgreSQL tests and 15 PostgreSQL tests pass.
The PostgreSQL suite exercises fresh migrations, downgrade/upgrade, raw retention, normalized
idempotency, changed-content corrections, empty valid history, UTC/NUMERIC round trips, and atomic
rollback. The opt-in live Alpaca pytest was skipped; the complete production CLI was run live
instead. Ruff checks and format validation pass. The one existing Starlette/AnyIO deprecation
warning remains unrelated. The engineering/runtime acceptance gate passes for this bounded slice.

Private/local evaluation is authorized by the current user task, with rights confirmation pending.
`ALPACA_TECHNICAL_FIT`, `ALPACA_BASIC_HISTORICAL_SIP`, `ALPACA_MINUTE_HISTORY`, and
`ALPACA_RAW_ADJUSTMENT` are **AVAILABLE** in the documented contract and the bounded runtime checks above (Basic tier is
consistent with response limits, not independently read from an account endpoint).
`ALPACA_PRIVATE_RESEARCH_USE=PROVISIONAL`, `ALPACA_PUBLIC_RAW_DISPLAY=NOT_APPROVED`, and
`ALPACA_PUBLIC_DERIVED_OUTPUT_RIGHTS=UNVERIFIED`. This implementation grants no publication rights.

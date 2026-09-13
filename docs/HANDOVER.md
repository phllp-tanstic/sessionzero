# Handover

## Current phase

`PHASE 1 — DATA PLANE (NATIVE EQUITY PROVIDER ACCESS GATED)`

## Completed

- Accepted bounded Bitget ingestion and PostgreSQL persistence remain compatible.
- Separate `TradingCalendarProvider` and `SourceSessionProvider` protocols prevent cash-market
  schedules from being mistaken for source availability.
- Pinned `exchange-calendars==4.13.2` supplies XNYS DST, holiday, early-close, and adjacent-session
  semantics in UTC.
- Version-controlled Bitget capability records carry effective bounds and source provenance.
- Gap quality now distinguishes expected source closure, missing while expected open, and unknown
  source availability without synthesizing observations.
- Typed `SessionZeroContext` produces only temporal `ACTIVE`/`INACTIVE`/`UNKNOWN` primitives.
- Public `BitgetReferenceDataProvider` validates explicit Reality/native mappings, actions, and
  Bitget source-session metadata without authentication.
- Raw response envelopes and versioned normalized reference records use separate PostgreSQL
  tables; repeats deduplicate and corrections append rather than overwrite.
- Metadata-derived Reality snapshots now retain complete discovery envelopes, content-address
  canonical members, and attach typed technical eligibility/exclusion evidence.
- Historical manifests deterministically ingest the first N eligible members through the existing
  quality/session/persistence path and preserve isolated failures per symbol.
- Historical coverage profiles now load an accepted universe version, evaluate the canonical first
  N members through the existing bounded/session-aware quality path, and persist content-addressed,
  idempotent profile/member evidence without storing another candle copy.
- Historical manifests now distinguish `normalized_records_written` (new inserts in that run) from
  `records_available_for_requested_window` (validated unique observations in the requested range).
- Bitget requests support explicit pacing, bounded retries, numeric `Retry-After`, retry exhaustion,
  and request/retry/rate-limit telemetry.

## Verified

- Final session-aware live verification completed at `2026-09-12T22:55:23Z`.
- NYSE and Nasdaq official 2026 calendars confirm Juneteenth closure, 9:30–16:00 Eastern regular
  hours, and November 27/December 24 early closes.
- XNYS tests verify normal days, weekends, Juneteenth, early close, previous/next boundaries, and
  the March 2026 DST shift.
- RAAL's June window remains 216/336 observations; all 120 absences are now explicit source-session
  unknowns because cited RAAL eligibility does not cover those timestamps.
- Official Bitget evidence places `RMRNAUSDT` in a 24/7 rollout on `2026-07-17 03:40`. Its tested
  July 18–20 weekend had 2 in-range candles, 46 missing-while-open intervals, and quality `FAIL`.
- Follow-up verification on `2026-09-13` used exact, end-only, adjacent-day, nearby control,
  page-size, and millisecond-alignment probes. It confirmed that sparse two-boundary requests can
  backfill earlier records instead of applying `startTime` as a strict response filter.
- Independent read-only `bgc` output reproduced all 48 exact-window RMRNA provider rows.
- A live `page_limit=1` adapter run reached both in-range candles in three backward pages and
  clipped one older row, confirming that the SessionZero pagination cursor is correct.

## Failed

- The RMRNA comparison still fails quality because Bitget history contains only two candle records
  in the verified-open two-day window. This is a confirmed provider-history gap, not a proven feed
  outage, and no SessionZero pagination defect was found.
- Native-equity implementation did not pass its provider gate. Massive, Alpaca, and Twelve Data
  were reviewed against current official documentation at `2026-09-13T10:32:29Z`; no credentials
  or project-appropriate non-display/public-product license is present. Per ADR-011, no speculative
  adapter, schema, mapping, migration, or fixture-backed live result was added.
- Bitget-native reference-data verification completed at `2026-09-13T11:42:27Z`. Public Reality
  endpoints now provide native-ticker mapping, sessions/calendar, dividends, and splits; public UTA
  exposes stock perpetuals and their reference indices. Native Stock+ quotes and OHLC remain gated
  by signed read-only access, which was not authorized or used.
- Production reference ingestion was verified on 2026-09-13 UTC with `RAALUSDT -> AAL`,
  `RAAPLUSDT -> AAPL`, and `RMRNAUSDT -> MRNA`. The AAPL bundle contained 92 dividends, nine split
  observations, one share-capital row, one suspension row, and nine raw responses. First
  persistence wrote 105 normalized and nine raw rows; an identical repeat wrote zero normalized
  and nine new per-run raw rows.
- Live universe verification at `2026-09-13T16:25:55Z` discovered 1,173 Reality instruments with
  1,173 mappings and technical eligibilities. One source-session assessment was known and 1,172
  were unknown without exclusion. The canonical first-three two-hour manifest selected RAAL,
  RAAOI, and RAAON; all received two rows, passed quality, and linked to successful ingestion runs.
- A 2026-09-13 canonical first-10 coverage pilot used accepted universe `85c5d4fb...b8db5` and the
  90-day 1H window ending `2026-09-13T20:00:00Z`. It made 139 serial requests with no retry or
  throttle response. Three members were `SOURCE_SESSION_TOO_UNKNOWN`, seven were
  `DATA_QUALITY_FAILURE`, and none passed sufficiency. Durations were 88.0-90.0 days with an
  88.166667-day median. A deterministic repeat resolved to the same profile identity.
- Migration `20260913_05` and all 11 PostgreSQL integration tests passed against an isolated local
  PostgreSQL instance. The 73 non-live/non-PostgreSQL tests also passed.

### Bitget-native capability matrix

| Capability | Status | Endpoint / evidence | Operational consequence |
|---|---|---|---|
| Reality to native ticker | **AVAILABLE** | Public `reality/market/stock-info`; live `RAAL->AAL`, `RAAPL->AAPL`, `RMRNA->MRNA` | Mapping substrate can come from Bitget, but ticker is not a permanent identifier. |
| ISIN/CUSIP/FIGI | **UNAVAILABLE** | No such field in reviewed Reality, UTA, or Stock+ schemas | A canonical identifier source remains external. |
| Native regular close / next open | **GATED** | Stock+ quote and session-filtered OHLC require signed `Stock+ Market Data (read-only)` permission | No native price entered SessionZero; public rToken/perp prices are not substitutes. |
| Native U.S. OHLC history | **GATED** | Stock+ `history-candlestick`; unauthenticated quote probe returned `40006` | Technically promising, but access, contract, and license gates remain. |
| Public delayed native data | **UNAVAILABLE** | No documented public delayed stock endpoint; Stock+ documents real-time Level 1 after account opening | Cannot replace an external public/delayed feed. |
| Underlying-linked index/reference input | **AVAILABLE** | Public `AAPLUSDT` perp ticker/index components returned a three-source composite | Supplemental derivative signal only, not an official cash close. |
| Stock futures/contracts | **AVAILABLE** | 321 live UTA futures rows marked RWA or stock | Cross-asset input is possible without authentication. |
| Corporate actions / splits / dividends | **AVAILABLE / PARTIAL** | Public Reality dividends/share changes/suspensions and UTA split records; live AAPL dividends verified | Can supplement risk controls after schema/coverage tests; completeness is unproven. |
| Trading sessions/calendar | **AVAILABLE** with limitations | Public Reality states, calendar, and per-symbol periods | Use for Bitget source availability only; XNYS remains the authoritative cash calendar. |
| Public unauthenticated substrate | **AVAILABLE** partially | Mapping, sessions, calendar, actions, Reality ticker/candles, futures/index all returned `00000` | Useful portions do not require credentials. |
| Authenticated read-only substrate | **GATED** | Stock+ market data and Reality depth/fills | No account, KYC, key, permission, or whitelist was requested. |
| Agent Hub | **AVAILABLE** partially | SDK `3.1.0` exposes generic market/futures actions; searches found no new Reality-reference or Stock+ actions | Direct public REST is currently required for the new reference endpoints. |
| Public-product/non-display rights | **UNVERIFIED / GATED** | Bitget API Key Terms do not expressly grant the required display, redistribution, or derived-product rights | Technical availability does not clear the licensing gate. |

## Outstanding

- Authorized native-equity price/reference data, broader historical capability coverage, backfills, continuous
  collection/scheduling, cross-asset/event providers, models, backtesting, API expansion, and UI.

## Known constraints

- Curated source history includes only one general 24/5 publication and one evidenced RMRNA 24/7
  rollout; unproven symbols/times remain unknown.
- General 24/5 evidence does not enumerate all exceptions. Holidays and generic-symbol weekends
  remain unknown unless symbol-specific evidence establishes availability.
- Exchange calendars encode scheduled sessions, not unscheduled halts or source outages.
- Bitget does not document the observed sparse-window `startTime` backfill behavior or explain why
  individual expected-open intervals have no candle record. The missing records' cause is unknown.
- Full quality reports are emitted by the command but only their summary fields are stored on the
  ingestion run.
- `FAIL` datasets are rejected before the raw/normalized transaction; their machine report is not
  durably stored in this slice.
- No native-equity price adapter, daemon, scheduler, managed database, or deployment exists.
- Massive is the preferred technical candidate only. `RESEARCH_USE` is `GATED`, `PUBLIC_DISPLAY`
  is `UNVERIFIED`, and `REDISTRIBUTION` is `GATED` until the applicable provider/order-form and
  exchange rights are supplied and reviewed.
- Bitget's public mapping, action, and session data do not make its Stock+ native-equity feed public.
  Stock+ is separately authenticated, eligibility/KYC and market-data permissions may apply, and
  reviewed terms do not establish SessionZero's public/non-display rights.
- Reality session payloads currently exhibit contract drift (`EST` versus documented `ET`, and an
  array where `tradingPeriod` is documented as a string). They must remain fail-closed and cannot
  replace the point-in-time XNYS calendar.
- Coverage earliest times are bounded-window observations. A value equal to the evaluation start is
  left-censored evidence of at least that much history, not a provider launch-time assertion.
- A full 1,173-member profile was not run: the pilot implies about 16,305 requests and 3.2 hours at
  observed serial runtime (13.6 minutes is only the pure 20-request/second theoretical floor).

## Current services

- Existing FastAPI and Next.js surfaces are unchanged.
- One-shot CLI: `sessionzero-ingest-bitget-history`.
- Read-only/optional-persistence CLI: `sessionzero-ingest-bitget-reference`.
- Snapshot/manifest CLI: `sessionzero-build-reality-manifest`.
- Coverage-profile CLI: `sessionzero-profile-reality-coverage`.
- Migration CLI: `alembic upgrade head`.

## Required env vars

- `DATABASE_URL`: required for migrations, persistence, and PostgreSQL tests.
- A native-provider API key and an account/license authorizing the intended use are required before
  native-equity implementation or live verification; no variable name is committed until selection.
- Existing public Bitget and web/API settings remain in `.env.example`.

## Test counts

- 73 deterministic non-live/non-PostgreSQL tests.
- 11 direct PostgreSQL integration tests.
- 4 opt-in live Bitget tests.

## Deployment URLs

`NOT DEPLOYED`

## Latest commit

`feat(data): add Reality historical coverage profiling` (local; not pushed).

## Next exact task

Obtain a written Bitget determination covering Stock+ read-only API eligibility and SessionZero's
non-display, derived-output, public-display, and redistribution rights, without opening an account.
Do not spend the estimated full-universe coverage budget until historical source-session evidence
is broadened or the scan is otherwise explicitly justified.

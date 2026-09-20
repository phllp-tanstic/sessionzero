# Handover

## Current phase

`PHASE 2 — RESEARCH BASELINES`

## Historical availability / revision integrity — current

- Acceptance decision: **B. RETROSPECTIVE_POINT_IN_TIME_NOT_VERIFIABLE_PROSPECTIVE_CAPTURE_READY**.
  Official Bitget docs do not establish historical candle revision/version/as-known semantics;
  Alpaca documents late bar updates plus trade corrections/cancellations. Frozen baseline prices
  remain RETROSPECTIVE_ONLY and metrics remain ESTIMATED, not BACKTESTED.
- A 2026-09-20 DEVELOPMENT-only refetch compared three rows per provider. All six were identical;
  changed/missing/new/timestamp/OHLC-change counts were zero. This OBSERVED sample is not an
  immutability proof. [Evidence and architecture](POINT_IN_TIME_INTEGRITY.md).
- `point_in_time_capture.v1` and migration `20260920_10` provide append-only capture runs,
  canonical observation versions, every raw retrieval and deterministic `decision_snapshot.v1`.
  Same observations deduplicate versions; revisions append; PostgreSQL triggers reject mutation.
- One remote-ready iteration: `.venv/bin/sessionzero-capture-decision --decision-timestamp <UTC>`.
  It requires PostgreSQL and Alpaca credentials, runs only inside the pre-decision window, admits
  only evidence ingested by the decision, and captures all 21 names by default. No scheduler or
  deployment exists. Remote images inject `SESSIONZERO_GIT_COMMIT`.
- Decision snapshots include Reality marks, previous native closes, point-in-time source evidence,
  calendar, mapping and capture/dataset identities. Next native open cannot enter the schema and
  remains FUTURE_OUTCOME. PROSPECTIVELY_SAFE describes evidence integrity, not performance.
- **Final OOS remains untouched by performance evaluation.** Existing CLI/library guards are
  unchanged. The capture command rejects historical invocation outside its live pre-decision
  window, including the frozen OOS dates.
- Verification: 194 secret-free non-live/non-PostgreSQL tests and 24 PostgreSQL tests pass; Ruff,
  formatting, migration upgrade/downgrade/restore and diff checks pass. Six authorized read-only
  provider refetches passed. No live prospective snapshot was created because no current decision
  window occurred during this task.
- No Fair Value, Discovery State, threshold optimization, strategy Sharpe, deployment, or push.
  Public derived-output rights remain unverified.
- Next exact task: deploy/schedule only after explicit authorization, then accumulate sufficient
  immutable prospective decisions and append outcome versions under a separately frozen contract.

## Phase 2 Task 1 — accepted research infrastructure

- Frozen protocol and four naive baseline implementations exist. No Fair Value, Discovery State,
  Confidence, Conviction, strategy, frontend or execution work was added.
- **Final OOS remains untouched by performance evaluation.** It begins 2026-08-14 at 20:00 UTC.
  CLI and library reject its evaluation before archive access; v1 has no bypass flag.
- The accepted Phase 1 dataset, cohort, calendar, prices and manifests are unchanged. Research
  verifies exact identities/checksums and reads private archives offline without database writes.
- Development and validation diagnostics cover all 21 symbols, 420 and 462 candidate observations.
  Full results, exclusions, shared-sample metrics and age distributions are generated privately.
  See [protocol](RESEARCH_PROTOCOL.md), [status](BACKTEST.md) and
  [verification receipt](../research/experiments/verification.json).
- Original price availability/revision history remains unverified; ADR-024 resolves this with a
  separate prospective path rather than upgrading the retrospective claims.
  Model-feature eligibility rejects these prices; retrospective comparisons are ESTIMATED, never
  BACKTESTED or final evidence. The accepted baseline infrastructure commit is `b73ac7e`.
- Historical verification at acceptance: 26 new deterministic research tests and 182
  non-live/non-PostgreSQL tests passed.
- New command: `.venv/bin/python -m research.baselines --partition DEVELOPMENT` (or VALIDATION).
  No environment variables or internet required; retained private Phase 1 archives are required.
  Reports and records are mode 0600 under `.local-data/research/experiments/`.
- Outstanding from this frozen slice: historical identity continuity, measured staleness and
  execution assumptions, and separate rights clarification.

The Phase 1 section below remains the accepted historical data-plane record.

## Phase 1 exit dataset — 2026-09-20 (accepted historical record)

- Phase 1 dataset exit gate: **YES**. No Phase 2 model, feature matrix, returns, or backtest exists.
- Dataset version: `e6d06eae4813cacf24f0087e38025e31aff1013a7a9de03a5e1be0266dec7020`.
  Resolve it through tracked `datasets/phase1/latest.json`; do not copy hashes from chat.
- The accepted 21 members and full universe/cohort hashes live in `datasets/phase1/cohort.json`,
  generated from retained evidence and accepted Bitget mapping provenance. Live and offline parser
  verification reproduced the accepted cohort. No old universe snapshot was recreated.
- Fixed window: `[2026-06-15T20:00:00Z, 2026-09-13T20:00:00Z)`; OOS begins August 14 at 20:00 UTC.
  Native targets: all 1,281 evaluation pairs available over 61 XNYS sessions; 42 extra anchor pairs
  cover June 15/September 14 without changing the window. All missing/failure/unknown counts zero.
- Actual Reality data: 39,133 raw and normalized hourly rows, all structural PASS. There remain
  5,620 known-open missing intervals and 1,512 source-unknown intervals. No gaps were filled.
- Actual native data: 2,646 raw pages and normalized boundary minutes, 1,323 target rows. Alpaca:
  2,646 requests, zero retries/429s; Bitget history: 404 requests, zero retries/429s. Source data
  collection took 866.92 seconds after mapping verification, with three globally paced workers.
- All 39,133 Reality rows join to previous-close and next-open target versions; 31,447 decision
  times are outside cash hours. Unresolved joins and unavailable joined prices: zero.
- Next opens are `FUTURE_OUTCOME`; previous closes and Reality observations retain unverified
  historical-availability labels. Decision time is completed Reality bar time, never its start.
- Migration `20260920_09` adds targets/manifests/link tables. The build and a fresh restore database
  independently contain identical counts and dataset identity, with zero SQL lineage violations.
  [Machine verification](../datasets/phase1/verification.json).
- One command after setting `DATABASE_URL`:
  `.venv/bin/python -m sessionzero_database.dataset_cli --restore`.
  It applies migrations, uses tracked identity metadata, and restores private mode-0600 archives
  under `.local-data/phase1/build-20260920/`. It needs no provider credentials or old database.
  Preserve these private archives for exact recovery; do not commit or publicly upload them.
- Tests: 177 non-live tests passed, including 21 PostgreSQL tests; five live tests deselected.
  Ruff format/check, Alembic upgrade/current/check, and diff checks passed.
- Public raw display remains NOT APPROVED; private research/retention remains PROVISIONAL and
  public derived-output rights UNVERIFIED. No push or deployment.
- Full contract, per-symbol counts, limitations, and commands: [PHASE1_DATASET.md](PHASE1_DATASET.md).

The dated sections below describe prior gates and are superseded by this current dataset state
where they say full history or candle-level dataset linkage is missing.

## Alpaca implementation — 2026-09-19 UTC (historical)

- Private/local Alpaca integration is implemented and its bounded runtime gate passed. Public raw
  display remains NOT APPROVED; public derived-output rights UNVERIFIED; private research rights
  PROVISIONAL. ADR-021 supersedes V2's licensing-before-implementation sequence only.
- Built provider-neutral `NativeEquityProvider`, explicit historical SIP/raw adapter, exact XNYS
  boundaries, migration `20260919_08`, append-only raw/normalized persistence, and bounded private
  CLI. [Full contract/results](ALPACA_NATIVE_EQUITY.md). Targets are FIRST_1M_BAR_OPEN /
  LAST_1M_BAR_CLOSE, never asserted auction prices.
- Derived membership from `bitget.2026-06-12.weekend-batch-21`, resolved all 21 tickers through
  live Bitget metadata, and reproduced the exact accepted cohort hash:
  `a69d8c427abac466e8b4088f109e55640bc9e5172011ec6b70919b1874176f32`.
  The owner-supplied original universe reference is
  `e0580746df9d0581bbd629e0a07dde94ce6ff04e973718fb8a1c3a103e81bd06`.
  No replacement universe snapshot was created or relabeled.
- Credentials were sourced from ignored `.env.alpaca.local`; values were not printed or copied.
  Live run began `2026-09-19T20:12:35.798747Z`. AAPL/NVDA/TSLA each returned five 1Min SIP/raw
  bars across three pages. All 21 boundary availability checks and all 25 target rows passed.
- Target symbols: AAOI/AAPL/AMD/AMZN/ASTS. Session dates: June 16, July 9, July 30, August 20,
  September 11. Each includes same-session open/close plus next-session open, including the
  September 11→14 weekend transition. Prices remain only in private reports/database.
- Main run: 126 requests, no retries/throttles, all 126 request IDs present, reported limit 200/min.
  Live AAPL repeat: three new raw pages, zero duplicate normalized versions. Final evidence totals:
  121 runs, 129 raw pages, 119 normalized versions, zero universe snapshots.
- Private ignored artifacts: `native-mapping-verification.json`, `native-equity-verification.json`,
  `native-equity-target-pairs.json`, and `native-equity-repeat-summary.json`, under `artifacts/`.
  Reports containing raw prices are mode 0600. Do not commit or publish them.
- Verified: 136 deterministic tests, 15 PostgreSQL tests, Ruff lint/format, and diff hygiene.
  The new opt-in Alpaca pytest remains skipped; the production CLI performed the full live test.
- Local PostgreSQL cluster: `/tmp/sessionzero-native-test-pg`, loopback port 55439. Separate
  `sessionzero_native_test` and `sessionzero_native_verification` databases; not durable production.
- No full backfill, modeling, returns, BOATS integration, push, public output, or deployment.

Earlier dated sections below remain historical evidence. Claims that no adapter exists or Massive
is preferred are superseded by this section and ADR-021.

## Native target provider selection V2 — 2026-09-18

- Documentation-only review: [full report](NATIVE_EQUITY_PROVIDER_SELECTION_V2.md).
- Decision: **NEEDS_DIRECT_PROVIDER_CONFIRMATION**. The next action is an Alpaca licensing
  clarification for retained historical SIP research and public derived-only hackathon outputs.
  The question is drafted in report section 13; no message was sent and no provider was selected.
- Current Alpaca documentation permits historical SIP on Basic when `end` is at least 15 minutes
  old. Earlier statements equating all Basic history with IEX are superseded; public-product and
  retention rights remain unresolved. Massive now lists minute aggregates on Basic, but its
  individual and business terms still require the appropriate strategy/derived-value license.
- Per the user's current operational report, Bitget MCP is available but degraded to adjusted
  daily native bars, and Stock+ entitlement is unavailable in the account UI. Do not wait on
  another Bitget reply. These task facts were not reverified with runtime calls in this review.
- The accepted 21-member cohort, window, and Reality sufficiency result remain unchanged.
  No exact native cohort coverage, auction boundary extraction, or historical as-known data was
  established. No implementation, migration, dependency, backtest, or Phase 2 work was performed.

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
- Historical source-session provenance now uses `bitget_source_sessions.v2`: eight typed official
  source records, clean batch symbol sets, explicit effective/publication/retrieval times, stable
  precedence, visible conflicts, and assessment-level evidence IDs/URLs.
- Coverage classification semantics are now `reality_historical_coverage.v2`; present-day metadata
  and ambiguous notices cannot rewrite historical source availability.

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

- Stock+ authenticated read-only verification on `2026-09-15` could not start because no complete
  `BITGET_API_KEY`/`BITGET_SECRET_KEY`/`BITGET_PASSPHRASE` set was present in the environment.
  Unauthenticated static and history controls both returned `40006 Invalid ACCESS_KEY`. Account
  entitlement, native rows, June coverage, adjustment behavior, and session reconstruction remain
  unverified. Bitget's direct hackathon-use authorization clears only the hackathon-use question.

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
- The exact pilot was rerun on 2026-09-14 after the source-evidence expansion. Status counts stayed
  at three source-session-unknown and seven quality failures with zero sufficiency passes. Across
  the ten members, unknown absences fell `6,004 -> 5,243` while known-open missing intervals rose
  `2,302 -> 3,063`; this is a classification improvement, not a data-quality improvement. The v2
  profile identity is `0e5657bf...a5a3fb4` and again used 139 requests without retries/rate limits.
  The exact accepted pairs came from the retained prior profile because its temporary snapshot
  database no longer existed; no fresh snapshot was mislabeled with the accepted version.
- Of 1,173 universe symbols, 21 (1.79%) have full-window dated symbol-level schedule evidence, 76
  more have partial-window evidence, and 1,076 have none. The full-universe scan was not run.
- Migration `20260913_05` and all 11 PostgreSQL integration tests passed against an isolated local
  PostgreSQL instance. The 80 non-live/non-PostgreSQL tests also passed.

### Evidence-qualified 21-symbol audit — 2026-09-14

- Cohort `a69d8c42...4176f32` was derived from the persisted 1,173-member universe
  `e0580746...81bd06` and `bitget_source_sessions.v2`; no production symbol list was used.
- The immutable `1H` window was `[2026-06-15T20:00:00Z, 2026-09-13T20:00:00Z)`. All 21
  machine-qualified members were evaluated in 404 requests with zero retries and zero rate-limit
  responses.
- Every member had 72 holiday-qualified unknown hourly boundaries: local dates Juneteenth,
  Independence Day observed, and Labor Day. Total unknown/holiday-ambiguous intervals were 1,512.
- Aggregate known-open evidence was 43,848 intervals: 38,228 observed and 5,620 missing. The exact
  aggregate ratios were 0.871829958 observed/known-open, 0.128170042 missing/known-open, and
  0.033333333 unknown/full-grid.
- Coverage status counts were 19 `SOURCE_SESSION_TOO_UNKNOWN`, two `DATA_QUALITY_FAILURE`, and zero
  in every other status. AVGO had five and META nine provider rows before the fixed left boundary,
  triggering the existing boundary-spillover quality failure. All 21 bounded histories were
  left-censored; duration median/max was 90 days and minimum was 88.166667 days.
- The profile is persisted under `reality_historical_coverage.v3`. Universe-to-evidence and
  evidence-to-quality/coverage lineage is durable. Request envelopes and raw/normalized candle rows
  remain in-memory in this read-only profiler and are not durably joined to the profile; do not
  claim complete candle-level audit lineage.

### Coverage semantics correction — 2026-09-14

- `reality_historical_coverage.v4` supersedes the v3 classification without rewriting its
  persisted profile. It independently records structural validity, availability completeness,
  60-day duration sufficiency, and deterministic final-30-day OOS feasibility.
- The exact same 21 members and immutable `1H` window were rerun. All 21 are structural `PASS`,
  meet the duration requirement, have actual observations before and within the final OOS segment,
  and are `SUFFICIENT_MINIMUM_HISTORY` under the corrected data-plane definition.
- The deterministic OOS boundary is `2026-08-14T20:00:00Z`. This is only a feasibility boundary;
  no split optimization, returns, alpha statistic, or strategy evaluation was performed.
- Availability warnings are unchanged: 43,848 known-open intervals, 38,228 observed while known
  open, 5,620 missing while known open, and 1,512 holiday-qualified unknown intervals. No density
  threshold was introduced.
- AVGO's five and META's nine pre-start provider rows are clipped and retained as boundary-
  spillover warning telemetry. Neither has another structural defect. Post-end leakage remains a
  structural failure.
- Duration sufficiency is not future research eligibility. The native-equity leg remains gated,
  availability completeness remains a future selection input, and candle-level profile lineage is
  still incomplete.

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

- Wider native-equity historical coverage, rights clarification, continuous collection,
  cross-asset/event providers, models, backtesting, API expansion, and UI.

## Known constraints

- Curated source history includes official June 12, June 23, July 3, July 17, and August 14
  publications. The explicit dated union covers 97 symbols for some part of the pilot window, but
  only 21 at schedule level for the full window; unproven symbols/times remain unknown.
- General 24/5 evidence does not enumerate all exceptions. Holidays and generic-symbol weekends
  remain unknown unless symbol-specific evidence establishes availability.
- Exchange calendars encode scheduled sessions, not unscheduled halts or source outages.
- Bitget does not document the observed sparse-window `startTime` backfill behavior or explain why
  individual expected-open intervals have no candle record. The missing records' cause is unknown.
- Full quality reports are emitted by the command but only their summary fields are stored on the
  ingestion run.
- `FAIL` datasets are rejected before the raw/normalized transaction; their machine report is not
  durably stored in this slice.
- The accepted cohort now has a full boundary-target dataset. No daemon, scheduler, managed database, or
  deployment exists. Alpaca private use is provisional; public raw display is not approved and
  public derived-output rights are unverified.
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
- Evidence-qualified audit CLI: `sessionzero-audit-evidence-coverage`.
- Private native CLI: `sessionzero-verify-native-equity` (or the documented Python module).
- Dataset build/restore CLI: `sessionzero-build-phase1-dataset` (or Python module above).
- Prospective decision capture CLI: `sessionzero-capture-decision`.
- Migration CLI: `alembic upgrade head`.

## Required env vars

- `DATABASE_URL`: required for migrations, persistence, and PostgreSQL tests.
- `NATIVE_EQUITY_PROVIDER=alpaca`, `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`: required for native
  verification. Source the local ignored environment file without displaying it.
- `SESSIONZERO_GIT_COMMIT`: required for prospective capture in remote images without `.git`;
  local capture instead verifies a clean tree and resolves `HEAD`.
- `BITGET_API_KEY`, `BITGET_SECRET_KEY`, and `BITGET_PASSPHRASE`: required together for the isolated
  Stock+ read-only verifier; values must never be committed or printed.
- Existing public Bitget and web/API settings remain in `.env.example`.

## Current test counts

- 193 deterministic non-live/non-PostgreSQL tests.
- 24 PostgreSQL integration/migration tests.
- Five opt-in live provider tests remain separate.

## Phase 1 test counts (historical)

- 156 deterministic non-live/non-PostgreSQL tests.
- 21 PostgreSQL integration/migration tests.
- 4 existing opt-in Bitget tests and 1 new opt-in Alpaca test.

## Deployment URLs

`NOT DEPLOYED`

## Phase 1 acceptance commit (unchanged)

`feat(data): build reproducible Phase 1 target dataset` is the acceptance commit for this handover;
resolve its hash with `git log -1`. Build base: `5cfd574`; exact source hashes are in the dataset
manifest, avoiding a self-referential commit hash. Nothing is pushed in this task.

The current integrity implementation is committed separately as
`feat(research): add point-in-time capture integrity`; resolve its hash with `git log -1` after
acceptance. It is not pushed.

## Previous next task (superseded by current section)

Define the Phase 2 baseline research protocol and explicit point-in-time availability/eligibility
policy against the frozen dataset, preserving the final OOS boundary and all missingness. Resolve
Alpaca research/retention/public-derived rights separately. Do not begin modeling, feature
engineering, returns, public output, push, or deployment without the next task's authorization.

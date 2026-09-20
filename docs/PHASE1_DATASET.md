# Phase 1 dataset build and recovery report

Verified: 2026-09-20 UTC. Phase 1 technical dataset exit: **YES**. No Phase 2 modeling began.

## Fixed identity

| Identity | Value |
|---|---|
| Dataset | `e6d06eae4813cacf24f0087e38025e31aff1013a7a9de03a5e1be0266dec7020` |
| Universe historical reference | `e0580746df9d0581bbd629e0a07dde94ce6ff04e973718fb8a1c3a103e81bd06` |
| Accepted cohort | `a69d8c427abac466e8b4088f109e55640bc9e5172011ec6b70919b1874176f32` |
| Reality content | `b2b78c06ed39583e22e4f486ae836be1ef693e522ee6ac8e12280772fba0b9aa` |
| Native target content | `f41e4d01de8cfbffda55a7642bb5b1b2b7456792b3748b09bbc312250d5a0421` |
| Calendar | `631de3a894ae0cc9d960be8af9051b9433c5fdbed35438b5ddcc816e9145bb57` |
| Source code | `b0045e5b70cf4dfd80d47136617c72dfd052bd9a66a341b5f030ce834628aaa1` |
| Source evidence | `bitget_source_sessions.v2` (full content hash also retained) |
| Transformation | `phase1_dataset.v1` |
| Target definition | `cash_boundary_minute.v1` |
| Calendar provider | XNYS / exchange-calendars 4.13.2 |

[Latest pointer](../datasets/phase1/latest.json), [versioned manifest](../datasets/phase1/e6d06eae4813cacf24f0087e38025e31aff1013a7a9de03a5e1be0266dec7020.json),
[cohort artifact](../datasets/phase1/cohort.json), [calendar artifact](../datasets/phase1/calendar.json),
and [independent SQL/restore verification](../datasets/phase1/verification.json) are tracked metadata.
Membership was generated from accepted historical evidence and retained Bitget mappings, then
reverified through live `stock-info` and replayed through the same `BitgetReferenceDataProvider`.
The original full universe snapshot is not claimed to have been recovered; its version remains a
historical identity reference. No handwritten production universe or ticker-string slicing exists.

The build base commit is `5cfd574d8501a8ac307890bf3eef434d7f8597be`. A manifest cannot include the hash of the later commit
that contains itself. Its `source_file_hashes` and `source_code_version` therefore bind the exact
implementation, while the acceptance commit retains that implementation and this manifest.
Generation/retrieval timestamps, request counters, database IDs, and local paths are outside
logical dataset identity. Exact target content, mappings, calendar, evidence, definitions, code,
and outcome roles are inside it. Re-fetching revised provider history can produce a new version.

## Rebuild and exact restore

Run from the repository root after installing the locked Python dependencies. Export a PostgreSQL
`DATABASE_URL` naming the intended database. The command applies Alembic migrations itself.

```bash
# Exact accepted version: no market-data credentials or network calls to providers.
.venv/bin/python -m sessionzero_database.dataset_cli --restore

# New live retrieval: ALPACA_API_KEY and ALPACA_SECRET_KEY must already be exported.
.venv/bin/python -m sessionzero_database.dataset_cli
```

The installed console-script equivalent is `sessionzero-build-phase1-dataset`. Use `--manifest`
for a particular retained manifest; the default resolves `latest.json`. Use `--archive-dir` to
locate a private archive directory or resume a collection from completed symbol archives.

Exact restore requires `.local-data/phase1/build-20260920/`, retained privately in the workspace,
with every file matching the manifest's SHA-256 index. Copy these licensed private files through
an authorized private backup process when moving machines. Git intentionally contains no raw
price archive. Restore fails on missing/corrupt archives, mapping/cohort mismatch, calendar changes,
source-code mismatch, or changed dataset identity. Use the acceptance checkout for exact code.
An empty database and these durable artifacts are sufficient; the previous temporary cluster,
chat history, and manual hash arguments are unnecessary. Without archives, a live rebuild requires
provider access and does not promise unchanged historical provider values.

## Architecture and persistence

The collector uses the existing Bitget bounded 1H history path and the Alpaca SIP/raw 1Min adapter.
Private JSON archives contain raw pages/rows and validated normalized observations with actual
retrieval timestamps. Native restoration replays the raw pages through the same parser, proving
that serialized normalized observations match raw evidence. Alpaca's inclusive end-minute response
is clipped by the existing half-open adapter; it is never substituted for a missing exact boundary.

Migration `20260920_09` adds four tables:

- `native_session_targets`: immutable content-addressed pairs, prices/timestamps, status, calendar,
  provider, feed/adjustment, definitions, raw-page/normalized-minute and ingestion-run foreign keys.
- `phase1_dataset_manifests`: durable logical identity and non-price report metadata.
- `phase1_dataset_targets`: unique dataset / Reality symbol / session-date membership and anchor role.
- `phase1_dataset_reality`: existing raw/normalized Reality references and exact previous-close /
  next-open target foreign keys, calendar version, completed-bar decision time, and outcome labels.

No raw candle storage table is duplicated. Repeated targets retain their original lineage;
revised native content appends a new target and minute version. Repeated manifests and dataset
links deduplicate. Reality raw ingestion is per-run; normalized Reality rows keep the existing
first-write policy. If an existing canonical Reality candle disagrees with incoming values, the
build stops with `REALITY_CANONICAL_REVISION_CONFLICT` rather than relabeling or overwriting it.
Use a fresh database for an isolated revised dataset until a Reality correction policy is approved.

Both the build and empty-database restore independently contain:

| Table / object | Count |
|---|---:|
| Ingestion runs | 2,667 |
| Raw Reality observations | 39,133 |
| Normalized Reality candles | 39,133 |
| Raw native pages | 2,646 |
| Normalized native boundary minutes | 2,646 |
| Native session target pairs | 1,323 |
| Dataset manifests | 1 |
| Dataset target links | 1,323 |
| Dataset Reality links | 39,133 |
| Replacement universe snapshots | 0 |

## Window, targets, and missingness

Evaluation is exactly `[2026-06-15T20:00:00Z, 2026-09-13T20:00:00Z)`: 90 calendar days.
The deterministic final 30-day OOS interval begins `2026-08-14T20:00:00Z`. All 21 Reality series
span at least 88.166667 observed days and contain observations before and inside that final segment.
This is chronology feasibility, not model eligibility or a claim of complete data density.

There are **61 intersecting XNYS regular sessions**, June 16 through September 11. The June 15
session closes exactly at the excluded left-side cash-session intersection, while September 14
opens after the evaluation window. Both are explicit **BOUNDARY_ANCHOR** sessions used for previous
close/next open joins; their 42 pairs are reported separately and do not move the window.

`FIRST_1M_BAR_OPEN` uses the minute beginning at scheduled regular open.
`LAST_1M_BAR_CLOSE` uses the minute beginning one minute before scheduled regular close.
These are **not official auction prices**. `feed=sip`, `adjustment=raw`, `timeframe=1Min`, and
`asof=-` are explicit. No IEX fallback, adjustment, nearest-minute lookup, or imputation exists.

| Pair status | Evaluation pairs | Anchor pairs |
|---|---:|---:|
| TARGET_AVAILABLE | 1,281 | 42 |
| OPEN_MISSING | 0 | 0 |
| CLOSE_MISSING | 0 | 0 |
| BOTH_MISSING | 0 | 0 |
| PROVIDER_FAILURE | 0 | 0 |
| STRUCTURAL_FAILURE | 0 | 0 |
| UNKNOWN | 0 | 0 |

Both leg statuses and static error codes remain separate in provenance. Failure status takes
precedence over missingness for the pair without discarding an available opposite leg. Empty
successful responses retain raw provenance with no fabricated normalized minute.

| Reality symbol | Native ticker | Sessions expected | Pairs available | Open missing | Close missing | Coverage | Reality rows |
|---|---|---:|---:|---:|---:|---:|---:|
| RAAOIUSDT | AAOI | 61 | 61 | 0 | 0 | 100.00% | 1,765 |
| RAAPLUSDT | AAPL | 61 | 61 | 0 | 0 | 100.00% | 1,918 |
| RAMDUSDT | AMD | 61 | 61 | 0 | 0 | 100.00% | 1,761 |
| RAMZNUSDT | AMZN | 61 | 61 | 0 | 0 | 100.00% | 1,703 |
| RASTSUSDT | ASTS | 61 | 61 | 0 | 0 | 100.00% | 1,619 |
| RAVGOUSDT | AVGO | 61 | 61 | 0 | 0 | 100.00% | 1,777 |
| RDRAMUSDT | DRAM | 61 | 61 | 0 | 0 | 100.00% | 1,915 |
| RGOOGLUSDT | GOOGL | 61 | 61 | 0 | 0 | 100.00% | 1,953 |
| RINTCUSDT | INTC | 61 | 61 | 0 | 0 | 100.00% | 1,928 |
| RLITEUSDT | LITE | 61 | 61 | 0 | 0 | 100.00% | 1,748 |
| RMETAUSDT | META | 61 | 61 | 0 | 0 | 100.00% | 1,791 |
| RMRVLUSDT | MRVL | 61 | 61 | 0 | 0 | 100.00% | 1,866 |
| RMSFTUSDT | MSFT | 61 | 61 | 0 | 0 | 100.00% | 1,805 |
| RMUUSDT | MU | 61 | 61 | 0 | 0 | 100.00% | 2,045 |
| RNOKUSDT | NOK | 61 | 61 | 0 | 0 | 100.00% | 1,628 |
| RNVDAUSDT | NVDA | 61 | 61 | 0 | 0 | 100.00% | 2,129 |
| RRKLBUSDT | RKLB | 61 | 61 | 0 | 0 | 100.00% | 1,770 |
| RSNDKUSDT | SNDK | 61 | 61 | 0 | 0 | 100.00% | 2,004 |
| RSOXLUSDT | SOXL | 61 | 61 | 0 | 0 | 100.00% | 1,824 |
| RSPCXUSDT | SPCX | 61 | 61 | 0 | 0 | 100.00% | 2,147 |
| RTSLAUSDT | TSLA | 61 | 61 | 0 | 0 | 100.00% | 2,037 |

Reality completeness remains independently explicit: 43,848 known-open intervals comprise
38,228 observed and 5,620 missing intervals. There are 1,512 holiday-qualified source-unknown
intervals, including 905 observed candles and 607 absences. The total retained Reality count is
39,133. No missing observations were synthesized, and no weak member was dropped.

## Request budget and runtime

Alpaca: **2,646 requests**, **0 retries**, **0 HTTP 429 responses**, and **0 provider errors**.
Three workers share a gate with a minimum 0.32-second spacing for every request, including retries:
at most 188 starts in any 60-second span, below the Basic 200/minute limit. Safe request IDs and
response headers are retained in private raw provenance. Source collection elapsed **866.92 s**
(14 min 26.92 s), measured after mapping verification and including concurrent Reality retrieval.
Bitget history: **404 requests**, **0 retries**, **0 rate-limit responses**, all structural PASS.
Live mapping verification retained 42 public metadata responses, separately from the 404 history
requests. One initial sandbox-denied network attempt preceded the successful collection.
[Alpaca's documented Basic limits](https://docs.alpaca.markets/us/docs/about-market-data-api).

## Join and point-in-time verification

All **39,133** actual Reality candles join through the accepted native ticker and pinned calendar
to previous-close and next-open target versions. **31,447** completed-bar decision timestamps are
outside cash hours. Unresolved joins, unavailable previous closes, and unavailable next opens are
all **zero**. Independent SQL checks of both databases found zero symbol/calendar/time-order or
price-to-normalized-minute lineage violations.

Machine-readable policy is retained in the manifest and on dataset links:

| Field | Role |
|---|---|
| Next cash open | `FUTURE_OUTCOME` |
| Previous cash close | `CONTEXT_AVAILABILITY_UNVERIFIED` |
| Reality candle | `OBSERVED_HISTORY_NOT_AS_KNOWN` |
| Decision timestamp | Reality bar start plus 1H |

Native raw prices are event-time observations, with separate actual retrieval timestamps.
Corporate-action restatement is not applied. Historical original availability and provider
revision timing remain unverified. The next open is strictly after the decision; the previous
close is at or before it. An hourly candle's final close is never treated as known at bar start.
This archive is not a feature matrix; later contemporaneous-input use requires an explicit
availability policy. No returns, Fair Value, predictive features, or backtests were calculated.

## Validation and exit decision

- 177 non-live tests passed, including all 21 PostgreSQL integration/migration tests; five optional
  live tests were deselected. One existing dependency deprecation warning remains.
- Ruff format/check passed; Alembic upgrade/current/check passed at `20260920_09` with no schema
  drift; `git diff --check` passed.
- Tests cover target idempotency/corrections/uniqueness, each missing leg, both missing, provider
  failure, unknown/structural states, identity/calendar linkage, future-outcome labels, exact
  boundaries, raw adjustment, no IEX fallback, raw-page replay, rate pacing, and safe CLI errors.
- A fresh empty database restored the same dataset version from private archives with no provider
  credentials or provider requests. Actual table counts and SQL lineage checks match the build.

**YES:** one command can reproducibly construct the accepted Phase 1 historical dataset from
its retained private evidence. This gate closes the historical dataset's technical linkage and
recovery requirements. It does not authorize Phase 2 work or claim public-product licensing,
historical as-known features, immutable provider history, unscheduled-halt coverage, or managed
production infrastructure. Public Alpaca raw display remains unapproved; private research and
retention remain provisional. The next task should define the baseline research protocol and
point-in-time eligibility policy without altering this cohort, window, or final OOS boundary.

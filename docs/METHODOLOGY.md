# Methodology

## Remote prospective claim boundary

An automatic worker run is `PROSPECTIVE OBSERVED` only when its full 21-member decision capture
finishes within the accepted XNYS calendar-derived window and its snapshot contains only
pre-decision features. The later native first-minute open is an append-only FUTURE_OUTCOME label,
not a decision feature. Failed, partial, missed, or database-unavailable runs are operational
evidence, not validated observations. Prospective accumulation alone does not grant a BACKTESTED
performance claim. [Worker contract](DEPLOYMENT.md).

## Revision-integrity decision — current

Official provider evidence and bounded refetches do not establish an as-known historical price
database. The accepted classification is
`RETROSPECTIVE_POINT_IN_TIME_NOT_VERIFIABLE_PROSPECTIVE_CAPTURE_READY`. See the
[integrity report](POINT_IN_TIME_INTEGRITY.md). Phase 1 and existing baseline results remain
**RETROSPECTIVE ESTIMATED**; they are not BACKTESTED. Six unchanged refetches are **OBSERVED** and
do not prove immutability.

`point_in_time_capture.v1` can create **PROSPECTIVE OBSERVED** evidence. It runs only immediately
before a declared decision, records provider responses before that decision, retains corrections
as new versions and freezes `decision_snapshot.v1`. A prospective snapshot contains Reality marks,
previous native closes, source-session evidence, calendar/mapping/dataset/capture versions, and no
future outcome. `PROSPECTIVELY_SAFE` describes the evidence record, not predictive performance.

**BACKTESTED** is reserved for a separately frozen evaluation over a sufficient prospective
history plus later outcome versions. No current result meets that definition. `FIRST_1M_BAR_OPEN`
remains outcome-only: revision risk affects label stability, while revision risk in Reality marks
or previous closes affects feature point-in-time integrity.

## Phase 2 baseline protocol — current

The [frozen research protocol](RESEARCH_PROTOCOL.md) and machine-readable
[baseline-v1 contract](../research/protocols/baseline-v1.json) govern current work. The accepted
Phase 1 archive is unchanged. Fixed 30/30/30-day chronological splits, one decision 60 minutes
before each cash open, raw reopen return, and four deterministic naive baselines are implemented.
Final OOS remains untouched. No tunable weights, strategy or Fair Value model exists.

Historical native close and Reality price availability remain UNKNOWN, so the model-feature gate
rejects them. Separate retrospective diagnostics are explicitly ESTIMATED, not BACKTESTED. Next
native open remains FUTURE_OUTCOME. Corporate actions with unknown publication availability are
excluded. The strict leak-free benchmark acceptance gate remains unmet pending as-known evidence;
no assumption or retrieval timestamp silently clears it. See [backtest status](BACKTEST.md).

The Phase 1 descriptions below are retained historical context, superseded only where they say
no baseline research exists.

## Phase 1 dataset point-in-time policy — accepted archive

The full fixed-window dataset is an event-time observation/outcome archive. Native prices remain
unadjusted; no corporate-action restatement is applied. Actual retrieval timestamps are retained
separately and are never replaced with historical event times. Original historical availability,
original publication latency, and historically immutable provider values are not claimed.

For each Reality 1H candle, the join decision timestamp is its start plus one hour: the completed
candle's close cannot be known at its start. The calendar supplies the most recent cash close
at or before that decision and the next cash open strictly after it. Database rows and manifests
label next open `FUTURE_OUTCOME`, previous close `CONTEXT_AVAILABILITY_UNVERIFIED`, and the Reality
observation `OBSERVED_HISTORY_NOT_AS_KNOWN`. These rows must not become contemporaneous features
without a separately approved availability policy. No future-open target enters a feature frame.

The evaluation window is unchanged. June 15 and September 14 are explicitly separate boundary
anchors; they support joins at the edges and do not expand the evaluation or OOS window. The final
30-day OOS interval begins `2026-08-14T20:00:00Z`. Availability inspection is a data-plane check,
not model fitting or holdout-performance evaluation. Native missingness and Reality source-session
unknowns remain explicit, with no imputation, density-based cohort changes, or strategy returns.
See [the dataset contract](PHASE1_DATASET.md).

## Native minute-boundary observations — current Phase 1 contract

The current task permits the explicit observable definitions `FIRST_1M_BAR_OPEN` and
`LAST_1M_BAR_CLOSE`. The existing XNYS calendar supplies the scheduled open and close; only the
exact first or final regular minute qualifies. Missing boundary minutes remain missing. These
prices are not official auction prints or every-condition first/last SIP trades. Alpaca's separate
auction endpoint exists but its runtime semantics have not been verified here. This supersedes
older statements below that no adapter exists, without authorizing models or returns.

[Full target and point-in-time contract](ALPACA_NATIVE_EQUITY.md): preserve unadjusted values and
all observed content versions; retrieval is not original historical availability. No corrected
close may silently become a prediction-time feature. Native target construction is private data
verification only; bounded runtime acceptance passed, with no auction-price equivalence claim.

Corporate-action evidence is supplemental. Event, announcement, effective, publication, and
ingestion times are distinct. Records with `availability_time_status=UNKNOWN` must not be
retroactively introduced into point-in-time research. This layer records splits but does not
adjust OHLC, derive features, or reinterpret prior candle-quality results.

## Current phase

Phase 1 currently establishes trustworthy inputs only. Reality instruments are selected by the
provider's `isReality=yes` metadata. Market values are parsed as decimal strings, timestamps become
timezone-aware UTC datetimes, and missing values remain missing.

Bounded candle history uses explicit `[start, end)` semantics and deterministic ascending output.
The quality gate compares observations with regular interval boundaries, then uses point-in-time
source-session evidence to classify each absence. A known source closure is not a gap; a missing
interval while the source was expected open is explicit availability incompleteness; and
insufficient historical evidence stays unknown. Missingness alone is not structural corruption or
proof of an outage. None of these states creates a synthetic candle.

The XNYS cash calendar and Bitget source availability are independent inputs. Cash-market closure
alone does not make Session Zero active: at least one qualifying source must be known available.
Present-day trading capabilities are never projected backward. These are deterministic temporal
primitives, not Discovery State, Fair Value, Confidence, Gap, or a trading signal.

Historical resolution uses only official Bitget evidence whose symbol scope and effective range
cover the timestamp. When an announcement says support is available “now” without a distinct
effective time, its displayed publication time is used as a conservative lower bound. A dated
addition proves the post-boundary capability but does not prove any pre-boundary mode or closure.
Explicit addition batches outrank contemporaneous status enumerations, which outrank general
rules; symbol-scoped suspensions outrank schedules. Contradictory equal-precedence outcomes,
unscoped notices, holidays qualified with “may”, and unsupported periods remain `UNKNOWN`.

Current Bitget `weekendTradable` and session payloads are current observations, not historical
facts. They may corroborate present behavior but do not participate in historical resolution.
Missing candles likewise never serve as evidence of a source opening or closure.

No predictive hypothesis is tested and no performance metric is reported in this phase.

Historical coverage uses a predeclared 60-day minimum total period and preserves the locked
30-day final OOS requirement. For interval candles, observed duration is the inclusive chronology
from the earliest observation through the end of the latest observation. The deterministic OOS
boundary is `evaluation_end - 30 days`; feasibility requires actual observations both before that
boundary and inside the final window. The split is not optimized.

Coverage v4 evaluates structural validity, availability completeness, duration sufficiency, and
OOS feasibility independently. Empty/provider-failed history is `HISTORY_UNAVAILABLE`; objective
structural errors are `DATA_QUALITY_FAILURE`; and a duration or OOS failure is
`INSUFFICIENT_HISTORY`. Otherwise `SUFFICIENT_MINIMUM_HISTORY` means only that Reality-side data
could support the locked chronological split. Known-open missingness and session unknowns remain
warnings and metrics but do not automatically override that result. No density threshold, outcome,
or market-performance statistic tunes these rules, and no duration pass makes a symbol part of a
future research universe.

Reality universe eligibility is objective and fixed before any future experiment: provider Reality
identity, online status, explicit native mapping, supported interval, and observed ingestion quality.
The bounded verification subset is the first N eligible symbols after canonical sorting. Failures
remain in the manifest and the subset is never changed to improve its appearance. Future research
must reference `universe_version`, `manifest_version`, `transformation_version`, and `git_commit`;
the accepted Phase 1 dataset now supplies durable candle/target linkage through `dataset_version`.
This still does not establish historical as-known feature availability or research eligibility.

The earlier 2026-09-13 native provider gate was superseded for private implementation by ADR-021.
Live native minute-boundary observations now exist with Bitget mapping lineage. They are neither
split-adjusted series nor a historical as-known feature dataset. No future open has entered any
feature dataset. Public licensing remains unresolved independently of technical verification.

## Locked future methodology

The eventual target is the next regular-session opening return. Work must begin with interpretable
baselines, use point-in-time features, walk-forward validation, and a final untouched out-of-sample
holdout. Any future backtest must include realistic fees, spreads, slippage, capital accounting,
turnover, and impossible-fill protection. Final OOS data cannot be used for tuning.

Every future claim must be labeled `OBSERVED`, `BACKTESTED`, `ESTIMATED`, `TARGET`, or
`HYPOTHESIS`. The current data-plane work makes only observed provider and data-integrity claims.

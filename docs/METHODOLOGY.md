# Methodology

## Phase 1 dataset point-in-time policy — current

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

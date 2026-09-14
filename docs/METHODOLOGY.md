# Methodology

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
interval while the source was expected open remains a defect; and insufficient historical evidence
stays unknown. None of these states creates a synthetic candle.

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
30-day final OOS requirement. For interval candles, observed duration is the inclusive covered
interval from the earliest observation through the end of the latest observation. Passing means
only that Reality-side market data could support those future validation windows. It does not make
a symbol strategy-eligible, select it for research, or establish predictive value.

Coverage classification is conservative. Empty/provider-failed history is `HISTORY_UNAVAILABLE`;
existing quality errors are `DATA_QUALITY_FAILURE`; less than 60 observed days is
`INSUFFICIENT_HISTORY`; sufficient duration with absent intervals whose source session cannot be
established is `SOURCE_SESSION_TOO_UNKNOWN`; and known-open missing intervals prevent a pass and
remain `UNKNOWN`. Only a non-failing series with at least 60 days and neither kind of unresolved
absence is `SUFFICIENT_MINIMUM_HISTORY`. No outcomes or market performance tune these rules.

Reality universe eligibility is objective and fixed before any future experiment: provider Reality
identity, online status, explicit native mapping, supported interval, and observed ingestion quality.
The bounded verification subset is the first N eligible symbols after canonical sorting. Failures
remain in the manifest and the subset is never changed to improve its appearance. Future research
must reference `universe_version`, `manifest_version`, `transformation_version`, and `git_commit`;
these Reality-side identities do not imply a complete dataset while native-equity observations are
gated.

The 2026-09-13 native-equity provider gate did not authorize a reference dataset. Provider
documentation, free plans, or test fixtures cannot substitute for credentials and rights covering
non-display quantitative use. Consequently no native close/open target, split-adjusted series,
provider-integrated symbol mapping, or overlapping historical slice exists, and no future U.S.
open has entered a feature dataset. The separately verified public Bitget Reality-to-ticker
mapping is reference metadata only and has not entered a model or provider adapter.

## Locked future methodology

The eventual target is the next regular-session opening return. Work must begin with interpretable
baselines, use point-in-time features, walk-forward validation, and a final untouched out-of-sample
holdout. Any future backtest must include realistic fees, spreads, slippage, capital accounting,
turnover, and impossible-fill protection. Final OOS data cannot be used for tuning.

Every future claim must be labeled `OBSERVED`, `BACKTESTED`, `ESTIMATED`, `TARGET`, or
`HYPOTHESIS`. The current data-plane work makes only observed provider and data-integrity claims.

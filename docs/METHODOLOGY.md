# Methodology

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

No predictive hypothesis is tested and no performance metric is reported in this phase.

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

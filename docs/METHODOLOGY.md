# Methodology

## Current phase

Phase 0 establishes trustworthy inputs only. Reality instruments are selected by the provider's
`isReality=yes` metadata. Market values are parsed as decimal strings, timestamps become
timezone-aware UTC datetimes, and missing values remain missing.

No predictive hypothesis is tested and no performance metric is reported in this phase.

## Locked future methodology

The eventual target is the next regular-session opening return. Work must begin with interpretable
baselines, use point-in-time features, walk-forward validation, and a final untouched out-of-sample
holdout. Any future backtest must include realistic fees, spreads, slippage, capital accounting,
turnover, and impossible-fill protection. Final OOS data cannot be used for tuning.

Every future claim must be labeled `OBSERVED`, `BACKTESTED`, `ESTIMATED`, `TARGET`, or
`HYPOTHESIS`. Phase 0 makes only observed provider-access claims.


# Fair Value V1 research — RETROSPECTIVE ESTIMATED

Decision: **FAIR_VALUE_V1_NOT_YET_JUSTIFIED**. The development-only procedure selected a
two-parameter robust displacement model, but validation does not consistently outperform the
strongest Reality baseline. No model is promoted to a production Fair Value engine. This is a
private retrospective research diagnostic, not a point-in-time certified backtest or signal.

## Identity and reproduction

The frozen `baseline_protocol.v1`, `chronological_30_30_30.v1`,
`raw_reopen_return.v1`, 21-symbol accepted Phase 1 dataset version
`e6d06eae4813cacf24f0087e38025e31aff1013a7a9de03a5e1be0266dec7020`, and
`FIRST_1M_BAR_OPEN / previous LAST_1M_BAR_CLOSE - 1` are unchanged. The first-minute
open is not described as an official auction print. Decision time is XNYS scheduled open minus
60 minutes. Development is June 15 20:00–July 15 20:00 UTC; validation is July 15 20:00–August
14 20:00 UTC. The final interval, August 14 20:00–September 13 20:00 UTC, is unsupported by
this command and has not been scored.

From the repository root with retained checksum-verified private archives, run:

```bash
.venv/bin/python -m research.fair_value
```

No network, database, credentials or provider call is needed. The command has no OOS flag.
It writes append-only mode-0600 `fair-value-result.json` and
`fair-value-predictions.json` under `.local-data/research/experiments/<experiment_id>/`.
The pre-commit validation receipt is `699a2ebf9b9cd2768923a6176b76bded1ede4b0ad72e9ee6f7e006c307e8bf4a`.
Experiment identity deliberately includes the Git base commit and exact source hashes, so a run
from the acceptance commit has a new deterministic ID with the same research inputs and results.
Revisions produce another identity. Full per-symbol metrics, ten worst errors, quantiles,
development/validation ablations and sample comparisons are generated, not handwritten.

## Feature architecture and eligibility

The report contains the machine-readable feature specification (formula, source, event-time,
eligibility, missingness, normalization, version). These are event-time *proxies*: the historical
Reality and native prices have `UNKNOWN_AVAILABILITY` in the frozen protocol and cannot enter
the certified model-feature lane. The runner explicitly checks this classification, sets
`model_eligible_observations=0`, and never calls these archived prices prospectively safe.
This diagnostic assumption is unchanged from the naive baselines: archived revisions stand in
for contemporaneous values, without proof that they were known then.

At decision T, C is the previous exact native final-minute close, A the Reality candle completing
exactly at that close, M the latest completed Reality candle strictly before T. Source evidence
must certify the entire off-session path as expected open and timely published. Every path
candle must complete before T. No candle or previous-close value is synthesized. Without exact A,
C, a Reality mark or a known source path, the row is excluded; optional earlier native fields are
development-mean imputed for the appropriate ablations, with a missing flag in FULL. No symbol is
removed from the cohort. Missing intermediate Reality hours are counted, not filled.

| Group | Added features and formulas | Inputs |
|---|---|---|
| Displacement | `M/A-1` | Exact A, latest M |
| Path | `M / first open in trailing 3h - 1`; `(max high-min low)/A`; `M/max high-1` | Strictly trailing off-session OHLC |
| Native | `previous close / previous session open - 1`; `previous session open / earlier close - 1` | Fully completed earlier native sessions |
| Full | `(T-latest completion)/hour`; `(expected-observed)/expected`; prior-gap missing indicator | Calendar and preceding observation grid |

Inputs retain completion times, native-session and Reality content hashes, and source version in
the prediction provenance. Event-time is necessary but not sufficient for original as-known
availability. No corporate actions, future open, current-session native close, State, Confidence,
Gap, Conviction, cross-sectional normalization, or future/prospective observation enters features.
All rolling windows are trailing. Scaling and optional-value imputation are fit only on the
training portion of development and then refit on all development for validation; zero-variance
columns use scale one. No fitted statistic uses validation.

## Candidates and selection

The predeclared small set is ridge (intercept unpenalized, L2=1) and Huber-style IRLS robust
ridge (delta=1.5 MAD scale, 12 fixed iterations), each for four nested feature groups: eight
fits. The shallow tree candidate was omitted: 210 internal-fit rows across 21 names and a
two-parameter winning linear fit give no complexity justification. No hyperparameter sweep,
random shuffle, or symbol-specific selection occurs. Development sessions are split by unique
decision date, first 60% (210 observations, through July 2) fitting, remainder (147 observations,
July 7–15) internal scoring; minimum internal bps MAE wins, with parameter count and name as
ties. Validation is external evaluation only. Selected internal candidate:
`HUBER_DISPLACEMENT`, one feature, two coefficients, 357 full-development fit rows. This is
the *research candidate*, not an accepted V1 production model. Prediction uncertainty is omitted:
no calibrated coverage or independent prospective residuals justify an interval.

## Results

All numbers below are RETROSPECTIVE ESTIMATED. Price MAE/RMSE are in native price units;
bps errors divide by previous native close. Development has 357 aligned observations; validation
has 462, all 21 symbols. This filtered Fair Value sample is not the entire baseline universe:
the prior baseline evaluation also reports its own 420 development and 462 validation candidate
observations. Within each table below every candidate is recomputed on the *identical* Fair Value
sample; report JSON also carries candidate-specific and common samples separately.

| Validation, n=462 | Price MAE | Price RMSE | Price median AE | Bps MAE | Bps RMSE | Bps median AE | Bps bias | Direction |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Previous close | 10.073 | 21.921 | 3.225 | 275.07 | 402.47 | 177.77 | -34.39 | 0.0% |
| Reality mark | 3.241 | 7.004 | 1.270 | **98.27** | **143.57** | 67.46 | 14.21 | 87.66% |
| Return transfer | 3.251 | 7.071 | **1.230** | 98.63 | 144.09 | **66.28** | 15.07 | **88.10%** |
| Fixed blend | 5.964 | 13.089 | 2.008 | 166.34 | 241.61 | 118.05 | -9.66 | **88.10%** |
| Selected candidate | **3.188** | 7.022 | 1.343 | 99.84 | 146.98 | 69.86 | 11.82 | **88.10%** |

On matched development rows, selected-candidate bps MAE/RMSE/median/bias are
96.44/144.09/65.11/+4.21 versus Reality mark 103.06/152.18/66.63/+13.68 and
return transfer 102.58/151.69/66.98/+13.20. The validation raw MAE gain against mark is
only 0.053 price units (~1.6%), while bps MAE worsens by 1.58, RMSE by 0.018 price units,
median by 0.073 price units. Bias improves, directional accuracy is 0.43 percentage points
higher than mark and tied with transfer. This is mixed, marginal and insufficient to claim
superiority. The absolute bps error median/p90/p95/p99 are 69.23/223.42/321.83/518.16;
the worst is 770.64 bps (RAAOIUSDT, August 4 decision). No outlier was removed.
Fair Value beats the Reality mark on per-symbol bps MAE in only 10 of 21 names. Each name has
22 validation observations; per-symbol Fair Value bps MAE ranges from 37.78 (RAMZNUSDT) to
224.85 (RSOXLUSDT). The generated report retains the matched baseline distribution for each.

| Ablation | Internal bps MAE, Huber / ridge | Validation bps MAE, Huber / ridge |
|---|---:|---:|
| Displacement | 92.67 / 97.13 | 99.84 / 99.17 |
| + Path | 95.44 / 99.15 | 101.89 / 100.37 |
| + Native | 108.88 / 109.79 | 107.37 / 107.86 |
| Full | 108.95 / 110.02 | 107.26 / 106.97 |

These validation ablations are descriptive only and did not change the selected model. The
private generated report gives all eight models' price and bps metrics, per-symbol distributions,
and worst cases. Correlated symbols and sessions preclude independent-sample significance claims.
The report also retains every fitted intercept, coefficient, development mean and scale.

## Output and limitations

Each private prediction has symbol, decision timestamp, previous native close, predicted return
and reconstructed fair value price, model/feature/dataset/split/experiment identity and input
references. It contains **no outcome**; outcome join occurs only in the report generation. The
experiment binds exact source hashes, accepted dataset/protocol/target/split versions, parameters,
Git base commit and null random seed. No public raw values are published; data rights remain
unverified. No strategy returns, Sharpe or trading claim exists. Production selection awaits
meaningful prospectively safe snapshots and a separately declared evaluation; do not retune on
this validation or inspect final OOS.

# Baseline experiments and backtest status

## Discovery State V1 is not a strategy backtest

The four outcome-defined research labels separate retrospective reopen behavior, but the
chronological four-state classifier misses every OVERSHOOT observation. Confidence buckets
separate classification reliability, not monotonically mark error. Decision:
**DISCOVERY_STATE_V1_NOT_JUSTIFIED**. No PnL, trading rule, final OOS or BACKTESTED claim exists.
See [Discovery State](DISCOVERY_STATE.md) for the generated private artifact and reproducibility.

## Fair Value V2 is not a strategy backtest

Four pre-OOS expanding-window folds yield 504 matched retrospective predictions from
819 eligible research rows. None of the three low-complexity fitted models beats the Reality
mark on both bps MAE and RMSE. Decision: **FAIR_VALUE_V2_NOT_JUSTIFIED**. The old validation
was already inspected, so V2 uses it only inside pre-OOS development, never as a fresh external
holdout. Final OOS, transaction costs, PnL and Sharpe were not evaluated. All figures are
RETROSPECTIVE ESTIMATED, not BACKTESTED. See [Fair Value](FAIR_VALUE.md) for generated artifact
identity and reproduction.

## Day 2 Fair Value result

The [generated Fair Value comparison and analysis](FAIR_VALUE.md) reports 357 development and
462 validation matched observations for the development-selected robust displacement candidate.
It does not convincingly beat the Reality mark on validation: raw MAE 3.188 vs 3.241, but bps MAE
99.84 vs 98.27, raw RMSE 7.022 vs 7.004, median AE 1.343 vs 1.270. Direction is 88.10% vs
87.66%. Classification is **RETROSPECTIVE ESTIMATED**; V1 selection is not justified. Private
machine output contains all metrics and ablations; no strategy PnL or final OOS result exists.

## Remote capture status

The worker and outcome-link pipeline are deployed (see HANDOVER). No legitimate
prospective decision snapshot or outcome has yet been captured remotely. Existing retrospective
baseline metrics remain ESTIMATED; no BACKTESTED claim or final-OOS strategy performance has been
computed. A missed automatic capture remains missed rather than retroactively filled.

Current phase: **PHASE 2 — RESEARCH BASELINES**. Final OOS remains untouched by performance
evaluation. No trading strategy or economic backtest exists. The blueprint's 60-day strategy
backtest and 30-day final-OOS performance requirements are not yet satisfied.

The historical revision-integrity audit selected decision B:
`RETROSPECTIVE_POINT_IN_TIME_NOT_VERIFIABLE_PROSPECTIVE_CAPTURE_READY`. Alpaca's official stream
contract establishes that minute bars can change after late/corrected/canceled trades; Bitget's
historical Reality contract does not establish immutability or as-known snapshots. Six bounded
DEVELOPMENT refetches were unchanged, which is insufficient to alter that decision. Details are in
[POINT_IN_TIME_INTEGRITY.md](POINT_IN_TIME_INTEGRITY.md).

The [frozen protocol](RESEARCH_PROTOCOL.md) defines exact partitions, decision timestamps, raw
reopen target, four naive predictions, metric formulas, shared-sample comparisons, missingness,
source availability, staleness, experiment identity and future execution costs. No Fair Value,
Discovery State, Confidence, Conviction, portfolio, or execution model was introduced.

Private development and validation diagnostics use all 21 accepted symbols. Results are computed
by `.venv/bin/python -m research.baselines --partition DEVELOPMENT` (or `VALIDATION`), never
handwritten. Each command emits a content-addressed mode-0600 JSON result and observation ledger
under `.local-data/research/experiments/`; repeated identical runs verify rather than overwrite.
The [run receipt](../research/experiments/verification.json) records canonical experiment IDs and
verification status without exposing prices or diagnostic metrics in tracked artifacts.

Results carry **ESTIMATED** because archived prices lack proven original historical availability
and revision history. Model-feature eligibility remains blocked. Counts/checksums are **OBSERVED**;
future execution rules are **TARGET**; Reality predictive value is a **HYPOTHESIS**. No results
qualify as **BACKTESTED** under the blueprint's strict as-known replay definition. Development
errors cannot establish final evidence or tradable alpha.

Future results from `decision_snapshot.v1` begin as **PROSPECTIVE OBSERVED**. They can become
BACKTESTED only after enough immutable captures and outcome versions exist and a new experiment is
frozen. The prospective collector does not access, score, or weaken the protected historical OOS.

Final OOS is unsupported by both normal CLI and library evaluation. Tests exercise rejection
before reading archives, split crossing, future outcomes and incomplete-bar rejection, model
eligibility, deterministic formulas, metric ties, missing observations, age reporting and identity.
Synthetic test values never enter production research. No OOS metrics have been generated.

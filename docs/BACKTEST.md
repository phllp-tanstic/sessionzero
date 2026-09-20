# Baseline experiments and backtest status

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

# Discovery State V1 — retrospective research diagnostic

## Subsequent formulation audit (V1 decision unchanged)

The [pre-OOS trajectory redesign](RESEARCH_REDESIGN.md) measures seven off-session times, direct
label sensitivity, retrospective transitions and OVERSHOOT support. It recommends separating
latent direction/transfer, path and evidence quality before any later mapping to the four locked
product names. V1 remains **DISCOVERY_STATE_V1_NOT_JUSTIFIED**; no State or Confidence V2 model
was built and no final OOS was inspected.

Decision: **DISCOVERY_STATE_V1_NOT_JUSTIFIED**. All figures below are **RETROSPECTIVE ESTIMATED** from archived prices whose original as-known availability and revisions are unverified. No production State or Confidence output is authorized. The generated private result is authoritative; these rounded figures describe pre-commit run `fed2b74ff83adda8b248bfafd80c1974eb19ceb4b3a06569568d64f0eb10f843`. A source edit or commit changes the experiment ID.

## Identity and reference

The frozen [machine contract](../research/protocols/discovery-state-v1.json) binds the accepted Phase 1 dataset, `fair_value_protocol.v2` pre-OOS folds, `discovery_label_ratio.v1`, `discovery_event_time.v1`, pooled regularized multinomial model, confidence calibration, exact source hashes and Git base commit. `FAIR_VALUE_BASELINE_V0 = REALITY_MARK`: the latest eligible completed hourly Reality candle close before the frozen decision. It is a historical price proxy, not an executable quote, learned model, or claim of superiority. Fair Value V1/V2 were not promoted.

## Labels and features

For previous native close C, Reality mark M, and future native first-minute open Y, set R=M/C−1 and O=Y/C−1. The fit-only resolution floor is 0.25 times the median absolute R in that fold's prior training dates. `NOISE` means either |R| or |O| is at/below that floor or R and O disagree in sign. Otherwise O/R below 2/3 is `OVERSHOOT`, above 3/2 is `UNDERREACTION`, and within the inclusive bounds is `DISCOVERY`. Equal bounds go to `DISCOVERY`. These semantic ratio/floor conventions were declared before evaluating the final OOS; they are not tuned to returns or classifier scores. Labels use Y only in training and scoring. A future reopen is never a decision feature.

The four nested ablations add: A Reality mark displacement/absolute magnitude; B trailing momentum, range, reversal, path efficiency and sign changes; C previous completed native session return and prior gap; D mark age, missing-hour fraction/count and native missing indicator. Every Reality bar is completed strictly before T and path hashes are checked against the accepted row builder; native fields precede T. The source-session evidence gate and exact anchor from the inherited row builder exclude unknown paths, rather than silently declaring those rows `NOISE`. This means this diagnostic does **not** measure a data-quality-driven NOISE state on excluded records. Historical price features remain `UNKNOWN_AVAILABILITY`, not certified point-in-time; zero rows are model-eligible in the strict lane. No Fair Value V1/V2 fitted outputs enter the state features.

Four blocked, expanding chronological folds fit 315/441/567/693 rows and score 126 each, using only completed prior labels. A pooled four-class L2 softmax has fixed step count, learning rate, and regularization; fit-only mean imputation and scaling are deterministic. Within each fit period, earlier 70% of dates fit a calibration model and later dates select temperature by multiclass log loss over the frozen candidate set. The main model then refits all prior dates. Confidence is its temperature-scaled maximum class probability, not an arbitrary weighted score. Bucket boundaries are fixed at [0,.5), [.5,.75), [.75,1]. This is a provisional probability mapping; the observed bucket reliability, not the temperature procedure alone, determines whether calibration may be claimed.

## Generated findings

Across 504 scored observations: `DISCOVERY` 222 (44.0%), `UNDERREACTION` 100 (19.8%), `OVERSHOOT` 37 (7.3%), `NOISE` 145 (28.8%). Each symbol has 24 scored observations; `OVERSHOOT` is absent in several names and peaks at six in RRKLB. Fold distributions are retained in the private report and range from 5 to 15 `OVERSHOOT` cases per fold. No class or name was silently dropped.

The outcome-defined labels have distinct behavior, as expected partly by construction: mark absolute error is 69.52/174.25/139.77/81.07 bps in the state order above; median transfer ratio is 1.06/1.95/0.56/0.13. Direction agreement is 100% for the first three by label definition and 57.2% for NOISE. Signed mark error is −14.68/−34.20/+102.26/+45.82 bps. The report also computes p50/p90/p95 absolute errors; label behavior is descriptive and cannot by itself prove inferability.

Macro F1 by ablation A/B/C/D is .367/.410/.413/.423; balanced accuracy is .440/.455/.454/.456. Path adds a modest improvement; native context adds very little, and quality adds little. The full model's macro F1 is .423 and balanced accuracy .456; per-class recall is .874/.130/**0**/.821. It never predicts `OVERSHOOT` correctly. Fold macro F1 is .405/.375/.470/.371: unstable and too weak for four-state deployment. Full confusion matrix and per-symbol distribution are generated in the private result.

Low/medium/high confidence groups contain 133/205/166 observations. Their mean confidence is .419/.625/.854 and realized classification reliability .421/.605/.880, respectively. This is encouraging for *classification reliability*, but mark absolute error is 106.92/95.61/96.17 bps and direction agreement .872/.878/.880: error is not monotone and directional differences are negligible. The small overall reliability trend does not rescue zero overshoot recall or establish calibrated per-class probabilities. A low-confidence cutoff would exclude 133 observations with only 42.1% correct classifications, versus 60.5%/88.0% above it; this is a retrospective abstention *hypothesis*, not a validated threshold or trade decision. No PnL, Sharpe, Gap, Conviction, execution rule, or final OOS selection was computed.

No independent source leadership was estimated: a single Reality path plus native context cannot identify competing sources. Any state-dependent reliability interpretation is **HYPOTHESIS**. This research establishes label separability descriptively (A: qualified yes), but not stable four-state inference (B: no); confidence relates to classification correctness (C: provisional yes) but not monotonically to reopening error, so an abstention foundation (D) is **partial and unpromoted**. Overall decision: **NOT JUSTIFIED**.

## Reproduce and guard

Run `.venv/bin/python -m research.discovery_state` from the repository root with the retained private, checksum-verified Phase 1 archives. No provider, database, credentials, or network is needed. It writes append-only mode-0600 result and outcome-free state records under `.local-data/research/experiments/<experiment_id>/`. The state contract includes symbol, T, Fair Value reference version, inferred state, model/confidence/feature versions, confidence, experiment ID and input provenance; outcomes appear only in the private evaluation report. The runner has no OOS option, verifies the inherited frozen split before archive access, and reuses the Fair Value row builder's OOS guard. It does not alter the cohort, target, prospective capture, deployment or public frontend. Public derived-output rights are still unverified.

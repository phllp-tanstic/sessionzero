# Root-cause research redesign — trajectories and latent discovery state

Status: **RETROSPECTIVE ESTIMATED diagnostic**, not a new Fair Value, State, Confidence or trading model. The accepted historical outcomes `FAIR_VALUE_V1_NOT_JUSTIFIED`, `FAIR_VALUE_V2_NOT_JUSTIFIED` and `DISCOVERY_STATE_V1_NOT_JUSTIFIED` remain unchanged. The authoritative generated private result is `research-redesign-result.json` in `.local-data/research/experiments/<experiment_id>/`; the first pre-commit receipt is `b2dc198b1e6a4bc384e4f16704c863831697f495885e99678afe800a5021d7bb`. Source or Git changes produce a new ID. Reproduce offline with `.venv/bin/python -m research.research_redesign` and the checksum-verified Phase 1 archives. [Machine protocol](../research/protocols/research-redesign-v1.json).

## What changes, and what remains

This diagnostic *adds* calendar-relative evaluation times and continuous path measurements; it does not alter the accepted cohort, target, archive, V1/V2 Fair Value models, V1 State model, prospective worker, or final-OOS boundary. Earlier negative outcomes are retained as valid tests of their own formulations. No model is fitted here beyond rerunning the **unchanged** V1 classifier to verify its two confidence targets. The reason for a new protocol is to test whether a single T−60 mark can represent an evolving off-session process and whether the direct four-class target is stable.

The seven predeclared slots are previous XNYS close +2h, +6h, and next scheduled XNYS open −6h, −3h, −2h, −1h, −30m. XNYS calendar instants are UTC and DST-safe; slot selection is independent of outcomes. Only 1H Reality candles completed *strictly before* a slot can enter. The −30m slot intentionally tests whether the present hourly feed adds information after −1h; it does not, and is omitted from transition-persistence calculations. The next native `FIRST_1M_BAR_OPEN` is a retrospective label/evaluation join only.

Each outcome-free `StateTrajectoryRecord` carries symbol, cash-session date, slot/time, trajectory features, no inferred state (none is modeled), null previous modeled state, dataset/protocol/experiment IDs and input provenance. Features include Reality displacement, anchor-relative return, log-return path efficiency/realized volatility, high-low range, running-high/low distance, trailing three-hour momentum, reversal, sign changes, log-price slope, observation density/missingness and staleness. Every bar and the exact previous native close precede evaluation; path hashes make the inputs auditable. Historical original availability and revisions remain **UNKNOWN_AVAILABILITY**.

## Multi-timestamp evidence and single-timestamp diagnosis

The pre-OOS calendar supplies 42 candidate cash sessions × 21 symbols. One session lacks an exact Reality anchor (21 symbol-session pairs); two more fail the source-path evidence gate at later slots (42 pairs). There are 5,817 trajectory records across 861 eligible symbol-sessions / 41 distinct cash sessions. All seven slots are present for 819 symbol-sessions. The 5,817 repeated measurements are **not independent observations**.

On the common 819-pair panel, Reality-mark MAE declines from 263.64 bps at close+2h to 228.17 at close+6h, 178.70 at open−6h, 138.26 at −3h, 123.91 at −2h, and 100.35 at −1h. Direction agreement rises from 54.6% to 88.5%. The −30m slot is identical to −1h on mark, labels and mark error because its newest eligible completed hourly bar is the same. This is *strong evidence that the discovery process evolves* and one T−60 snapshot omits earlier path/transition information. It is **not** evidence that T−60 is a poor terminal mark; it has the smallest error among distinct tested hourly slots. A different model family alone is not established as the root cause.

| Candidate failure cause | Current diagnosis |
|---|---|
| Wrong model family | **INCONCLUSIVE**: only simple V1 state inference was tested; no new classifier is fit here. |
| Wrong direct label | **SUPPORTED**: material ratio-versus-residual assignment changes and near-zero instability. |
| One T−60 snapshot | **SUPPORTED for process description**, not for terminal mark quality. |
| Rare OVERSHOOT | **SUPPORTED** under V1 labels; prevalence changes with time/rule, and support is clustered. |
| Missing path evolution | **SUPPORTED as information loss**; predictive benefit of adding it remains untested. |
| Insufficient independent sources | **SUPPORTED** for leadership research. |
| Wrong confidence target | **SUPPORTED**: class correctness rises with V1 confidence; mark reliability does not. |
| Insufficient effective sample | **SUPPORTED concern**: 41 distinct dates and rare, correlated labels. |

## Continuous latent quantities and label sensitivity

Keep separate latent coordinates rather than immediately predicting a four-class code:

- **Direction quality:** sign(R·O), with a near-zero/indeterminate region calibrated from prior development displacements.
- **Magnitude transfer:** O/R only when |R| clears that resolution; also retain signed residual O−R and `10,000×(O−R)` bps. The ratio is unstable near zero.
- **Path quality:** efficiency, realized path volatility, reversal and direction changes measured only through T.
- **Evidence quality:** known source-session status, completion/ingestion times, missing intervals and staleness.

The previous-close and Reality mark define R; future open defines O **only for retrospective evaluation**. A possible later latent architecture would estimate a predictive distribution over reopen residual/direction from trailing trajectories, retain path/evidence reliability as separate decision-time dimensions, then derive the locked `DISCOVERY`, `UNDERREACTION`, `OVERSHOOT`, `NOISE` names through a frozen decision map. That map must be specified before prospective evaluation and must allow uncertainty/indeterminacy; no map or classifier is promoted here.

For a non-tuned sensitivity audit, slot-specific resolution floors are 25% of median |R| over the first 15 pre-OOS cash sessions. The V1 ratio bands 2/3–3/2 are compared with transparent narrower 3/4–4/3 bands, and with a development-median absolute-residual band. All thresholds are fit from the same early development slice, never final OOS. The narrower ratio bands change 365/5,817 assignments (6.3%); the absolute-residual formulation changes 1,041/5,817 (17.9%). At T−60 the two variants change 79/819 and 175/819, respectively. All four states remain present overall, but residual-based `OVERSHOOT` has only 4/861 cases at close+2h. Thus modest ratio-band changes are material near the open, and changing the geometric definition of “agreement” materially alters direct labels. The four-state product vocabulary is retained; the direct V1 label formulation **needs latent reformulation**.

## OVERSHOOT and transitions

`OVERSHOOT` occurs 29/861 at close+2h, 43/861 at +6h, 62/819 at open−6h, 73/819 at −3h, 64/819 at −2h and 68/819 at −1h. The −30m count repeats −1h. This is timestamp-dependent in frequency but remains a small class. Across all seven repeated slots, 407 overshoot labels include 64 for RRKLB; RAAPL has only two. Those 407 are *not* independent examples. Frequency is 0.6% for <50 bps displacement versus 13.0% for ≥200 bps; 2.4% in the lowest versus 12.0% in the highest trailing-volatility tercile; path-efficiency tercile rates are 4.7%/9.7%/6.5%. These are associated conditions, not causal explanations or new labeling thresholds. The 42 late-slot exclusions are source-path unknowns, not enough to account for zero V1 OVERSHOOT recall by themselves. V1's 37/504 walk-forward overshoots and this diagnostic's 68/819 T−60 overshoots have different samples and fit-floor policies and must not be equated. Scarcity plus correlated observations makes reliable class inference underidentified with this archive.

At T−60, the narrower ratio convention raises `OVERSHOOT` to 91/819, while the development-residual convention gives 86/819; this shows threshold/geometry contributes to prevalence without making the class robustly inferable. No evidence here can establish whether overshoot is economically rare in the broader market universe.

The retrospective label transition matrix (excluding redundant −30m) has 66.8% adjacent-slot persistence. Conditional self-transition probabilities are 75.6% `DISCOVERY`, 54.5% `UNDERREACTION`, 65.1% `OVERSHOOT`, 71.4% `NOISE`. `UNDERREACTION→DISCOVERY` occurs in 29.8% of transitions leaving `UNDERREACTION`; `NOISE→UNDERREACTION` in 18.5% of transitions leaving `NOISE`. Early slots are mostly `NOISE`/`UNDERREACTION`; `DISCOVERY` becomes common nearer the open. These are **outcome-informed historical labels**, not observable real-time state transitions or predictive Markov probabilities. The shared eventual reopen mechanically links labels within a session.

Improved late-slot direction and error describe a clearer *outcome relationship*, not proven classifier separability. No new slot-specific inference model was trained, so whether states become easier to predict nearer the open remains unresolved.

## Conditional Fair Value and Confidence

The mark's error plainly changes with time, but simple path conditioning is not yet a reproducible fair-value correction. Pooled path-efficiency tercile MAEs are 135/143/209 bps (low/mid/high), reversal terciles 135/153/200, and volatility terciles 140/143/205. These bins pool early and late slots and are confounded by elapsed time, displacement and repeated symbol-sessions. High path efficiency does **not** imply smaller mark error in this sample. No Fair Value V3 is justified by these descriptive cuts. A future hypothesis should compare *within-slot, chronological out-of-sample* conditional residuals on prospectively captured paths.

V1 Discovery Confidence answers “how certain is the four-class classifier?” Its unchanged chronological low/medium/high buckets have classification reliability 42.1/60.5/88.0%, but Reality-mark MAE 106.9/95.6/96.2 bps and direction agreement 87.2/87.8/88.0%. It does not consistently answer “how reliable is price discovery?” A future research protocol should distinguish `STATE_CONFIDENCE = P(correct state interpretation | available evidence)` from `PRICE_DISCOVERY_CONFIDENCE = P(|mark−reopen|≤δ | available evidence)` or a calibrated expected-error distribution. δ must be declared from a real use case and pre-OOS/prospective development, not optimized for PnL. Calibration should use chronology and account for symbol/date clustering; path stability, completeness and staleness enter as predictors, not arbitrary averaged score components. Introducing two eventual product outputs requires separate product-contract review; neither exists now.

The low V1 confidence group is less correctly classified, but its mark error is not monotonically worse and its direction agreement barely differs. Early marks have much larger error and weaker direction agreement, but that is time-to-open, not a validated confidence or abstention rule. **No abstention threshold is established.** The appropriate future decision-theoretic question is whether an interpretation's calibrated uncertainty exceeds the cost of being wrong, under a separately declared loss function—not a tuned score cutoff.

At the V1 scored T−60 timestamps, path-efficiency terciles have state-classification reliability 69.6/49.4/75.0% (low/mid/high), mark MAE 88.2/104.0/104.1 bps, and direction agreement 71.4/93.5/98.2%. Among 76 paths with any missing hour, classifier reliability is 57.9% versus 65.9% for 428 complete paths, yet mark error is 95.7 versus 99.3 bps and directional agreement is 92.1% versus 86.9%. Every V1 mark is within one hour by the candle-completion measure, so this sample cannot assess a stale-mark abstention rule. These crossed targets reinforce that path/data-quality indicators cannot simply be averaged into one “confidence” score.

## Source diversity and leadership feasibility

The machine audit distinguishes capability from an *aligned, independent research panel*. Bitget Reality 1H is **AVAILABLE** as the sole accepted continuous path; historical as-known semantics and public-derived rights are unverified. Alpaca SIP/raw is **AVAILABLE** for exact native cash boundaries but does not supply an accepted overnight path. Public Bitget stock-perpetual/index-component endpoints are **DEGRADED for this research**: the capability has been observed, but no aligned, versioned cohort history or independence/PIT validation exists. User-reported Bitget MCP native adjusted-daily data is **DEGRADED** for intraday leadership. Bitget Stock+ is **GATED** by signed entitlement; Alpaca's documented delayed `feed=boats` overnight history is **GATED for this research** because it has not been requested, validated, licensed or captured. A composite index may reuse other venues' prices and cannot count as an independent leader without constituent lineage.

| Source | Session/granularity usable in this archive | Independence and as-known limit |
|---|---|---|
| Bitget Reality | Off-session 1H path, 21 accepted symbols | One tradable source; original revisions/latency unknown. |
| Alpaca SIP/raw native | Exact regular-session boundary 1Min bars | Distinct cash-market outcome/context, **not** a contemporaneous overnight path; revisions possible. |
| Bitget stock perpetual | Public derivative capability, no aligned accepted 1H panel | Distinct contract; index components may overlap/republish other venues. |
| Bitget MCP native | User-reported adjusted daily only | No usable intraday leadership timing; upstream identity unverified. |
| Bitget Stock+ | Documented minute/native sessions, access gated | Entitlement, historical as-known behavior and rights unverified. |
| Alpaca BOATS | Documented delayed historical overnight bars, not collected | Potential distinct overnight venue; coverage, PIT and rights unverified. |
| Bitget index components | Observed public AAPL composite, no aligned panel | Constituent reuse means independence cannot be assumed. |

Official documentation currently supports Bitget public Reality/history candle access, Stock+ read-only permission for native history, and Alpaca's distinct BOATS/Overnight feed options ([Bitget market history](https://www.bitget.com/docs/catalog/market/market-data), [Stock+ historical candles](https://www.bitget.com/zh-CN/docs/catalog/stock-plus/stock-quotes), [Alpaca 24/5](https://docs.alpaca.markets/us/docs/245-trading-for-trading-api)). These document *capability*, not the account's entitlement, source independence, publication-time integrity, historical overlap, or redistribution rights. **SOURCE_LEADERSHIP_NOT_INSTRUMENTED**: dynamic leadership cannot be validated from one accepted continuous feed plus later native outcome. No provider or hardcoded leadership weights were added.

## Identifiability and prospective capture gap

The pre-OOS panel has 21 symbols, 41 eligible dates (42 candidate dates), 861 eligible symbol-sessions and 5,817 repeated rows; a complete seven-slot panel has 819 symbol-sessions. Effective information is constrained by 41 shared macro/event dates, strong within-session serial dependence, cross-symbol co-movement and rare overshoots. A broad trajectory classifier with dozens of coefficients or symbol effects would not be defensible. More duplicate timestamps do not solve missing rare-state support; a genuinely longer, as-known history with diverse events and sufficient overshoot cases is needed, and even that may not make four classes separately inferable.

The deployed `decision_snapshot.v1` captures only T−60 Reality mark and exact previous native close, then links the later outcome. It cannot reconstruct the preceding path, earlier snapshots, transitions, observation-density/staleness evolution or source agreement. A compatible *future* capture contract would append immutable raw Reality OHLCV versions through each declared slot, bar completion/request/ingestion times, per-slot source-session evidence and quality/missingness, plus versioned calendar/mapping/cohort IDs and later outcome linkage outside every feature snapshot. For leadership, separately sourced, aligned provider observations and constituent/provenance/rights evidence are required. Do not retroactively reconstruct missed prospective snapshots. This is a specification only; the worker and database are unchanged.

## Required decisions and next architecture

| Question | Decision | Basis |
|---|---|
| SINGLE_TIMESTAMP_FORMULATION | **INADEQUATE** for state-process research; terminal T−60 mark retained | large within-session evolution, redundant −30m |
| DIRECT_FOUR_CLASS_LABELS | **NEEDS_LATENT_REFORMULATION** | ratio/residual sensitivity and near-zero instability |
| OVERSHOOT_SUPPORT | **INSUFFICIENT** for stable inference, with timestamp-dependent prevalence | 37 V1 scored cases/zero recall; 29–73 per trajectory slot, clustered |
| DISCOVERY_CONFIDENCE_V1 | **NEEDS_REDEFINITION** | tracks classifier correctness, not reliably mark error |
| SOURCE_LEADERSHIP | **NOT_INSTRUMENTED** | no accepted independent aligned second continuous source |
| PROSPECTIVE_CAPTURE | **REQUIRES_ADDITIONAL_CAPTURE_FIELDS** | current snapshot is mark-only at T−60 |

Next architecture: freeze a *prospective* multi-slot raw-path capture protocol; collect immutable aligned independent sources only after technical/rights validation; define continuous direction-transfer-residual and evidence-quality targets with an explicit near-zero regime; assess their chronological stability and clustered uncertainty; derive the locked four names only if latent dimensions can be inferred; separately calibrate state correctness and mark-error reliability. Keep `FAIR_VALUE_BASELINE_V0 = REALITY_MARK` until a separate prospective conditional-value experiment earns promotion. No new production model, strategy, PnL, deployment or final-OOS access occurred.

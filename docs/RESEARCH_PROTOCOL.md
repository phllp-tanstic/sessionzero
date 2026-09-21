# Frozen baseline protocol v1

## Research-redesign v1 diagnostic (not a replacement baseline protocol)

The [versioned pre-OOS trajectory protocol](../research/protocols/research-redesign-v1.json)
inherits the accepted Fair Value V2 split/dataset and rejects OOS before archive access. Seven
calendar-relative slots, strict completed-bar features, early-development-only label scales,
two sensitivity alternatives and outcome-free trajectory records test formulation root causes.
It does not revise baseline/Fair Value/Discovery State V1 contracts or promote a new model.
[Generated findings and next architecture](RESEARCH_REDESIGN.md). Historical features remain
UNKNOWN_AVAILABILITY and findings RETROSPECTIVE ESTIMATED.

## Discovery State V1 pre-OOS extension

[`discovery_state_protocol.v1`](../research/protocols/discovery-state-v1.json) inherits the accepted
Fair Value V2 pre-OOS split and baseline identity without altering either frozen contract. It
defines fit-only label resolution, four locked states, nested event-time features, pooled
chronological inference, fit-only temperature selection, and fixed confidence buckets. The
historical archive is RETROSPECTIVE ESTIMATED, not as-known; no final OOS entry point exists.
The negative acceptance decision and limitations are in [Discovery State](DISCOVERY_STATE.md).

## Explicit Fair Value V2 protocol transition

[`fair_value_protocol.v2`](../research/protocols/fair-value-v2.json) supersedes only the use of
the old split for *future Fair Value research*. V1's `baseline_protocol.v1` and its immutable
30/30/30 split, experiment records, dataset/target/decision identities and negative V1 decision
remain historical facts. Its former VALIDATION (2026-07-15 20:00–2026-08-14 20:00 UTC) was
inspected during Fair Value V1 and cannot be represented as pristine external validation again.
V2 uses `PRE_OOS_RESEARCH` [2026-06-15 20:00, 2026-08-14 20:00) UTC with expanding chronological
folds. `FINAL_OOS` [2026-08-14 20:00, 2026-09-13 20:00) UTC remains frozen and unsupported by
the V2 runner. The protocol validates the historical union, baseline checksum, accepted dataset
and eligibility status before archive access; the row builder additionally rejects an end beyond
the final boundary. Outcome completion must precede the next fit's test decision. Details and
generated evidence are in [Fair Value](FAIR_VALUE.md). This is RETROSPECTIVE ESTIMATED only.

## Historical baseline v1 contract

Current phase: **PHASE 2 — RESEARCH BASELINES**. Final OOS remains untouched by performance
evaluation. Phase 1 is accepted and unchanged. This task implements the protocol and non-ML
benchmark machinery; **the strict leak-free benchmark acceptance gate is NOT PASSED** because
original historical availability and revision history of price inputs are unverified.

The later revision-integrity audit resolved this gate as decision B:
**RETROSPECTIVE_POINT_IN_TIME_NOT_VERIFIABLE_PROSPECTIVE_CAPTURE_READY**. It does not change this
frozen v1 protocol, its splits or its results. Current diagnostics remain RETROSPECTIVE ESTIMATED.
The separate `point_in_time_capture.v1` / `decision_snapshot.v1` path can accumulate PROSPECTIVE
OBSERVED evidence for a future experiment. See [the integrity report](POINT_IN_TIME_INTEGRITY.md).

The machine contract is [baseline-v1.json](../research/protocols/baseline-v1.json), pinned by SHA-256
in [the runner](../research/baselines.py). Changing the contract requires an explicitly new version,
not editing v1 after viewing errors. Dataset identity resolves through `datasets/phase1/latest.json`
and must match the frozen manifest hash and its logical content hash. The complete universe,
cohort, calendar, source-evidence (semantic and content), native-target, build commit and source-code
versions are in the contract. Every consumed private archive is checksum verified. No rebuild,
network request, database write, new symbol selection, or provider substitution is performed.

## Temporal contract

All ranges are UTC and half-open:

| Partition | Start inclusive | End exclusive |
|---|---|---|
| DEVELOPMENT | 2026-06-15 20:00 | 2026-07-15 20:00 |
| VALIDATION | 2026-07-15 20:00 | 2026-08-14 20:00 |
| FINAL_OOS | 2026-08-14 20:00 | 2026-09-13 20:00 |

This is the accepted 90-day history with the final 30-day holdout preserved. The first 60 days are
split equally by calendar duration, independently of outcomes. No weights or parameters are fit
in v1. A future fitted baseline may fit only DEVELOPMENT, evaluate on VALIDATION, and must freeze
its complete selection procedure before an independently authorized final-OOS run. Repeated
validation use is development evidence, not a new untouched holdout. No walk-forward fitting is
needed for these parameter-free candidates; this does not claim a 60-day strategy backtest.

Assignment requires BOTH the decision and first-minute outcome completion to precede the partition
end. Cross-boundary outcomes are purged, never borrowed from the following partition. Outcome
completion exactly on the end is also purged conservatively. June 15 is a reference anchor only;
September 14 remains an anchor outside the evaluation and is not scored. All 21 frozen symbols
stay in scope, including when a candidate cannot produce a prediction. No symbol ranking exists.

## Decision and target

For each evaluation cash session with scheduled open O, set T = O - 60 minutes, once per symbol.
The pinned XNYS schedule is authoritative, including DST and early closes. In the current window
these decisions are 12:30 UTC. This fixed operational lead is chosen without measuring errors;
hourly completed bars are compatible with the archive and leave time before the cash open. It is
an event-time diagnostic convention, not a measured data-delivery or execution-latency guarantee.

Let C be the preceding session's exact **LAST_1M_BAR_CLOSE**. Let Y be the current session's exact
**FIRST_1M_BAR_OPEN**, labeled **FUTURE_OUTCOME**. Canonical target: `y = Y / C - 1`;
canonical predicted return: `y_hat = P_hat / C - 1`. These are raw reopening price returns,
not total returns or official auction opens. The native first-minute bar must have completed
before its outcome is allowed into a partition's scoring. Its open is never a prediction input.

Let M be the latest archived Reality candle close whose completion is strictly before T and at
or after the preceding cash close. Let A be the Reality candle close completed exactly at that
cash close. No nearest-anchor substitution. The prediction function has only C, M, A arguments:

| Candidate | Predicted next native open |
|---|---|
| PREVIOUS_CLOSE | C |
| REALITY_MARK | M |
| REALITY_RETURN_TRANSFER | C × M / A |
| SIMPLE_BLEND | (C + C × M / A) / 2 |

The fixed 50/50 blend is an untuned shrinkage benchmark between no change and full return transfer.
`REALITY_MARK` is a name for an hourly last-price proxy, not a derivative mark or executable quote.
It assumes USDT/USD parity (**ESTIMATED**); no observed FX conversion exists. Return transfer
cancels a constant scale difference but does not remove time-varying FX, basis or corporate actions.

## Point-in-time gate and claim labels

The machine contract enumerates candidate families; unregistered fields fail closed.

- **AVAILABLE_AT_DECISION_TIME**: scheduled calendar information and explicitly scoped,
  effective source evidence with publication no later than the relevant historical timestamp.
  These are calendar/eligibility controls, not realized future sessions or halts.
- **FUTURE_OUTCOME**: next native open and incomplete/future candles. Always forbidden as features.
- **UNKNOWN_AVAILABILITY**: archived native previous close, Reality OHLCV, corporate actions and
  uncollected event/cross-asset/funding/depth/FX candidates. Forbidden as historical model features.
- **RESEARCH_ONLY_NOT_MODEL_ELIGIBLE**: retained current mapping/universe and retrieval metadata.
  The accepted cohort is a fixed research scope, not proof of a contemporaneously selected universe.

`require_model_eligible` additionally requires an actual availability bound no later than T. Giving
an old event timestamp to an UNKNOWN field does not make it eligible. Corporate-action effective
or ex-dates do not establish publication availability. No corporate actions enter these baselines,
and no historical prices are restated using them.

The separate retrospective diagnostic path uses archived raw C/M/A under the explicit assumption
that they stand in for original contemporaneous prices. It is **ESTIMATED**, not **BACKTESTED**:
original latency, corrections and historical identity cannot be proven by this archive. This is
not an exportable model feature matrix, a production signal, or final evidence. Archive counts
and checksums are **OBSERVED**. Execution components remain **TARGET**. The eventual predictive
value of Reality observations remains a **HYPOTHESIS**. No as-known leak-free claim is made.

## Missingness and staleness

Missing native boundary disables all candidates. Missing M disables Reality candidates; missing
exact A disables transfer and blend. Unknown/closed source coverage at any hourly boundary from
the reference bar start through the decision, or at the decision itself, disables Reality
candidates. Evidence without timely publication also fails closed. The previous-close baseline
remains separately reported. These are observation exclusions, never permanent symbol removals.

No interpolation, synthetic prices, or forward fill from before the previous cash close occurs.
An observed mark may remain the latest observation inside the same off-session interval only if
the entire source path is known open; missing intervening hours are counted, not filled. This is
an explicit last-observation selection rule, not a claim that the price stayed constant.

Age = T minus selected candle completion. This underestimates possible underlying last-trade age,
which is unavailable in OHLC. Report min/median/nearest-rank p95/max and count older than one hour.
A defensible economic staleness cutoff is not established: exclusion threshold is **TBD**, null in
the contract, and never optimized against OOS. Old observations remain diagnostics only. The exact
anchor has zero alignment age at the preceding close; missing anchors remain missing.

## Metrics and experiment identity

For e = P_hat - Y report mean absolute error, sqrt(mean(e²)), median absolute error, and mean(e)
(signed bias). Repeat all four on `10000 × e / C` in basis points. Directional accuracy is the
mean of `sign(P_hat-C) == sign(Y-C)`; sign(0)=0. Thus the no-change baseline matches direction only
when the actual open is unchanged; it is not scored as automatically 50% accurate. Empty samples
return null metrics, not zeros. No costs, Sharpe, trading PnL or strategy outputs are calculated.

Observation weights are equal, with no performance-based weighting. Price errors pool instruments
with different price scales; bps are the principal comparable unit. Each candidate reports its
own valid sample AND the intersection common sample across all four candidates. Compare candidates
on the common sample; report candidate-specific counts and per-symbol availability separately.
No confidence intervals or independent-observation significance is asserted for correlated names.

An experiment ID hashes dataset, full protocol, split, feature-set and target versions, exact
research/imported source hashes, parameters, partition and null random seed. Reports add Git base
commit, UTC run timestamp, outcome/record hash, metrics, exclusions, decision dates, age distribution,
and all-symbol counts. Code hashes resolve uncommitted source exactly; the base commit alone is
not falsely represented as the complete implementation. Reruns must match deterministic results;
existing results cannot be overwritten. Earlier runs remain in the private registry.

## Final OOS guard and reproduction

Both CLI choices and the library guard permit only DEVELOPMENT or VALIDATION. There is no
`--allow-final-oos` escape hatch in v1. The guard runs before archive access; the temporal filter
runs before outcome price extraction. Immutable archive files include OOS bytes and are parsed for
checksum-preserving replay, but no holdout prices are selected, predicted or scored. This is an
accidental-evaluation guard, not protection against someone intentionally writing a new program.
A future OOS command requires a separately reviewed implementation and authorization.

From repository root, with the existing environment and retained private Phase 1 archives:

```bash
.venv/bin/python -m research.baselines --partition DEVELOPMENT
.venv/bin/python -m research.baselines --partition VALIDATION
.venv/bin/pytest -m 'not live and not postgres' -q
```

No credentials, database or internet are needed. The CLI prints the exact experiment ID and private
result path. Mode-0600 JSON reports and observation ledgers live in the append-only directory
registry `.local-data/research/experiments/<experiment_id>/`. Raw prices and derived diagnostics
are not committed or exposed publicly. Public-derived rights remain unverified.

## Execution boundary (future only)

The machine contract freezes required components and fail-closed behavior: venue/account-specific
entry/exit fees and applicable funding/borrow; executable two-sided spread; size-dependent slippage;
actual receipt and execution delay; rejected/no-trade events; notional/per-name/portfolio caps;
initial cash, collateral, realized/unrealized PnL and capital constraints. Values are null and
**TARGET**, never implicitly zero or BACKTESTED. A strategy cannot run until values and stress
scenarios are independently measured or justified and frozen under a new execution contract before
viewing strategy performance. A candle close cannot be assumed fillable at decision time.

## Acceptance and next step

Deterministic contract, baselines, protected OOS, diagnostic runs and tests are implemented. The
remaining gate is evidence for original historical price availability/revisions and, where needed,
identity continuity. An artificial latency offset cannot fix missing revision history. Obtain that
evidence or establish a prospectively captured as-known dataset as a separate version; preserve this
accepted Phase 1 archive. Do not promote ESTIMATED diagnostics to BACKTESTED or start Fair Value.
The user's acceptance-conditioned commit is withheld while the strict gate remains unmet.

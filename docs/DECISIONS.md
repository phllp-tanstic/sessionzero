# Architecture Decision Records

## ADR-030 — Freeze trajectory evidence contract; gate the second source

Date: 2026-09-21. Status: **SPECIFICATION ACCEPTED FOR IMPLEMENTATION PLANNING; NOT DEPLOYED**.

Six XNYS-relative slots (close+2h/+6h; open−6h/−3h/−2h/−1h) are the prospective trajectory
capture target. T−30 is omitted at the current 1H cadence because it adds no new eligible
completed bar. A feature at T requires bar completion, actual ingestion and source evidence
strictly before the frozen slot cutoff. Raw envelopes and all corrected bar versions append;
one outcome-free snapshot per symbol/slot freezes the selected as-ingested path. Missed slots
stay missed. Existing T−60 snapshots remain valid `LEGACY_MARK_ONLY` evidence, not reconstructed
trajectories. The current worker/PostgreSQL are extendable/sufficient in architecture, with new
schema and scheduler work gated by migration, latency, capacity and backup verification.

BOATS is the strongest *hypothesized* independent second continuous venue, but account/feed
entitlement, 21-symbol overlap, PIT latency, storage/research/public-derived rights and
prospective capture are unverified. Bitget Stock+, MCP native and stock-perpetual/index inputs
do not currently pass the independent aligned-panel gate. Decision:
`SOURCE_LEADERSHIP_SECOND_SOURCE_GATED`; leadership research remains blocked. No provider,
worker, database, model, final-OOS, deployment or push change is authorized by this ADR.
[Capture contract](TRAJECTORY_CAPTURE.md); [source gate](SOURCE_LEADERSHIP_GATE.md).

## ADR-029 — Redesign research around trajectories and latent dimensions, without promoting a model

Date: 2026-09-21. Status: **RESEARCH ARCHITECTURE PROPOSED; NO PRODUCTION MODEL**.

The [root-cause audit](RESEARCH_REDESIGN.md) finds large, measurable within-session change in
mark accuracy and retrospective labels; T−30 adds no completed hourly-bar information beyond
T−60. The single snapshot is inadequate for state-process research, not evidence that the
terminal Reality-mark baseline should be abandoned. Direct labels are sensitive to the
agreement geometry, OVERSHOOT support is sparse/correlated, V1 confidence tracks classifier
correctness more than mark reliability, no accepted independent aligned second continuous source
supports leadership, and the deployed mark-only snapshots cannot replay trajectories. Future
research should begin with prospectively captured multi-slot paths and separate continuous
direction/transfer, path and evidence dimensions. Keep all V1/V2 negative outcomes, baseline,
cohort, target and final OOS unchanged. No new model, provider, worker change, strategy, push or
deployment is authorized by this ADR. Evidence remains RETROSPECTIVE ESTIMATED.

## ADR-028 — Reality mark reference; do not promote Discovery State V1

Date: 2026-09-21. Status: **DISCOVERY_STATE_V1_NOT_JUSTIFIED**.

Freeze `FAIR_VALUE_BASELINE_V0 = REALITY_MARK` for current MVP research, without claiming a
learned fair-value model. Fair Value V1/V2 remain non-promoted. A deterministic, versioned
four-state outcome-label contract and pooled chronological diagnostic over the accepted
pre-OOS region show descriptive behavioral separation, but the fitted model has zero OVERSHOOT
recall. Maximum temperature-scaled probability correlates with classification correctness;
reopening error does not decline monotonically. Do not promote State/Confidence or an
abstention threshold. Archived features remain UNKNOWN_AVAILABILITY and results RETROSPECTIVE
ESTIMATED. No final OOS, Gap, Conviction, strategy, frontend, worker, deployment or push.
[Contract, method and findings](DISCOVERY_STATE.md).

## ADR-027 — Version the inspected validation transition; do not promote Fair Value V2

Date: 2026-09-21. Status: **FAIR_VALUE_V2_NOT_JUSTIFIED**.

V1 inspected the original validation, so it is no longer pristine. Preserve its historical
30/30/30 experiments and frozen `baseline_protocol.v1`, but use new `fair_value_protocol.v2`
and `pre_oos_expanding_blocks.v2` for the combined first 60 days. The final 30-day OOS and
accepted dataset/cohort/target/decision time are unchanged. Four chronological folds compared
three fixed low-dimensional pooled transfer formulations to the Reality mark on identical
samples. All three worsen bps MAE and RMSE. The best fitted candidate wins only one fold;
no Fair Value model is promoted. Original archived prices remain UNKNOWN_AVAILABILITY, making
the evidence RETROSPECTIVE ESTIMATED. No State, Confidence, strategy, prospective worker change,
deployment or push. [Method and result](FAIR_VALUE.md).

## ADR-026 — Fair Value research candidate not promoted

Date: 2026-09-21. Status: **FAIR_VALUE_V1_NOT_YET_JUSTIFIED**.

The user authorized Day 2 development/validation Fair Value research without changing the frozen
dataset or point-in-time evidence policy. Eight low-dimensional ridge/robust-linear fits over four
nested feature groups were evaluated; a chronological development-only fold selected robust
displacement. On the identical validation sample, its small raw MAE gain over the Reality mark
does not survive normalized MAE, RMSE or median AE. Preserve this negative/mixed result and do
not select a production model from validation ablations. Archived prices remain
UNKNOWN_AVAILABILITY; all diagnostics are RETROSPECTIVE ESTIMATED, not BACKTESTED. No final OOS,
prospective worker change, State/Confidence, strategy, deployment or push. [Evidence](FAIR_VALUE.md).

## ADR-025 — Remote prospective worker and separate outcome linkage

Date: 2026-09-21. Status: IMPLEMENTED LOCALLY; DEPLOYMENT NOT AUTHORIZED.

The blueprint suggests Railway or equivalent persistent Python containers with managed
PostgreSQL, but does not lock a vendor. Choose a Railway-compatible one-shot cron container and
private persistent PostgreSQL. This affects operations only; the accepted calendar, cohort,
capture command and retrospective claim boundary remain unchanged. The worker derives the
decision from XNYS rather than a fixed UTC cron, records immutable run states, and rejects late
capture. Exactly one decision snapshot is allowed per timestamp; repeated evidence and later
outcome corrections append separate versions. The SIP/raw first-minute open is collected after
availability and linked outside the snapshot. Railway cron timing is approximate, so failure is
explicit and never backfilled. Usage-based worker/database cost and vendor rights remain risks.
[Runbook](DEPLOYMENT.md).

## ADR-024 — Historical prices remain retrospective; capture future decisions immutably

Date: 2026-09-20. Status: ACCEPTED — PROSPECTIVE CAPTURE READY.

Decision B is selected: `RETROSPECTIVE_POINT_IN_TIME_NOT_VERIFIABLE_PROSPECTIVE_CAPTURE_READY`.
Bitget's official Reality history contract supplies no historical revision/version/as-known
guarantee. Alpaca explicitly documents late-trade bar updates, corrected trades and canceled/error
trades; raw adjustment does not freeze those revisions. Six bounded DEVELOPMENT refetches matched
the archive but cannot prove historical immutability. Reality marks and previous native closes stay
RETROSPECTIVE_ONLY. Next native opens stay FUTURE_OUTCOME; their revision risk concerns label
stability, not historical feature leakage.

Migration `20260920_10` adds append-only capture runs, canonical observation versions, every raw
retrieval and deterministic decision snapshots. Identical content reuses a version; corrections
append. Database triggers reject UPDATE/DELETE. Capture is valid only in a predeclared pre-decision
window and only evidence ingested by the decision enters the snapshot. Future opens cannot be
represented in the snapshot schema or database constraints. The one-shot command is remotely
deployable and scheduler-free. `PROSPECTIVELY_SAFE` applies to captured evidence, not alpha or a
backtest. [Evidence and contract](POINT_IN_TIME_INTEGRITY.md).

This does not change the cohort, splits, final OOS or existing diagnostic labels. No Fair Value,
strategy, deployment or push is authorized by this decision.

## ADR-023 — Frozen naive baseline contract with protected final OOS

Date: 2026-09-20. Status: IMPLEMENTED; STRICT AS-KNOWN BENCHMARK ACCEPTANCE BLOCKED.

Bind research to the exact accepted manifest and private archive checksums. Freeze equal calendar
30-day development/validation splits before the accepted final 30-day OOS, one scheduled-open-minus-
60-minute decision per symbol/session, raw first-minute-open / previous-minute-close return, and
previous-close, Reality mark, return-transfer and fixed 50/50 shrinkage baselines. No fitting,
performance-dependent membership, synthetic prices or trading costs in prediction metrics.

The price archive cannot prove original availability or immutable historical revisions. Keep those
fields UNKNOWN_AVAILABILITY and forbidden to model features. A separate, explicit retrospective
comparison may run as ESTIMATED diagnostics only; it cannot satisfy the blueprint's as-known
BACKTESTED claim. Unknown-publication actions remain excluded. Future opens are outcome-only.

Both CLI and library reject FINAL_OOS before archive access. Partition outcome purging, closed-bar
alignment and a separate scalar prediction interface guard temporal leakage. Source-unknown paths
and absent exact anchors produce declared observation exclusions; all 21 names remain in scope.
Staleness is measured with an explicit TBD cutoff; costs are TARGET requirements pending empirical
values and a separately frozen execution contract. No strategy or Fair Value is authorized here.

All experiment versions remain privately retained and reproducible by code/content hashes. This
user-authorized research supersedes earlier no-research sequencing statements, but does not change
the accepted dataset or resolve availability/licensing gaps. The conditional acceptance commit is
withheld; no push or deployment. [Full protocol](RESEARCH_PROTOCOL.md).


## ADR-022 — Fixed, privately reproducible Phase 1 observation/outcome dataset

Date: 2026-09-20. Status: accepted for the user-authorized fixed 21-member backfill.

The build derives membership from retained machine-readable evidence and accepted Bitget mapping
provenance. It preserves the original universe reference and reproduces the accepted cohort hash;
it never invents a replacement snapshot. Tracked cohort/calendar/dataset manifests and private,
checksum-addressed archives remove reliance on temporary database state or chat-supplied hashes.

Every intersecting XNYS session has explicit exact-minute open/close target status. June 15 and
September 14 are separate anchors, while evaluation and final OOS bounds remain locked. The
provider-neutral target table references existing raw pages/normalized candles and preserves
corrections as immutable versions. Logical identity excludes generation/retrieval times and DB
surrogate IDs but binds observation content, definitions, evidence, calendar and build code.

Reality candles are durably joined at their completed-bar timestamp. Next open is FUTURE_OUTCOME;
previous close and Reality history carry unverified original-availability labels. This closes the
technical Phase 1 dataset gate without claiming a point-in-time feature matrix, auction prices,
public-data rights, model readiness, or any strategy result. Exact restore was demonstrated into
a fresh database. Public raw prices remain unapproved, and no Phase 2 modeling is authorized by
this decision. [Contract and evidence](PHASE1_DATASET.md).

## ADR-001 — Python is the quantitative source of truth

Status: **ACCEPTED**

Python owns market normalization and will own quantitative research. TypeScript is limited to the
web product and its transport contracts.

## ADR-002 — Alpha Factory / Open Theme positioning

Status: **ACCEPTED**

SessionZero targets Alpha Factory under Open Theme as closed-market price-discovery intelligence.

## ADR-003 — No synthetic Reality depth fallback

Status: **ACCEPTED**

Reality depth and platform fills are whitelist-gated. Until access is legitimately available,
capabilities report `GATED` and no substitute is presented as provider data.

## ADR-004 — Point-in-time historical replay is mandatory

Status: **ACCEPTED**

Future replay and research must reconstruct only information available at the selected timestamp.
No future values, revised data, or cherry-picked hardcoded displays are allowed.

## ADR-005 — Required provider failures fail closed

Status: **ACCEPTED**

Network, timeout, HTTP, provider-code, empty-result, or schema failure returns an explicit error.
Production paths never load fixtures or fabricate values.

## ADR-006 — Agent Hub is verification tooling, not the data plane

Status: **ACCEPTED**

The official `bgc` CLI independently confirms assumptions during development. SessionZero owns its
schemas, client, collection, errors, provenance, and tests and never shells out to `bgc` at runtime.

## ADR-007 — Phase 0 remains read-only

Status: **ACCEPTED**

No Agentic Account OAuth, private credentials, account reads, paper/live execution, or order code is
authorized. Research is the only eventual default until separately reviewed.

## ADR-008 — PostgreSQL persistence and conservative candle idempotency

Status: **ACCEPTED**

PostgreSQL is the sole production persistence database and Alembic is the schema authority. Each
persistence attempt retains its own run metadata and raw provider evidence. Normalized candle
identity is `(source, symbol, market, interval, event_time)` and is enforced by a database unique
constraint with `ON CONFLICT DO NOTHING` writes. Identical retries and differing ingestion times
do not change the first normalized record. Revised upstream values remain auditable in raw rows but
do not overwrite normalized values until a dedicated, versioned revision policy is designed.

The run row is created independently. Raw and normalized inserts and successful run finalization
share one transaction; a failed write rolls back both data tables before the run is marked failed.

## ADR-009 — Dataset quality gates bounded historical persistence

Status: **ACCEPTED**

Bounded Bitget history is normalized and validated as a complete dataset before PostgreSQL writes.
Timestamp/order/boundary defects, duplicates that survive page-overlap handling, impossible OHLC,
non-positive prices, negative quantities, pagination failure, and empty results are `FAIL` and are
not persisted. Missing regular intervals, unexpected spacing, and identical page overlap are
`WARN`; they may persist only with explicit quality metadata. Missing data is never filled.

ADR-010 replaces the original calendar-naive expected-interval policy while preserving ADR-009's
validation-before-persistence and no-fill decisions.

## ADR-010 — Reference sessions and source availability are separate point-in-time facts

Status: **ACCEPTED**

The reference U.S. cash calendar and a SessionZero source's expected availability have separate
provider interfaces. XNYS rules determine regular sessions, holidays, early closes, and adjacent
cash-session boundaries. They do not imply that a Bitget rToken was open or closed. Effective-dated,
cited Bitget capability records determine source availability and resolve to `UNKNOWN` when evidence
does not cover the symbol and timestamp.

Gap validation consults source availability: `EXPECTED_CLOSED` is informational,
`EXPECTED_OPEN` makes an absent candle a data-quality warning, and `UNKNOWN` remains visible. This
prevents both false feed-failure claims and retroactive application of current 24/7 marketing.

## ADR-011 — Native-equity implementation requires technical and licensing access

Status: **ACCEPTED — GATED**

The 2026-09-13 official-documentation review compared Massive, Alpaca Market Data, and Twelve Data.
Massive is the preferred technical candidate because it supplies consolidated U.S. coverage,
point-in-time identifiers, explicit adjusted/unadjusted aggregates, and splits. It is not selected:
no credentials are available and its self-service terms do not authorize SessionZero's intended
non-display strategy/derived-work use or public display/redistribution.

Alpaca Basic is IEX-only and therefore insufficient for the authoritative reference close. Twelve
Data requires paid split access and separate business/display or redistribution rights. No adapter,
schema, persistence, or symbol mapping may be implemented until a provider account and applicable
rights are verified. Clearing this gate does not authorize public display unless that permission is
separately explicit.

## ADR-012 — Check Bitget-native reference data before purchasing an external feed

Status: **ACCEPTED — PARTIALLY AVAILABLE / GATED**

After ADR-011 gated external-provider implementation, Bitget's current official Reality, UTA v3,
Stock+, stock-perpetual, and Agent Hub surfaces were reviewed before any external feed purchase.
Public Reality endpoints provide an explicit Reality-to-native-ticker mapping and partial
corporate-action metadata. Public UTA endpoints also provide stock-perpetual market, mark, and
index inputs. These capabilities may supplement reference metadata and risk controls but do not
constitute native cash-equity OHLC or an official regular-session close.

Stock+ is technically promising because its documented read-only market-data surface includes
native security metadata, real-time quotes, session-filtered candles, and historical OHLC. It
remains `GATED`: signed access was not authorized, eligibility and entitlements are unresolved,
and reviewed terms do not establish SessionZero's intended non-display, derived-output,
public-display, or redistribution rights. No provider or adapter is selected by this decision.

## ADR-013 — Version Bitget reference evidence without overwriting corrections

Status: **ACCEPTED**

Public Bitget Reality mapping, corporate actions, and source-session metadata use a dedicated
provider boundary and raw/normalized tables. They are not native-equity OHLC and do not replace a
calendar provider. Because Bitget exposes no stable action ID, a canonical hash of provider source
fields identifies each normalized version. Identical retrievals deduplicate; changed source fields
append a version and raw evidence. Missing publication timestamps remain explicitly `UNKNOWN`, and
partial coverage is never described as authoritative.

## ADR-014 — Content-address Reality universes and preserve per-symbol manifest failures

Status: **ACCEPTED**

Reality universes are immutable normalized snapshots derived only from retained Bitget metadata.
Their identity hashes canonical member content together with schema and transformation versions;
wall-clock generation time is separate. Historical manifests deterministically choose the first N
technically eligible members and reuse the accepted candle path. Each symbol commits its accepted
candles independently, so an isolated failure remains an explicit manifest entry while other
members continue. A manifest is Reality-side evidence, not a complete research dataset.

## ADR-015 — Profile Reality history conservatively before broad backfill

Status: **ACCEPTED — CLASSIFICATION SUPERSEDED IN PART BY ADR-018**

Historical sufficiency profiles are derived only from an accepted versioned Reality universe and a
fixed UTC evaluation window. The locked minimum is 60 total days with 30 days reserved for final
OOS validation. These are data-availability requirements, never performance thresholds or symbol
selection criteria.

Profiles reuse bounded history pagination and source-session quality semantics without persisting
another candle copy. `SOURCE_SESSION_TOO_UNKNOWN` and `UNKNOWN` are preferred to false sufficiency;
no candle is synthesized. Logical identity hashes the universe, interval, transformation, window,
and normalized member evidence while excluding generation/verification times and operational retry
noise. Pilot scope is the canonical first 10 by default; scans above 20 require an explicit full
universe switch after reviewing provider and runtime budgets.

## ADR-016 — Resolve historical source sessions from typed, effective-dated evidence

Status: **ACCEPTED**

Bitget historical source-session evidence is stored as source-level records with explicit symbol
sets, capability, session mode, effective bounds, publication time, URL, retrieval time, evidence
type, and confidence. Announcement publication time is the conservative lower bound when Bitget
says support is available “now” but gives no separate effective timestamp. No symbol state is
projected before that bound, and current `stock-info` metadata is excluded from historical
resolution.

Resolution first requires explicit scope and an effective range. Explicit suspensions outrank
schedule evidence only when their affected symbols are enumerated. Within schedule evidence,
dated symbol-addition batches outrank dated status lists, which outrank general product rules;
newer effective evidence wins within the same class. Equal-precedence evidence with different
outcomes resolves to typed `CONFLICT` and `UNKNOWN`. Ambiguous notices remain retained provenance
but cannot become wildcard closures. This policy is versioned as `bitget_source_sessions.v2`.

## ADR-017 — Audit only full-window evidence-qualified Reality histories

Status: **ACCEPTED — CLASSIFICATION SUPERSEDED IN PART BY ADR-018**

The expanded Reality coverage audit uses a machine-derived cohort, never a manually maintained
production list. Qualification requires membership in the selected persisted universe, a native
ticker mapping, explicit verified symbol evidence covering the entire locked 90-day window, and
no source-evidence conflict. Partial evidence does not qualify even when later current metadata
suggests the same session mode.

Coverage semantics classify the complete hourly grid. Known-open ratios exclude all unknown
intervals, holiday-qualified ambiguity remains explicit, and bounded starts remain left-censored.
The result reuses historical coverage persistence and is versioned as
`reality_historical_coverage.v3`. This audit does not authorize native-equity implementation,
alpha metrics, signal research, backtesting, or Phase 2 work.

## ADR-018 — Separate structural validity from coverage and chronology sufficiency

Status: **ACCEPTED**

Coverage v4 answers four independent data-plane questions: structural validity, availability
completeness, 60-day observed chronology, and deterministic final-30-day OOS feasibility. Verified
Bitget pre-start spillover is clipped and warned rather than treated as corruption. A known-open
timestamp with no returned candle remains counted, but it does not prove an outage or structural
failure. Holiday-qualified unknowns remain outside known-session denominators without invalidating
an otherwise feasible chronology.

The final OOS boundary is `evaluation_end - 30 days`; actual observations must exist before it and
within the final segment. No candle-density threshold exists because none is locked or externally
required. `SUFFICIENT_MINIMUM_HISTORY` therefore means only structurally valid Reality data meets
the duration and OOS feasibility requirements. It does not mean future research eligibility,
strategy readiness, alpha selection, or complete native-plus-Reality data.

## ADR-019 — Separate Stock+ hackathon-use approval from runtime entitlement

Status: **ACCEPTED — ACCOUNT ACCESS GATED**

Bitget directly confirmed that available Bitget stock-market data may be used for this hackathon,
so `STOCKPLUS_HACKATHON_USE` is `AVAILABLE`. This narrow determination does not imply broader
commercial display or redistribution rights.

Stock+ native-equity market data remains a runtime gate until successful signed, read-only
responses prove the user's account/API entitlement. Verification uses an isolated environment-only
script, sends no writes, persists no provider data, and stops on the first static-endpoint access
failure. No `NativeEquityProvider`, schema, migration, backfill, modeling, or research-universe
change is authorized by this decision. Raw provider values and the requested adjustment enum must
remain explicit if access is later proven.

## ADR-020 — Resolve narrow native-target rights without waiting for Stock+

Status: **NEEDS_DIRECT_PROVIDER_CONFIRMATION — NO PROVIDER SELECTED**

The 2026-09-18 [provider selection V2](NATIVE_EQUITY_PROVIDER_SELECTION_V2.md) reviews only Alpaca,
Massive and Twelve Data for historical native session targets plus public derived outputs.
Current Alpaca documentation allows historical SIP queries on Basic outside the latest 15 minutes;
this supersedes ADR-011's Basic/IEX-only technical rationale. Massive Basic now includes minute
aggregates, but its individual terms and business §6.1(j) require appropriate strategy/derived-value
licensing. Twelve Data's historical minute-feed scope and public derived-data entitlement remain
unresolved. All three are GATED for the complete SessionZero use.

Alpaca is the first provider to ask for written project-specific storage, research/backtesting,
replay and public derived-output permission, including the minimum plan and retention conditions.
It is a clarification target, not a selected adapter. No support message was sent.

WHAT changes: Stock+ access is no longer a prerequisite for investigating the external native leg.
WHY: the user reports unavailable Stock+ entitlement and an adjusted-daily-only Bitget MCP runtime.
EVIDENCE/RISK: these operational facts are user-supplied; official external documentation supports
candidate capability but not complete project clearance or verified cohort/session extraction.
PRIOR WORK affected: only the next-task sequence and earlier provider-assessment rationale change.
The accepted cohort, Reality ingestion, mapping, actions, source sessions and calendar remain intact.
Blueprint section 22 already permits an external provider, so no architecture change is adopted.
ADR-011's licensing gate remains; no implementation, target calculation, or Phase 2 is authorized.

## ADR-021 — Alpaca technical candidate for private historical cash targets

Status: **ACCEPTED FOR PRIVATE EVALUATION — BOUNDED RUNTIME VERIFIED** (2026-09-19).

WHAT: implement Alpaca behind provider-neutral `NativeEquityProvider`, with raw historical SIP
minute observations, XNYS boundary extraction, and append-only PostgreSQL provenance.
WHY: the user reports unavailable Stock+ entitlement and a Bitget MCP native surface lacking
intraday/session-specific cash data. EVIDENCE: current official Alpaca documentation supports
Basic historical SIP outside the latest 15 minutes, minute granularity, and raw adjustment;
[contract and sources](ALPACA_NATIVE_EQUITY.md). The exact accepted cohort hash and bounded authenticated runtime gate passed: three pilots,
21/21 availability, and 25/25 deterministic session rows; no full backfill.

The user's current instruction supersedes ADR-011/020's requirement to finish licensing before
private implementation. Private/local integration may proceed with rights **PROVISIONAL**; public
raw display is **NOT APPROVED**, public derived-output rights **UNVERIFIED**. No public deployment.

Use `FIRST_1M_BAR_OPEN` / `LAST_1M_BAR_CLOSE`, explicitly distinct from auction prices. A missing
boundary minute has no target. Alpaca documents separate auction data, which remains unverified;
we do not claim minute OHLC proves official auction values. This explicit observable contract
supersedes selection V2's auction-only extraction gate under the current task authorization.

PRIOR WORK: Bitget stays primary for Reality data, accepted mappings/cohort, session evidence,
corporate actions, and hackathon tooling. No alternate mapping authority or cohort replacement.
RISK: complete historical coverage, original historical availability, ticker identity history,
and rights remain unresolved. Corrections append content versions; no silent overwrite or as-known claim.
No modeling, features, returns, backtests, BOATS integration, push, or deployment is authorized.

# Historical availability and revision integrity

Decision: **RETROSPECTIVE_POINT_IN_TIME_NOT_VERIFIABLE_PROSPECTIVE_CAPTURE_READY**.

The frozen Phase 1 prices cannot be certified as an as-known dataset. Bitget's official Reality
history contract documents candle retrieval and fields but no correction policy, revision history,
historical database version, publication latency, or as-known selector. Alpaca explicitly documents
late trades that update a prior minute bar, corrected trades, and canceled/error trades. Its
historical bars endpoint returns aggregates with current query-time semantics; `asof` controls
symbol identity, not the historical database state. `adjustment=raw` prevents corporate-action
adjustment but does not freeze trade corrections. Absence of a revision field is not immutability.

Official sources reviewed on 2026-09-20:

- Bitget UTA [Market Data / historical candles](https://www.bitget.com/docs/catalog/market/market-data)
  and [Reality guide](https://www.bitget.com/docs/uta/reality-trading-guide).
- Alpaca [historical single-symbol bars](https://docs.alpaca.markets/us/reference/stockbarsingle-1),
  [real-time stock data](https://docs.alpaca.markets/us/docs/real-time-stock-pricing-data), and
  [market-data FAQ](https://docs.alpaca.markets/us/docs/market-data-faq).

## Inputs audited

| Input | Source / endpoint | Event time | Retained retrieval time | Role | Classification |
|---|---|---|---|---|---|
| Reality decision mark | Bitget `GET /api/v3/market/history-candles`, hourly close | Hour start; considered only after completion | Local ingestion plus provider `requestTime` | FEATURE | `REVISION_POLICY_UNKNOWN`, `RETROSPECTIVE_ONLY` |
| Previous native close | Alpaca `GET /v2/stocks/{symbol}/bars`, SIP/raw/1Min/asof=- | Final regular minute start | Response ingestion | FEATURE | `REVISION_POSSIBLE`, `RETROSPECTIVE_ONLY` |
| Next native open | Same Alpaca endpoint | First regular minute start | Response ingestion | FUTURE_OUTCOME | `REVISION_POSSIBLE`, `RETROSPECTIVE_ONLY` |

Revision uncertainty in `FIRST_1M_BAR_OPEN` affects label stability and reproducibility. It is not
feature lookahead because the field remains outcome-only and is structurally excluded from decision
snapshots. Revised previous closes and Reality marks are different: they can change inputs that a
historical decision purports to know, so their unversioned historical API values cannot be certified
as point-in-time features.

## Bounded runtime comparison

At `2026-09-20T21:40:17.429370Z`, six deterministic DEVELOPMENT rows were fetched again: AAPL,
NVDA and TSLA examples from each relevant endpoint. All six canonical rows were identical to the
retained Phase 1 observations. Changed, missing, new, timestamp-changed and OHLC-changed counts were
all zero. No final-OOS row or performance result was accessed. This is **OBSERVED** evidence about
six retrievals, not proof that either database is immutable or that earlier revisions never occurred.
The price-free machine record is
[availability-v1.json](../research/integrity/availability-v1.json).

## Prospective immutable capture

Migration `20260920_10` adds four PostgreSQL tables:

- `point_in_time_capture_runs` binds decision time, deployed Git commit, collector contract,
  mapping/calendar/dataset versions and the capture content version;
- `point_in_time_observation_versions` deduplicates identical canonical content and appends a new
  version when any provider value changes;
- `point_in_time_retrievals` retains every provider response, provider identifiers, request time and
  ingestion time, even when its observation version already exists;
- `decision_time_snapshots` freezes the feature versions and versioned calendar, mapping,
  source-session and capture context known by the decision timestamp.

Database triggers reject UPDATE and DELETE on all four tables. Foreign keys use `RESTRICT`.
Writes happen in one transaction. An identical refetch links new raw evidence to the existing
version; a correction has the same logical key and a different canonical/version hash. Raw provider
responses are retained as JSONB with their value strings intact. Secrets and auth headers are never
stored; Alpaca provider identifiers are restricted to safe request/date/rate-limit headers.

The collector fails unless it starts within the configured 1–30 minute pre-decision window and all
observations are ingested no later than the decision. The timestamp must equal the scheduled XNYS
open minus 60 minutes. Reality bars must be completed strictly before it. The native feature must be
the exact preceding session's final regular minute. Any symbol/provider failure aborts the atomic
snapshot; no partial snapshot is labeled safe.

One scheduler-free capture iteration for all accepted symbols is:

```bash
.venv/bin/sessionzero-capture-decision \
  --decision-timestamp 2026-09-21T12:30:00Z
```

Run `alembic upgrade head` first. The command needs `DATABASE_URL`, `ALPACA_API_KEY`, and
`ALPACA_SECRET_KEY`; Bitget remains public. A deployed image without `.git` must inject the exact
`SESSIONZERO_GIT_COMMIT`. Local execution requires a clean tree. The process has no filesystem data
dependency beyond version-controlled cohort/evidence artifacts and can run in a remote worker.
There is no scheduler, deployment, or laptop-only daemon in this task.

## Snapshot contract

`decision_snapshot.v1` includes decision timestamp, captured Reality version hashes, captured
previous-close version hashes, source-session assessments/evidence version, exact session calendar
version, frozen mapping version, prospective dataset version and raw capture version. Its hash is
deterministic and independent of insertion order. Pydantic and database constraints admit only
`REALITY_DECISION_MARK` and `PREVIOUS_NATIVE_CLOSE` with role `FEATURE`; the snapshot carries
`contains_future_outcome=false`. Next open, future actions, late retrievals and later correction
versions cannot enter an already stored snapshot.

`PROSPECTIVELY_SAFE` applies only to successfully captured snapshots under this contract. It does
not retroactively upgrade Phase 1 or the existing baseline diagnostics. A later provider revision
is preserved as evidence but cannot rewrite what the earlier snapshot knew.

## Claim policy

- **RETROSPECTIVE ESTIMATED**: current frozen baseline diagnostics. They remain useful comparative
  research but cannot be promoted to BACKTESTED point-in-time evidence.
- **PROSPECTIVE OBSERVED**: immutable responses and snapshots captured by v1. This means the record
  of what the collector observed is point-in-time safe; it does not establish alpha.
- **BACKTESTED**: reserved for evaluation on enough prospectively captured, immutable decisions and
  later outcome versions under a separately frozen experiment. No current metric has this label.

The acceptance decision is B because the retrospective defect is documentary and irrecoverable
from today's API response alone, while the prospective capture contract is implemented, tested,
append-only and remotely runnable. Final OOS remains untouched by strategy-performance evaluation.

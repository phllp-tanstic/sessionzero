# Architecture Decision Records

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

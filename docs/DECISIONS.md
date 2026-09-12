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


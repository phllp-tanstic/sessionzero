# Security and Data Integrity

## Phase 0 controls

- Public Bitget endpoints only; no API key, private account, OAuth, trading, or orders.
- Agentic Account status: **PLANNED — NOT AUTHORIZED**.
- Secrets are excluded by `.gitignore`; `.env.example` contains names and non-secret defaults only.
- Provider requests have explicit total timeouts and bounded retry counts.
- External responses pass envelope and model validation before use.
- Provider failures fail closed with structured errors; there is no fixture or generated-data
  fallback.
- Reality depth and platform fills are explicitly `GATED`; no emulation exists.
- CORS uses an exact configurable allowlist and rejects wildcard configuration.
- Production API docs are disabled.

## Data rules

Decimal values are not converted through binary floating point. UTC is mandatory. Missing volume
or turnover stays `null`, distinct from numeric zero. Test fixtures are labeled and located only
under `tests/fixtures`; production packages do not import that path.

## Outstanding

Dependency auditing, rate limiting, database controls, log redaction infrastructure, persisted
audit trails, and deployment security are later-phase work. No deployment exists in Phase 0.


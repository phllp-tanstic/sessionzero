# Security and Data Integrity

## Current controls

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
- `DATABASE_URL` is environment-only and never logged by database error handling.
- Only PostgreSQL URLs using psycopg are accepted; missing configuration and failed connections
  fail explicitly with no SQLite or in-memory fallback.
- Alembic, rather than application startup, controls schema changes.
- Foreign keys, check constraints, and database uniqueness enforce core integrity independently of
  application duplicate checks.

## Data rules

Decimal values are not converted through binary floating point. UTC is mandatory. Missing volume
or turnover stays `null`, distinct from numeric zero. Test fixtures are labeled and located only
under `tests/fixtures`; production packages do not import that path.

## Outstanding

Managed-database TLS, least-privilege roles, backup/restore drills, retention, rate limiting,
central log redaction, and deployment security remain later work. The local verification database
is disposable and trust-authenticated on loopback only. No deployment exists.

# Security and Data Integrity

Bitget reference ingestion uses documented public endpoints only and sends no API key, signature,
account identifier, or order request. `--persist` requires only `DATABASE_URL`; default CLI use is
read-only. Technical access does not grant display, redistribution, or quantitative-use rights.

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
- Native-equity provider credentials are absent. Provider selection fails closed until secrets are
  environment-managed and the account's non-display, derived-work, public-display, and
  redistribution permissions are documented. A free/developer plan is not assumed to grant them.

## Data rules

Decimal values are not converted through binary floating point. UTC is mandatory. Missing volume
or turnover stays `null`, distinct from numeric zero. Test fixtures are labeled and located only
under `tests/fixtures`; production packages do not import that path.

## Outstanding

Managed-database TLS, least-privilege roles, backup/restore drills, retention, rate limiting,
central log redaction, and deployment security remain later work. The local verification database
is disposable and trust-authenticated on loopback only. Native-equity vendor contracting and
exchange entitlements are unresolved. No deployment exists.

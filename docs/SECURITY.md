# Security and Data Integrity

## Phase 1 dataset retention and recovery

The authorized full backfill stores private source archives under ignored `.local-data/phase1/`.
Archive files use mode 0600; collection directories use mode 0700. Tracked `datasets/phase1/`
artifacts contain membership, schedules, content hashes, quality counts, and provenance metadata,
not raw prices or credential values. Keep private archives with any authorized backup or machine
migration; Git alone intentionally does not distribute licensed observations.

Offline restore verifies file checksums, accepted mapping/cohort identity, pinned calendar and
source-code identity, and raw-to-normalized native replay before publishing dataset linkage. It
needs only `DATABASE_URL`, not Alpaca credentials. A separate empty-database restore drill passed.
Database URLs and provider exception bodies are suppressed in CLI errors. No brokerage endpoints,
public prices, deployment, or remote upload was added. Private retention/research remains subject
to the existing provisional rights status; public raw display remains unapproved.

## Alpaca private/local evaluation — current authorization

The current task authorizes authenticated read-only Alpaca market-data requests using only
`ALPACA_API_KEY` / `ALPACA_SECRET_KEY` from the environment. This supersedes the older
public-endpoints-only implementation description below; it does not authorize brokerage access.
Credentials are never logged, written into fixtures, or persisted in provenance. Response headers
are allowlisted and provider error bodies are not exposed. Local raw reports use mode 0600 and
must remain ignored artifacts; no native price is returned by a public API. See
[contract and limitations](ALPACA_NATIVE_EQUITY.md).

Private research is provisional pending rights confirmation. Raw public display is not approved;
public derived outputs remain unverified. No deployment or public output is authorized. There is
no configurable switch purporting to grant those rights.

Bitget reference ingestion uses documented public endpoints only and sends no API key, signature,
account identifier, or order request. `--persist` requires only `DATABASE_URL`; default CLI use is
read-only. Technical access does not grant display, redistribution, or quantitative-use rights.

## Current controls

- Bitget production ingestion uses public endpoints; native Alpaca ingestion uses authenticated
  read-only market data. No private account, OAuth, trading, or orders are called.
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
- Native-equity credentials are environment-only and remain excluded from all reports.
  The isolated Stock+ verifier reads the Bitget key,
  secret, and passphrase from environment variables only, never prints headers/signatures, sends
  signed GET requests only, persists nothing, and stops on its first static-endpoint access error.
  Bitget has authorized available stock-market data for this hackathon; broader public display and
  redistribution rights remain unproven and are not inferred from that determination.

## Data rules

Decimal values are not converted through binary floating point. UTC is mandatory. Missing volume
or turnover stays `null`, distinct from numeric zero. Test fixtures are labeled and located only
under `tests/fixtures`; production packages do not import that path.

## Outstanding

Managed-database TLS, least-privilege roles, off-machine backup operations, retention policy,
central log redaction, and deployment security remain later work. The local verification database
is disposable and trust-authenticated on loopback only. Native-equity vendor contracting and
exchange entitlements are unresolved. No deployment exists.

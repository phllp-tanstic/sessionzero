# Remote prospective worker deployment

Status: **IMPLEMENTED LOCALLY; NOT DEPLOYED**. No Railway project, managed database, scheduler,
service URL or first prospective snapshot exists yet. Deployment and secret provisioning require
separate authorization. Do not run old decision timestamps or insert a synthetic success.

## Target and costs

The blueprint suggests Railway or an equivalent persistent container service for Python workers
and managed PostgreSQL. This implementation targets a Railway cron service built from
`Dockerfile.worker`, connected over private networking to a persistent PostgreSQL service. It
does not require a public worker URL or the user's laptop. Railway's
[cron documentation](https://docs.railway.com/cron-jobs) says jobs are short lived, UTC scheduled, at least five
minutes apart, and may start a few minutes late. The internal XNYS calendar, not cron, determines
the exact decision and outcome timestamps. Railway's
[PostgreSQL documentation](https://docs.railway.com/databases/postgresql) recommends backups and monitoring; enable both.
Railway [pricing](https://railway.com/pricing) is usage based, with a Hobby minimum of $5/month and
additional resource usage as applicable. Database storage, backups, memory and networking add
cost; measure the actual bill before scaling.

The target changes only operations: existing Bitget, Alpaca, calendar, accepted cohort, immutable
capture tables and baseline research remain intact. The deployment introduces one cron container,
one managed PostgreSQL service and append-only worker/outcome tables. Public raw Alpaca data
routes are not added.

## Service configuration after authorization

1. Provision managed PostgreSQL with durable storage, backups, and a private connection. Create
   the worker service from the repository root using `Dockerfile.worker` (one replica, no public
   domain). Pin the deployed Git commit as `SESSIONZERO_GIT_COMMIT`.
2. Put `DATABASE_URL` (psycopg PostgreSQL URL), `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`,
   `NATIVE_EQUITY_PROVIDER=alpaca`, and `SESSIONZERO_ENV=production` in the service's environment
   secret store. Bitget historical candles are public for this path. Never put secret values in a
   build argument, Git, log, URL, or command line. Restrict database access to the private network.
3. Run `alembic upgrade head` once as a controlled migration job before enabling the cron. Verify
   `alembic current` is `20260921_11`; the worker does not create schema at runtime. Test the
   container's `sessionzero-prospective-worker status` command against that database.
4. Configure Railway's cron schedule as `*/5 12-14 * * 1-5` (UTC) with start command
   `sessionzero-prospective-worker tick`, restart policy `NEVER`, and a runtime budget that permits
   all 21 paired requests. The cron can wake on exchange holidays; `session_on(local_date)` skips
   them without provider requests. This cadence covers summer 12:30/13:47 UTC and winter
   13:30/14:47 UTC decision/outcome readiness, with 15-minute pre-decision collection and a
   17-minute post-open SIP embargo buffer. The provider clients have bounded retries.
5. Review logs and `sessionzero-prospective-worker status` after deployment. Alert if no run has
   occurred within 20 minutes during the UTC schedule, on any failure or missed decision, and if
   an expected session's outcome remains unlinked. A skipped Railway cron while an earlier
   invocation remains active may cause a missed snapshot; it must stay missed, never backfilled.

There is no deploy script that implicitly creates accounts, buys service capacity, grants vendor
rights, or provisions secrets. Railway's deprecated `railway.toml` config-as-code is not used for
new services; the service settings above are the deployment contract. The current official
[configuration guidance](https://docs.railway.com/config-as-code) recommends the newer
Infrastructure as Code surface if this topology is later managed declaratively.

## Calendar and run behavior

Each invocation checks the frozen 21-member cohort/evidence identity, including original
`universe_version`, `cohort_version` and accepted mapping. The calendar computes the scheduled
open and decision exactly 60 minutes before it. Before the 15-minute collection window it skips.
Within the window it reuses `capture_iteration`; after the decision, a missing snapshot records
`MISSED_DECISION_WINDOW`. A snapshot already present prevents another decision provider call.
After open plus 17 minutes the separate outcome collector fetches exact SIP/raw first-minute
opens and appends versions/links without changing the snapshot.

Every invocation writes a structured worker row with scheduled event, actual start/completion,
lateness, status, symbol counts, provider degradation, snapshot and outcome-link counts. The
`status` command reports the latest run, stale flag, migration head, latest snapshot and outcome
link count; it contains no raw prices or credentials. If PostgreSQL is unavailable, a redacted
`DATABASE_FAILURE` line is emitted but cannot be durably recorded until PostgreSQL returns.

## First remote verification

After an authorized deployment, verify the running deployment/service identifier, private
PostgreSQL connectivity, migration head, accepted cohort hashes, cron settings, and executable
worker command. No valid decision window should be simulated. At the next legitimate session,
confirm one immutable decision snapshot with 21 paired features, then 21 append-only outcome
links after the open. A failure is an explicit operational state and does not become a successful
prospective observation retroactively.

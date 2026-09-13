# Handover

## Current phase

`PHASE 1 — DATA PLANE (POINT-IN-TIME MARKET SESSION SEMANTICS)`

## Completed

- Accepted bounded Bitget ingestion and PostgreSQL persistence remain compatible.
- Separate `TradingCalendarProvider` and `SourceSessionProvider` protocols prevent cash-market
  schedules from being mistaken for source availability.
- Pinned `exchange-calendars==4.13.2` supplies XNYS DST, holiday, early-close, and adjacent-session
  semantics in UTC.
- Version-controlled Bitget capability records carry effective bounds and source provenance.
- Gap quality now distinguishes expected source closure, missing while expected open, and unknown
  source availability without synthesizing observations.
- Typed `SessionZeroContext` produces only temporal `ACTIVE`/`INACTIVE`/`UNKNOWN` primitives.

## Verified

- Final session-aware live verification completed at `2026-09-12T22:55:23Z`.
- NYSE and Nasdaq official 2026 calendars confirm Juneteenth closure, 9:30–16:00 Eastern regular
  hours, and November 27/December 24 early closes.
- XNYS tests verify normal days, weekends, Juneteenth, early close, previous/next boundaries, and
  the March 2026 DST shift.
- RAAL's June window remains 216/336 observations; all 120 absences are now explicit source-session
  unknowns because cited RAAL eligibility does not cover those timestamps.
- Official Bitget evidence places `RMRNAUSDT` in a 24/7 rollout on `2026-07-17 03:40`. Its tested
  July 18–20 weekend had 2 in-range candles, 46 missing-while-open intervals, and quality `FAIL`.
- Follow-up verification on `2026-09-13` used exact, end-only, adjacent-day, nearby control,
  page-size, and millisecond-alignment probes. It confirmed that sparse two-boundary requests can
  backfill earlier records instead of applying `startTime` as a strict response filter.
- Independent read-only `bgc` output reproduced all 48 exact-window RMRNA provider rows.
- A live `page_limit=1` adapter run reached both in-range candles in three backward pages and
  clipped one older row, confirming that the SessionZero pagination cursor is correct.

## Failed

- The RMRNA comparison still fails quality because Bitget history contains only two candle records
  in the verified-open two-day window. This is a confirmed provider-history gap, not a proven feed
  outage, and no SessionZero pagination defect was found.

## Outstanding

- Native-equity price/reference data, broader historical capability coverage, backfills, continuous
  collection/scheduling, cross-asset/event providers, models, backtesting, API expansion, and UI.

## Known constraints

- Curated source history includes only one general 24/5 publication and one evidenced RMRNA 24/7
  rollout; unproven symbols/times remain unknown.
- General 24/5 evidence does not enumerate all exceptions. Holidays and generic-symbol weekends
  remain unknown unless symbol-specific evidence establishes availability.
- Exchange calendars encode scheduled sessions, not unscheduled halts or source outages.
- Bitget does not document the observed sparse-window `startTime` backfill behavior or explain why
  individual expected-open intervals have no candle record. The missing records' cause is unknown.
- Full quality reports are emitted by the command but only their summary fields are stored on the
  ingestion run.
- `FAIL` datasets are rejected before the raw/normalized transaction; their machine report is not
  durably stored in this slice.
- No native-equity price adapter, daemon, scheduler, managed database, or deployment exists.

## Current services

- Existing FastAPI and Next.js surfaces are unchanged.
- One-shot CLI: `sessionzero-ingest-bitget-history`.
- Migration CLI: `alembic upgrade head`.

## Required env vars

- `DATABASE_URL`: required for migrations, persistence, and PostgreSQL tests.
- Existing public Bitget and web/API settings remain in `.env.example`.

## Test counts

- 55 deterministic non-live/non-PostgreSQL tests.
- 7 direct PostgreSQL integration tests.
- 2 opt-in live Bitget tests.

## Deployment URLs

`NOT DEPLOYED`

## Latest commit

`docs(data): record Bitget sparse history verification` (this handover's commit).

## Next exact task

Add a point-in-time native-equity historical price provider behind the existing provider boundary.

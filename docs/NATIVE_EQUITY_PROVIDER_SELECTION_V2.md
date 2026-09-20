# Native equity target provider selection V2

Review date: **2026-09-18 UTC**. Phase: **1 — DATA PLANE**.
Decision: **C. NEEDS_DIRECT_PROVIDER_CONFIRMATION**. First contact: **Alpaca**.
This is documentation research, not provider implementation or a verified native dataset.

## 1. Requirement Restatement

Obtain legitimate native U.S. equity historical regular-session closes and next opens for the
unchanged accepted 21-member cohort. Preserve the accepted Reality window
`[2026-06-15T20:00:00Z, 2026-09-13T20:00:00Z)` and final OOS feasibility boundary
`2026-08-14T20:00:00Z`. Fetching a preceding close or following open may eventually require native
observations just outside that window; it must not change the Reality cohort/window.

Required rights cover private observation storage, quantitative research, backtesting, historical
replay, and public SessionZero Fair Value, Discovery State, Discovery Confidence, Gap, and
Conviction. Public raw prices are optional. Real-time subscriptions, order books, brokerage,
execution, and broad platform capabilities are unnecessary for this decision.

Repository basis: blueprint sections 5, 13, 15, 16, 22; ADR-004/010/011/018; HANDOVER's coverage-v4
result. The user's current report supersedes the old instruction to wait for Stock+ credentials:
Stock+ is operationally gated and Bitget MCP supplies adjusted daily bars only. These are supplied
task facts, not runtime results independently reproduced during this review.

The retained source evidence enumerates the 21 Reality symbols under
`bitget.2026-06-12.weekend-batch-21`. No provider's full 21-native-ticker/date coverage was tested.
The persisted accepted universe mapping remains authoritative; stripping Reality prefixes is not
an acceptable replacement. Broad U.S.-coverage claims below establish candidate capability, not
verified coverage of every member, listing history, or session boundary.

## 2. Providers Evaluated

**Alpaca, Massive, Twelve Data only.** No fourth candidate was necessary to identify the immediate
licensing question. Polygon is not counted again as a separate provider. No account was opened,
subscription purchased, credentials inspected, support message sent, or market dataset downloaded.

## 3. Official Sources Reviewed

All links below were retrieved/reviewed on **2026-09-18 UTC**. Only provider-owned documentation,
legal documents, pricing, and support material support hard claims. Dates within documents are
not retrieval dates. Unverified fields remain explicit rather than inferred from marketing.

| Provider | Official sources | Purpose / qualification |
|---|---|---|
| Alpaca | [Plans/authentication](https://docs.alpaca.markets/us/docs/about-market-data-api), [market-data FAQ](https://docs.alpaca.markets/us/docs/market-data-faq), [historical bars](https://docs.alpaca.markets/us/reference/stockbars) | Prices, limits, historical SIP access, timestamps, adjustments, symbol mapping |
| Alpaca | [Asset identifiers](https://docs.alpaca.markets/us/reference/get-v2-assets-symbol_or_asset_id), [corporate actions](https://docs.alpaca.markets/us/reference/corporateactions-1), [stream updates](https://docs.alpaca.markets/us/docs/real-time-stock-pricing-data), [minute-bar explanation](https://alpaca.markets/learn/stock-minute-bars) | Identity, action availability, corrections; older explanation conflicts with current FAQ on timestamp basis |
| Alpaca | [Terms and Conditions](https://files.alpaca.markets/disclosures/library/TermsAndConditions.pdf), [current customer agreement](https://files.alpaca.markets/disclosures/library/AcctAppMarginAndCustAgmt.pdf) | Personal/application restrictions; customer PDF footer identifies V26.2026.07 |
| Massive | [Individual pricing](https://massive.com/pricing), [business stocks](https://massive.com/business-stocks), [stock overview](https://massive.com/docs/rest/stocks/overview), [custom bars](https://massive.com/docs/rest/stocks/aggregates/custom-bars) | Historical consolidated coverage, plan access, bar contract |
| Massive | [Ticker details](https://massive.com/docs/rest/stocks/tickers/ticker-overview), [splits](https://massive.com/docs/rest/stocks/corporate-actions/splits), [canceled trades](https://massive.com/knowledge-base/article/how-much-does-massives-feeds-handle-canceled-trades), [late aggregates](https://massive.com/knowledge-base/article/why-am-i-receiving-a-late-aggregate-bar-through-massives-websockets) | Identity, actions, revisions |
| Massive | [Terms routing](https://massive.com/legal/terms), [individual terms](https://massive.com/legal/individuals-terms-of-service), [market-data terms](https://massive.com/legal/market-data-terms-of-service), [business terms](https://massive.com/legal/businesses-terms-of-service) | Individual terms dated July 18, 2025; market-data terms August 28, 2025; business terms September 2, 2025 |
| Twelve Data | [Individual pricing](https://twelvedata.com/pricing), [business pricing](https://twelvedata.com/pricing-business), [March pricing update](https://twelvedata.com/news/march-2026-updates) | Business pricing full-page fetch failed; official indexed excerpts show different Venture configurations, so exact minimum is unresolved |
| Twelve Data | [API documentation](https://twelvedata.com/docs), [history](https://support.twelvedata.com/en/articles/5656039-how-to-get-historical-prices), [timezones](https://support.twelvedata.com/en/articles/5745849-timezones), [adjustments](https://support.twelvedata.com/en/articles/5179064-are-the-prices-adjusted), [extended hours](https://support.twelvedata.com/en/articles/5195429-pre-post-market-data) | Main API page exceeded browser extraction size; parameter details checked through official indexed documentation and support pages |
| Twelve Data | [U.S. feed/licensing](https://support.twelvedata.com/en/articles/9935903-us-equities-market-data), [terms](https://twelvedata.com/terms) | Feed article dated August 18, 2026; historical coverage and contract distinctions |

## 4. Technical Capability Matrix

Documented capability only; exact cohort coverage and boundary extraction remain unverified.

| Provider | Technical capability | Granularity / history | Timestamp / identity | Limits / authentication |
|---|---|---|---|---|
| Alpaca | Historical U.S. stocks/ETFs, SIP bars and historical trade surface; likely fit subject to boundary validation | 1-minute and 5-minute OHLC; since 2016, subject to instrument existence | RFC-3339; asset UUID plus ticker; date-based `asof` symbol mapping | Basic 200 requests/minute; Plus 10,000/minute; 10,000 bars/page across symbols; key/secret headers |
| Massive | Consolidated native stock history, custom aggregates; raw trades on entitled tiers | Minute/custom OHLC; Basic 2 years, Starter 5, Developer 10, Advanced 20+ | Unix milliseconds at bar start; dated ticker metadata, composite/share-class FIGI | Basic 5 calls/minute; paid unlimited advertised; 50,000 base aggregates/query; API key |
| Twelve Data | Historical U.S. OHLC; exact minute-feed consolidation and boundary rules unresolved | 1-minute/5-minute; minute archive starts 2020-02-10, individual depth varies | Configurable IANA timezone; ticker + exchange/MIC; FIGI higher-tier access | Basic 8 credits/minute, 800/day; Grow starts 55/minute; time-series weight 1/symbol, 5,000 output-size limit; API key |

Sources: [Alpaca plans](https://docs.alpaca.markets/us/docs/about-market-data-api),
[bars](https://docs.alpaca.markets/us/reference/stockbars),
[Massive bars](https://massive.com/docs/rest/stocks/aggregates/custom-bars),
[ticker identity](https://massive.com/docs/rest/stocks/tickers/ticker-overview),
[Twelve history](https://support.twelvedata.com/en/articles/5656039-how-to-get-historical-prices),
[pricing](https://twelvedata.com/pricing), [API](https://twelvedata.com/docs).

Stable identity does not mean a ticker never changes. Each eventual mapping must bind the accepted
native security, provider identifier, listing venue, and effective dates. Availability of an
identifier endpoint does not prove complete historical identity for this cohort.

## 5. Usage-Rights Matrix

These classifications concern the complete SessionZero use, not hypothetical personal experiments.

| Provider | Private storage | Quant research / backtesting / replay | Public derived outputs | Public raw reference prices |
|---|---|---|---|---|
| Alpaca | Project retention and post-cancellation rights unresolved | Personal use framework exists; project-specific non-display rights require confirmation | No explicit clearance for this public product | Written consent / applicable data agreements required |
| Massive individual | Restricted use; market-data §8 requires deletion on termination/restriction/suspension | §5(d) requires a license for non-display/strategy uses | §5(c)-(d) restrict analytics/derived works | Not permitted by ordinary individual access |
| Massive business | §2.2 explicitly allows storage, subject to agreements | Business product advertises backtesting; §6.1(j) still requires licensing for strategies/indicative values | Require order-form/third-party scope to cover the named outputs | Edge-user access exists within contractual scope; not an unrestricted redistribution grant |
| Twelve Data | Internal storage granted, documentation time limits apply; deletion at termination | Tier-dependent non-display permission | Irreversible derived-data creation/ownership allowed; external publication and financial-product boundary unresolved | Eligible business display entitlement/add-on or written agreement; exchange conditions apply |

Massive's individual restriction is explicit, not merely missing permission. Its business route is
real, but buying a business subscription does not by itself resolve §6.1(j).
[Market-data terms](https://massive.com/legal/market-data-terms-of-service),
[business terms §§2.2, 6.1](https://massive.com/legal/businesses-terms-of-service).

Alpaca's Terms require advance notice for a user application and separate written consent for
publication/commercial reuse. Notification alone is not equivalent to consent. The customer
agreement also restricts reproduction, distribution and commercial exploitation. Neither reviewed
document expressly clears this derived-only hackathon use or indefinite research retention.
[Terms](https://files.alpaca.markets/disclosures/library/TermsAndConditions.pdf),
[customer agreement p.16](https://files.alpaca.markets/disclosures/library/AcctAppMarginAndCustAgmt.pdf).

Twelve Data §§2.1–2.4, 6.2 and 12.5 distinguish internal use, irreversible derived data, external
display, and termination. A right to create/own derived data is not an unambiguous public-product
license. Its feed support article describes paid commercial/non-display use more broadly than
individual pricing; the exact applicable tier must be confirmed.
[Terms](https://twelvedata.com/terms),
[feed/licensing support](https://support.twelvedata.com/en/articles/9935903-us-equities-market-data).

## 6. Feed Authority Analysis

| Surface | Authority classification | Decision implication |
|---|---|---|
| Alpaca `feed=sip` historical | **AUTHORITATIVE_ENOUGH**, conditional on target extraction | CTA/UTP consolidated source; plausible cash-market reference |
| Alpaca `feed=iex` | **LIMITED_BUT_POTENTIALLY_USABLE** | Supplemental validation only; not cleared for the locked authoritative target |
| Massive consolidated historical data | **AUTHORITATIVE_ENOUGH**, conditional on target extraction | Use actual historical trades/aggregates, not Massive's proprietary real-time Fair Market Value |
| Twelve default real-time feed | **LIMITED_BUT_POTENTIALLY_USABLE** | Approximately 5% of volume; listed-symbol breadth is not consolidated venue coverage |
| Twelve historical minute feed | **UNKNOWN** for exact required surface | Support says historical/EOD covers all volume; wording also calls it a daily view. Confirm this applies to 1-minute history and identify consolidation/auction rules |

The important Alpaca correction: **Basic is not restricted to IEX for old historical queries**.
The FAQ explicitly permits historical SIP when `end` is at least 15 minutes old. Set `feed=sip`
explicitly; defaults are subscription-dependent. No real-time upgrade is technically necessary
for June–September history. [Alpaca FAQ](https://docs.alpaca.markets/us/docs/market-data-faq).

Twelve's historical claim must also be preserved: it would be wrong to apply its 5% real-time
limitation automatically to all historical data. [U.S. feed documentation](https://support.twelvedata.com/en/articles/9935903-us-equities-market-data).

**Boundary correctness:** XNYS remains the schedule, not a claim that every security lists on
NYSE. Opening/closing auctions depend on the native listing venue. The 09:30 bar's open is the
first qualifying trade in that minute. The 15:59 bar's close excludes a trade timestamped exactly
16:00; the 16:00 bar can also contain post-market activity. Neither is automatically the official
closing price. Five-minute bars do not fix this. Validate condition-coded native opening/closing
prints or a documented official session-price field; otherwise fail the target, rather than
silently substitute a proxy. This is an inference from aggregation semantics, not a live test.
[Alpaca aggregation rules](https://docs.alpaca.markets/us/docs/market-data-faq),
[Massive aggregate contract](https://massive.com/docs/rest/stocks/aggregates/custom-bars).

## 7. Point-in-Time / Adjustment Analysis

| Provider | Raw / adjustments | Revisions / actions | PIT consequence |
|---|---|---|---|
| Alpaca | Explicit `adjustment=raw`; separate split, dividend, spin-off, all modes | Late trades can update bars. Corporate-action creation/publication availability is not guaranteed; `asof` is symbol mapping, not a historical database vintage | Raw target candidates are viable; historical first-availability remains unproven |
| Massive | Explicit `adjusted=false`; default split-adjusted, not a dividend-total-return switch | Canceled trades can revise EOD aggregates; splits expose execution dates/factors, not proof of when SessionZero knew them | Preserve raw values and append revisions; do not use today's cumulative factor as past knowledge |
| Twelve Data | Support says intraday unadjusted; API advertises none/splits/dividends/all | No comprehensive correction/version-history policy found; action publication/availability semantics unverified | Verify explicit `adjust=none` behavior; no claim of historical as-known snapshots |

Sources: [Alpaca bar parameters](https://docs.alpaca.markets/us/reference/stockbars),
[late updates](https://docs.alpaca.markets/us/docs/real-time-stock-pricing-data),
[action warning](https://docs.alpaca.markets/us/reference/corporateactions-1),
[Massive split contract](https://massive.com/docs/rest/stocks/corporate-actions/splits),
[cancellations](https://massive.com/knowledge-base/article/how-much-does-massives-feeds-handle-canceled-trades),
[Twelve adjustment support](https://support.twelvedata.com/en/articles/5179064-are-the-prices-adjusted).

None of the reviewed bar contracts proves a historical database vintage available at prediction
time. Client UTC retrieval time must be recorded; an event timestamp, request ID, or HTTP response
date does not supply the original publication time. Raw prices prevent corporate-action
restatement, but do not prevent corrections.

For eventual research, version raw responses, request parameters, feed, mapping, retrieval times,
and transformations. Treat subsequently observed next opens as outcome labels only. A previous
close used as a feature needs an availability policy; a corrected value downloaded today cannot
be called what the system knew in June. The 15-minute SIP embargo also belongs in replay timing.
Cross-split returns need a separately documented, point-in-time corporate-action treatment; this
review neither adjusts prices nor computes targets.

Alpaca's older minute-bar article uses participant timestamps, while the current FAQ says SIP
timestamps. The discrepancy requires a boundary contract check and prevents claiming exact auction
reconstruction from documentation alone.
[Older explanation](https://alpaca.markets/learn/stock-minute-bars).

## 8. Cost / Access Analysis

**ESTIMATED workload:** 21 × approximately 63 sessions × 390 minutes ≈ **516,000 rows**.
This is planning arithmetic, not an audited calendar count or observed dataset. Fetching all
extended hours could increase it to roughly 1.27 million rows. Boundary-only retrieval is smaller.
There is no throughput reason to buy real-time data for this historical task.

| Provider | Minimum technical access | Practical cost for the complete authorized use | Access friction |
|---|---|---|---|
| Alpaca | Basic **$0**, historical SIP older than 15 minutes; Plus **$99/month** unnecessary here | **Unknown pending written permission/quote**; $0 data access is not a cleared product license | Account/API keys, applicable jurisdiction/subscriber terms, project license clarification |
| Massive | Basic **$0**, now explicitly includes minute aggregates; Starter **$29/month** improves rate/depth | Published Stocks Business **$2,499/month**, plus any specifically required license; narrow historical quote may differ | Self-service key insufficient; written strategy/derived-value scope required |
| Twelve Data | Basic **$0** for technical evaluation; Grow **$79/month** listed for individuals | Business Venture page shows **from $149/month** and a **$499/month** configuration; exact historical/derived-only entitlement and add-ons **unquoted** | Tier selection, feed confirmation, retention/display scope |

Sources: [Alpaca plans](https://docs.alpaca.markets/us/docs/about-market-data-api),
[Massive pricing](https://massive.com/pricing), [business pricing](https://massive.com/business-stocks),
[Twelve individual pricing](https://twelvedata.com/pricing),
[business pricing](https://twelvedata.com/pricing-business).

At maximum page sizes, approximately 52 Alpaca pages or 105 Twelve symbol-pages could carry the
regular-session rows, before metadata, retries, and boundary checks. Massive's 50,000-base-bar
ceiling implies at least one request per symbol and more if extended hours exceed that ceiling.
Even Basic rates are practical. Costs above exclude tax. No post-cancellation retention is assumed,
so a one-month download is not presented as a permanent licensed archive.

## 9. Provider-by-Provider Findings

**Alpaca:** Best first clarification target. Technical sufficiency is plausible with Basic SIP;
data authority is adequate at the feed level; usage rights remain gated. IEX alone is not cleared.
The V1 assertion that Basic necessarily forces IEX history is superseded. A $99 upgrade would not
resolve the public-product license. [Historical SIP rule](https://docs.alpaca.markets/us/docs/market-data-faq).

**Massive:** Strong technical candidate, not rejected as a provider. Its individual product terms
expressly limit the audience/use, and market-data terms restrict non-display and derived works.
Business grants allow application processing/storage but §6.1(j) retains a license requirement for
investment strategies and indicative values. Private backtesting and public Fair Value therefore
need an applicable grant, not reliance on advertised use cases. [Individual terms](https://massive.com/legal/individuals-terms-of-service),
[business terms](https://massive.com/legal/businesses-terms-of-service).

**Twelve Data:** Viable history candidate with unusually explicit irreversible-derived-data
language. It is not yet cleared because creation rights, public publication, permitted retention,
and the exact historical minute feed are distinct questions. Do not require a paid split endpoint
merely to download raw target prices; authoritative action handling remains a later integrity gate.
[Terms](https://twelvedata.com/terms), [adjustment support](https://support.twelvedata.com/en/articles/5179064-are-the-prices-adjusted).

## 10. Final Decision

**C. NEEDS_DIRECT_PROVIDER_CONFIRMATION.** No provider is selected or authorized for implementation.

The following complete decision matrix describes SessionZero readiness, not generic API uptime.

| Provider | Technical capability | Granularity | Historical depth | Feed authority | Point-in-time safety | Private storage | Backtesting rights | Derived-output rights | Public raw display rights | Minimum practical cost | Access friction | Overall status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Alpaca Basic historical SIP | Documented candidate; cohort/boundaries unverified | 1m/5m + trades | Since 2016 | AUTHORITATIVE_ENOUGH, extraction conditional | Raw supported; revisions/availability unresolved | Confirm project retention | Confirm project scope | Confirm public use | Consent required | $0 technical; licensed total unknown | Account + written scope | **GATED** |
| Massive | Strong documented candidate; cohort/boundaries unverified | Minute/custom; trades by tier | 2–20+ years by tier | AUTHORITATIVE_ENOUGH, extraction conditional | Raw supported; revised history | Business grant conditional | Explicit license needed | Explicit license needed | Contract-specific | $0 technical; Business $2,499/month before scoped license | Business/order-form review | **GATED** |
| Twelve Data | Candidate; minute-feed/boundaries unverified | 1m/5m | Minute archive from 2020; varies | UNKNOWN for required historical minute surface | Raw intraday; corrections unknown | Conditional; termination deletion | Tier-dependent | Creation allowed; publication unresolved | Business entitlement/add-on | $0 technical; Venture $149–$499 configurations, total unknown | Feed + tier + rights clarification | **GATED** |

The single next action is a written **Alpaca licensing clarification**, requesting the minimum
appropriate plan. Prioritize legal usability and exact feed semantics before price. This is a
choice of contact, not a provider selection disguised as clearance.

## 11. Blueprint Impact

**WHAT:** End the mandatory wait for Stock+; investigate an external provider only for native
session targets. No architecture or target change is adopted.

**WHY:** User-reported Stock+ entitlement remains inaccessible and the exposed Bitget MCP daily
adjusted surface cannot satisfy this session-aware target requirement.

**EVIDENCE / RISK:** Current official documents support historical alternatives; none establishes
the complete project's entitlement plus exact cohort/boundary/PIT correctness. ADR-011's gate
remains, while its Basic-IEX-only rationale is corrected.

**PRIOR WORK:** Reality ingestion, accepted 21-member cohort, chronology/OOS feasibility, mapping,
corporate actions, source sessions, calendar, persistence, and supplemental Bitget data remain
useful and unchanged. Bitget's hackathon permission is not transferred to third-party contracts.
Blueprint section 22 already accommodates an external `NativeEquityProvider`; no blueprint rewrite
is needed. Phase 2 remains blocked.

## 12. Risks / Unknowns

- No live native data or all-21 coverage proof; verify the accepted mappings, including any ETF,
  ADR, renamed, or recently listed member, without dropping inconvenient symbols.
- No guarantee that minute boundary OHLC equals the required official opening/closing print.
- Historical corrections and original availability are not solved merely by choosing raw prices.
- Public Fair Value/Gap combinations may expose or allow recovery of inputs; “derived” is not
  automatically irreversible or exempt. Any public replay actual-open field would be raw display.
- Exact retention after cancellation, commercial classification, and exchange obligations need
  applicable written terms. No residency eligibility is inferred from the workstation timezone.
- Twelve's price configurations and historical minute-feed scope require clarification; its broad
  historical 100%-volume statement must not be omitted or overextended.
- No provider correction SLA or complete point-in-time corporate-action master was established.

## 13. Exact Next Task

Submit this single question to Alpaca support/licensing and retain the written answer and applicable
terms before any implementation. **Draft only; not sent.**

> Which minimum plan/agreement permits SessionZero to retain 90 days of historical SIP data for
> 21 U.S. tickers for private quantitative research, backtesting and replay, and publicly display
> derived Fair Value, State, Confidence, Gap and Conviction in a hackathon app without raw prices,
> including any retention limits or exchange fees?

The eventual technical gate must still validate the accepted cohort and exact native session
prices; a licensing reply is not evidence of successful historical retrieval. No Bitget reply is
required to progress this clarification.

## 14. Git Status

Starting tree: clean; `main` ahead of `origin/main` by one commit.
Existing HEAD: `61f54bb feat(data): add Stock+ access verifier`.

This task changes documentation only: this report, `docs/HANDOVER.md`, `docs/DATA.md`, and
`docs/DECISIONS.md`. No tests added or run because no executable behavior changes. Validation:
`git diff --check`, documentation review, and final Git status. No commit, push, or deployment.

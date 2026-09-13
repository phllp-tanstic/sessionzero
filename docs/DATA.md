# Data Verification

Status labels in this document mean `BUILT`, `VERIFIED`, `PLANNED`, `BLOCKED`, or `UNVERIFIED`.
All runtime observations below were unauthenticated and read-only. They are dated in the relevant
section; the initial capability verification was made on 2026-09-12.

## Implemented Bitget public reference-data contract — 2026-09-13

`BitgetReferenceDataProvider` uses unauthenticated `GET` requests only: mapping uses
`/api/v3/market/instruments` and `/api/v3/reality/market/stock-info`; actions use
`/api/v3/reality/market/dividends`, `/api/v3/market/split-records`,
`/api/v3/reality/market/share-capital-change`, and
`/api/v3/reality/market/suspension-resumption-info`; source metadata uses
`/api/v3/reality/market/states` and `/api/v3/reality/market/calendar`. Reality endpoints document
one request/second/IP, split records five requests/second/IP, and all require no permission. The
official sources are the Reality market-data, Reality basic-info, UTA public-config, and August
2026 changelog pages linked below; retrieval was `2026-09-13T15:20:00Z`.

Runtime differed from documentation: `tradingPeriod` was an array rather than a string;
`states.data` was an object rather than an array and used `EST` where docs say `ET`; action dates
were often epoch-millisecond strings; split dates were compact `YYYYMMDD` rather than
`yyyy-MM-dd`; the terminal dividend page used `list=null` with `cursor=null`. Only verified forms
are accepted. Contradictory identifiers, malformed dates or
ratios, invalid types/statuses, and non-progressing pagination fail closed; empty histories are
valid.

Raw envelopes are retained in `raw_reference_observations`; validated versions use
`reality_symbol_mappings`, `corporate_actions`, `share_capital_changes`, `suspension_records`, and
`source_session_metadata`. With no provider action ID, identity is a SHA-256 of canonical JSON
containing only record type and source fields. Identical later runs deduplicate normalized records;
changed upstream fields append a new version without overwriting evidence. Bitget exposes no
permanent identifier or publication timestamp. Availability is therefore `UNKNOWN`, and action
coverage remains `AVAILABLE / PARTIAL`, unsuitable as an authoritative point-in-time master.

## Native U.S. equity provider verification gate — 2026-09-13

Verification timestamp: `2026-09-13T10:32:29Z`.

No native-equity provider is selected. The technical candidates can all be reached from a remote
worker over authenticated HTTPS, but this workspace has no provider credentials and none of the
reviewed self-service terms establish the rights SessionZero needs for its intended research,
strategy-derived outputs, and eventual public application. Under ADR-011 the implementation gate
is therefore `GATED`; no adapter, symbol mapping, historical slice, or database schema was added.

| Requirement | Massive | Alpaca Market Data | Twelve Data |
|---|---|---|---|
| U.S. stock coverage | All U.S. stocks; official product page says 100% coverage across exchanges, dark pools, and FINRA facilities | Basic is IEX only; Algo Trader Plus is SIP/all U.S. exchanges | U.S. equities/ETFs; provider advertises all U.S. markets but does not identify a consolidated reference-close feed as clearly as Massive/Alpaca SIP |
| Historical depth | Basic: 2 years; Starter: 5; Developer: 10; Advanced: 20+ | Since 2016 on Basic and Algo Trader Plus | Daily generally back to first trading date; one-minute data from 2020-02-10; depth varies by instrument/interval |
| OHLC | Daily and minute/custom aggregates; qualifying trades; missing bar when no eligible trade | Minute through monthly aggregate bars | Intraday and daily/weekly/monthly OHLCV |
| Adjustment semantics | `adjusted=true` is split-adjusted; `false` is as-traded/unadjusted; response repeats the flag | Explicit `raw`, `split`, `dividend`, `spin-off`, and `all` modes | `adjust=all|splits|dividends|none`; support also states daily/weekly/monthly are split-adjusted and intraday is unadjusted, so exact behavior still needs live contract verification |
| Corporate actions | New `/stocks/v1/splits` endpoint supplies event id, execution date, type, ratio, and historical adjustment factor; included in all stock plans | `/v1/corporate-actions` includes forward/reverse/unit splits and other actions, but warns creation may be delayed | `/splits` supplies date and ratio; available on Grow/Venture and above |
| Instrument identity | Point-in-time ticker reference supports ticker, name, market, locale, primary-exchange MIC, CIK, composite FIGI, and share-class FIGI | U.S. stock/ETF symbol coverage; historical bars offer `asof` symbol mapping, with documented next-day mapping lag after a rename | Symbol catalog plus exchange/MIC metadata; FIGI access is higher-tier |
| Authentication | API key in `apiKey` query parameter or official client | `APCA-API-KEY-ID` and `APCA-API-SECRET-KEY` headers | API key; examples use `apikey` query parameter |
| Rate limit | Basic: 5 requests/minute; paid individual stock plans advertise unlimited calls | Basic: 200 historical calls/minute; Algo Trader Plus docs say 10,000/minute (marketing also says unlimited, so the API documentation is controlling) | Basic: 8 API credits/minute and 800/day; higher tiers start at 55 credits/minute; endpoint weights apply |
| Current relevant price | Stocks Basic $0/month, Starter $29, Developer $79, Advanced $199; all are labeled individual/non-professional | Basic $0; Algo Trader Plus $99/month | Individual Basic $0, Grow $79, Pro $229, Ultra $999; current business Venture pricing is materially higher and must be confirmed for the needed rights |
| Free/developer limitations | Basic has 2-year history, end-of-day data, and 5 calls/minute; individual license only | Free uses IEX, approximately 2.5% of U.S. volume, and excludes the latest 15 minutes; it is not a trustworthy consolidated official/reference close | Free is internal non-display, 8 credits/minute, 800/day; split endpoint requires Grow/Venture |
| Research/non-display rights | Self-service terms restrict use to personal, non-business, non-commercial display use and separately prohibit non-display use, derived works, and an investment strategy unless licensed | Customer agreement permits personal access but forbids reproduction, distribution, sale, or commercial exploitation without written consent | Individual plans are personal/internal/non-commercial; non-display scope depends on tier; free commercial use is forbidden |
| Public display/redistribution | Individual plans expressly forbid customer-facing display and redistribution; Business/order-form rights require sales and applicable exchange licensing | Public/commercial display or redistribution is not established by the reviewed Trading API plan or customer agreement; written consent/partner terms are required | External display requires an eligible business tier; redistribution requires an add-on or separate written agreement and may require exchange agreements |
| Remote worker | Technically yes, over HTTPS with a key | Technically yes, over HTTPS with key/secret | Technically yes, over HTTPS with a key |
| Gate result | Best technical fit, but `GATED` on credentials and an appropriate non-display/business license | `GATED`; free IEX is insufficient for reference close and public rights are not verified | `GATED`; credentials, split-tier access, exact adjustment behavior, and public/redistribution rights remain unresolved |

### Official sources and verified implications

**Massive**

- Stocks overview and plan matrix: https://massive.com/docs/rest/stocks/overview
- Current stock pricing: https://massive.com/pricing
- Custom bars contract: https://massive.com/docs/rest/stocks/aggregates/custom-bars
- Point-in-time ticker details: https://massive.com/docs/rest/stocks/tickers/ticker-overview
- Current splits endpoint: https://massive.com/docs/rest/stocks/corporate-actions/splits
- Individual market-data terms: https://massive.com/legal/market-data-terms-of-service
- Business terms: https://massive.com/legal/businesses-terms-of-service

Massive is the preferred technical candidate because it combines consolidated U.S. coverage,
point-in-time identifiers, raw or split-adjusted aggregates, and explicit split data. That is not a
selection: its individual terms expressly restrict non-display strategy use, derived works, public
display, and redistribution. A suitable Business order form and any required exchange permissions
must be reviewed before SessionZero uses the data.

**Alpaca Market Data**

- Plans, authentication, coverage, history, and rate limits:
  https://docs.alpaca.markets/us/v1.1/docs/about-market-data-api
- Historical feeds: https://docs.alpaca.markets/us/v1.1/docs/historical-stock-data-1
- Historical bars and adjustment modes: https://docs.alpaca.markets/us/reference/stockbars
- Corporate actions: https://docs.alpaca.markets/us/reference/corporateactions-1
- Current customer agreement:
  https://files.alpaca.markets/disclosures/library/AcctAppMarginAndCustAgmt.pdf

Alpaca has the strongest explicit point-in-time adjustment choices and a useful corporate-action
API. The free IEX feed represents only a small fraction of U.S. volume and cannot serve as the
required consolidated reference close. Algo Trader Plus supplies SIP coverage, but the reviewed
self-service agreement does not grant SessionZero public/commercial display or redistribution.

**Twelve Data**

- API, OHLC, adjustment, symbol, and splits contracts: https://twelvedata.com/docs
- Current individual pricing and credit limits: https://twelvedata.com/pricing
- Historical depth: https://support.twelvedata.com/en/articles/5656039-how-to-get-historical-prices
- Adjustment clarification:
  https://support.twelvedata.com/en/articles/5179064-are-the-prices-adjusted
- Terms and redistribution boundary: https://twelvedata.com/terms

Twelve Data is technically viable for OHLC and has explicit adjustment modes, but split access is
not on the free individual tier, its published adjustment descriptions require live contract
verification, and external display/redistribution depends on business/add-on agreements.

### Access and licensing decision

- `RESEARCH_USE: GATED` — no credentials or project-appropriate non-display/strategy license is
  present. Personal experimentation rights are not treated as authorization for SessionZero.
- `PUBLIC_DISPLAY: UNVERIFIED` — the intended public application requires provider/business and
  potentially exchange permissions that have not been obtained and reviewed.
- `REDISTRIBUTION: GATED` — all reviewed providers require express entitlements, add-ons, written
  consent, or a negotiated agreement; no such grant exists in the workspace.

Unblock evidence must include a named provider/account tier, credentials supplied through the
secret environment, the applicable executed/current terms for internal quantitative use, and a
written determination of whether raw prices, charts, and derived SessionZero outputs may be shown
publicly. API availability or a free signup alone is not evidence of those rights.

## Bitget-native reference-data verification — 2026-09-13

Verification timestamp: `2026-09-13T11:42:27Z`. The status vocabulary in this matrix is specific
to this investigation: `AVAILABLE`, `GATED`, `UNAVAILABLE`, or `UNKNOWN`. All runtime calls were
unauthenticated, read-only requests. No account was opened, no credentials were supplied, and no
trade endpoint was called.

| Capability | Status | Endpoint/tool | Auth requirement | Evidence | Notes |
|---|---|---|---|---|---|
| Canonical native U.S. equity ticker for a Reality instrument | **AVAILABLE** | `GET /api/v3/reality/market/stock-info` | None; 1 request/s/IP | Live `code=00000` mappings: `RAALUSDT -> AAL`, `RAAPLUSDT -> AAPL`, `RMRNAUSDT -> MRNA` | `code` is documented as the stock ticker. It is a ticker, not a permanent security identifier. |
| Underlying identifier / ticker mapping | **AVAILABLE** for ticker; **UNAVAILABLE** for ISIN/CUSIP/FIGI | Reality `stock-info`; Stock+ `market/static` | Reality mapping public; Stock+ static read-only authentication | Reality responses expose `symbol` and `code`; reviewed Reality, UTA, and Stock+ schemas expose no ISIN, CUSIP, or FIGI | Stock+ uses `ticker.region` such as `AAPL.US`, but no direct Reality-to-Stock+ identifier field was observed. |
| Native-equity regular-session close | **GATED** | Stock+ `GET /api/v3/stockplus/market/quote`; `candlestick`; `history-candlestick` | Stock+ market-data read-only permission and signed headers | Docs expose `prevClose` and `Intraday` OHLC; unauthenticated `AAPL.US` quote returned `40006 Invalid ACCESS_KEY` | No live native close was inspected. The public Reality `lastPrice` is an rToken market price, not a native close. |
| Native-equity next regular-session open | **GATED** | Stock+ quote and session-filtered candles | Stock+ market-data read-only permission and signed headers | Docs expose regular-session `open`/`Intraday` bars; no authenticated call was authorized | A future open price cannot exist before the session trades. Scheduled session timing is separately public below. |
| Official/index/reference price tied to underlying stock | **AVAILABLE** as a derivative reference input; **GATED** as a native quote | UTA futures ticker, index components, index candles; Stock+ quote | Futures reference endpoints public; Stock+ signed auth | Live `AAPLUSDT` perp: index `331.1904438179967775`, mark `331.1`; components were Binance Index, Hyperliquid, and Pyth Pro | This is a Bitget composite for a stock perpetual, not an exchange official close or a direct native-equity print. |
| Native U.S. stock OHLC history | **GATED** | Stock+ `GET /api/v3/stockplus/market/history-candlestick` | Stock+ market-data read-only permission and signed headers | Official schema supports minute through day/year, `Intraday`/pre/post/overnight sessions, and `NoAdjust`/`ForwardAdjust` | Reality and stock-perpetual candles are different instruments and cannot be relabeled as native stock history. |
| Delayed U.S. equity market data | **UNAVAILABLE** | No documented public native-equity delayed endpoint | Stock+ account is required for documented Level 1 real-time data | Official Stock+ material describes Level 1 real-time quotes after account opening, not a public delayed API | Absence is limited to the current reviewed Bitget documentation; marketing pages are not treated as an API contract. |
| U.S. stock futures / stock-related contracts | **AVAILABLE** | UTA instruments, tickers, market/mark/index candles, index components; Agent Hub `market` | None | Live UTA metadata returned 321 `USDT-FUTURES` rows marked `isRwa=YES` or `symbolType=stock`; `AAPLUSDT` was online | Useful as a cross-asset reference input only; perpetual funding, venue liquidity, and composite-index construction differ from native cash shares. |
| Corporate-action metadata | **AVAILABLE / PARTIAL** for Reality-supported codes | Reality `dividends`, `share-capital-change`, `suspension-resumption-info`, and UTA `split-records` | None | Official August changelog and schemas; live AAPL dividends and four current split records returned `code=00000` | Coverage/completeness against an authoritative corporate-action master has not been established. |
| Splits / dividends | **AVAILABLE / PARTIAL** | `GET /api/v3/reality/market/dividends`; `GET /api/v3/market/split-records` | None | Full live AAPL pagination returned 92 dividend rows and five historical splits; the public split feed added four current records | Dividend query is keyed by native ticker. Runtime split dates used `YYYYMMDD`, while docs specify `yyyy-MM-dd`; consumers must fail closed on schema drift. |
| Stock-market trading-session metadata | **AVAILABLE**, with authority limitations | `GET /api/v3/reality/market/states`; `calendar`; `stock-info` | None | Live states returned pre/regular/after/overnight windows; calendar returned weekend rules and dated closures; symbol mapping returned eligible periods | Runtime says `EST` even though docs describe `ET`; no historical effective-dating or early-close contract was verified. Keep XNYS as authoritative cash calendar and use this only for Bitget source availability. |
| Public / unauthenticated availability | **AVAILABLE** for a partial substrate | Reality reference endpoints and generic UTA market endpoints | None | All mapping, states, calendar, dividends, splits, Reality ticker/candles, and futures checks succeeded without credentials | Does not extend to Stock+ native quotes/OHLC, Reality depth, or Reality platform fills. |
| Authenticated-but-read-only availability | **GATED** | Stock+ market data; Reality depth/fills | Signed key; some feeds additionally require entitlement/whitelist | Stock+ docs label endpoints `Stock+ Market Data (read-only)`; public probe returned `40006`; Reality guide gates depth/fills | No private access was requested or used. Account eligibility, KYC, jurisdiction, and market-data entitlement remain unresolved. |
| Agent Hub exposure | **AVAILABLE** only for generic UTA/derivative inputs | `bgc discover --tool market --read-only` (SDK `3.1.0`) | Public for listed market actions | Catalog includes instruments, ticker, candles/history, and index components; searches for stock info, states, calendar, dividends, and split records returned no matches | Agent Hub does not currently expose the new Reality reference endpoints or Stock+ native-equity endpoints, so direct public REST was required for verification. |

### Official Bitget sources checked

- Reality trading and access model: https://www.bitget.com/docs/uta/reality-trading-guide
- UTA instruments, tickers, candles, and index components:
  https://www.bitget.com/docs/catalog/market/market-data
- Reality reference-market endpoints: https://www.bitget.com/docs/catalog/reality/market-data
- Reality company and corporate-action endpoints:
  https://www.bitget.com/docs/catalog/reality/basic-info
- UTA public split records: https://www.bitget.com/docs/catalog/market/public-config
- August 2026 endpoint changelog: https://www.bitget.com/docs/uta/changelog/2026-08
- Stock+ native stock quotes, static data, OHLC history, depth, intraday, and trades:
  https://www.bitget.com/zh-CN/docs/catalog/stock-plus/stock-quotes
- Stock+ static-info English endpoint page:
  https://www.bitget.com/api-doc/uta/stockplus/market/equity-etf/Get-Static-Info
- Stock+ product/access description:
  https://www.bitget.com/support/articles/12560603887309
- U.S. stock Level 2 eligibility:
  https://www.bitget.com/support/articles/12560603885453
- Agent Hub surface: https://www.bitget.com/activity-hub/agent-hub
- API Key Terms of Use: https://www.bitget.com/support/articles/12560603797947

### Reality mapping and price semantics

`stock-info` is the first reviewed official Bitget endpoint that establishes a native ticker
mapping rather than relying on the `r` prefix. Runtime examples were:

| Reality pair | Reality base coin | Native ticker (`code`) | Declared source periods | Weekend tradable |
|---|---|---|---|---|
| `RAALUSDT` | `rAAL` | `AAL` | overnight, pre-market, regular, after-hours | no |
| `RAAPLUSDT` | `rAAPL` | `AAPL` | overnight, pre-market, regular, after-hours | yes |
| `RMRNAUSDT` | `rMRNA` | `MRNA` | overnight, pre-market, regular, after-hours | no |

At the live comparison, the public `RAAPLUSDT` Reality ticker reported `lastPrice=332.78` with
instrument timestamp `1789299700870`. The public `AAPLUSDT` stock perpetual reported
`lastPrice=331.02`, `indexPrice=331.1904438179967775`, and `markPrice=331.1` with timestamp
`1789299696410`. The index was a three-way Bitget composite of Binance Index, Hyperliquid, and
Pyth Pro. These timestamps are Bitget data-generation timestamps and the prices describe an rToken
venue and a perpetual/index respectively; neither establishes the native AAPL official close.

The native Stock+ `AAPL.US` quote would distinguish `lastDone`, `prevClose`, regular `open`, and
pre/post/overnight subquotes, but the unauthenticated read-only probe returned `40006`. It was not
retried with credentials. Consequently there is no verified live native-equity price example and
no Reality-to-native price comparison in this gate.

### Corporate actions and sessions

The public Reality dividend endpoint returned five AAPL cash-dividend records, including explicit
announcement, record, ex-right, and payment dates plus dividend-per-share. Public split records
returned type, status, ratio, effective date, timezone, and Bitget halt bounds. This is sufficient
to add Bitget as a future *supplemental* corporate-action signal after contract tests, but not to
claim complete historical coverage or authoritative adjustment semantics.

The public states/calendar endpoints can describe Bitget's source availability: pre-market
04:00–09:30, regular 09:30–16:00, after-hours 16:00–20:00, and overnight 20:00–04:00, plus weekend
rules and specific closures. They do not replace `exchange-calendars`/XNYS: the live payload used
fixed `EST`, the docs use `ET`, no point-in-time version history was exposed, and no early-close
representation was verified. `stock-info.tradingPeriod` also arrived as an array although its
published schema describes a string.

### Replacement boundary and access implications

Bitget can now satisfy the Reality-to-native ticker mapping and can supplement corporate-action
risk, Bitget source-session availability, and derivative/index reference inputs. It cannot yet
satisfy SessionZero's native cash-equity OHLC/regular-close/next-open requirement without Stock+
authentication. Even then, Stock+ would require live contract verification for history depth,
venue/consolidation semantics, corrections, point-in-time symbol changes, and adjustment behavior.

Technical public access is not a redistribution license. The reviewed API Key Terms grant a
limited, revocable license tied to use of the platform and do not expressly authorize public
display, redistribution, or SessionZero's intended quantitative/non-display derived-product use.
Stock+ Level 1 is described as available after account opening, Level 2 requires VIP eligibility,
and official institutional material says Stock+ permissions/KYC and, for some feeds, whitelisting
may apply. Therefore Bitget does not remove the existing licensing gate for a public product.

## Official documentation reviewed

| Capability | Official documentation URL | Documented endpoint | Documented access | Observed access | Observed UTC timestamp | Notes |
|---|---|---|---|---|---|---|
| Reality guide and identification | https://www.bitget.com/docs/uta/reality-trading-guide | Reuses instruments; `isReality` flag | Capability table says public | **VERIFIED** public | 2026-09-12T13:45:47Z | `isReality=yes` is the canonical filter. The symbol prefix is descriptive, not used as authority. |
| Instruments | https://www.bitget.com/docs/catalog/market-market-data/market-instruments | `GET /api/v3/market/instruments` | Public, 20 requests/s/IP | **VERIFIED** public; code `00000` | 2026-09-12T13:45:47Z | `category=SPOT` returned 1,173 Reality instruments. Older `/api/v3/public/instruments` returned `40404`. |
| Ticker | https://www.bitget.com/docs/catalog/market/market-data | `GET /api/v3/market/tickers` | Public | **VERIFIED** public; code `00000` | 2026-09-12T13:46:14Z | Dynamically selected `RAALUSDT`; returned ticker timestamp and non-empty price/volume fields. |
| Current candles | https://www.bitget.com/docs/catalog/market/market-data | `GET /api/v3/market/candles` | Public in capability table | **VERIFIED** public; code `00000` | 2026-09-12T13:46:14Z | `1H`, `market`, five rows. Unsupported `3m` returned `48001`. |
| Historical candles | https://www.bitget.com/docs/catalog/market/market-data | `GET /api/v3/market/history-candles` | Public in capability table | **VERIFIED** public; code `00000` | 2026-09-12T13:46:33Z | Pre-2026-07-09 sample returned 100 rows. Volume/turnover were present in this sample; docs say they *may* be empty, so schemas preserve missing values. |
| Reality depth | https://www.bitget.com/api-doc/uta/public/Reality-OrderBook | `GET /api/v3/account/reality-orderbook` | API key plus whitelist | **GATED**; unauthenticated code `40006` | 2026-09-12T13:47:00Z | No synthetic fallback. |
| Reality platform fills | https://www.bitget.com/api-doc/uta/public/Reality-Fills | `GET /api/v3/account/reality-fills` | API key plus whitelist | **GATED**; unauthenticated code `40006` | 2026-09-12T13:47:00Z | No synthetic fallback. |

## Documentation contradiction

The Reality guide's capability table labels instruments, ticker, and candles public, but a broad
note says Reality market-data endpoints are only open to whitelisted users. The endpoint-specific
depth and fills pages require both authentication and whitelisting. Runtime evidence resolves the
safe Phase 0 behavior: the four reused market endpoints are currently public; the two dedicated
`/api/v3/account/reality-*` endpoints are gated. Capability states reflect both documentation and
observation, not the broad note alone.

## Reality candle contract

- Type: `market` only. Other documented types may silently fall back, so SessionZero sends only
  `market`.
- Intervals: `1m`, `5m`, `15m`, `1H`, `4H`, `1D` only.
- Before 2026-07-09, volume and turnover may be empty. Empty strings, absent columns, and nulls are
  normalized to `null`, never zero.
- Current endpoint maximum: 1,000 rows. Historical endpoint maximum: 100 rows and at most 90 days
  per requested range.

### Historical pagination verification — 2026-09-12

The current official history documentation defines `startTime` as data after the start, `endTime`
as data before the end, a maximum/default limit of 100, and a maximum 90-day query range. It warns
that an `endTime` even 1 ms beyond an interval boundary can round the calculation and return an
additional earlier interval. It does not document response ordering or a cursor.

Read-only `RAALUSDT` probes established the behavior used by this adapter: responses were ascending,
`limit` selected the newest rows before the requested end, an aligned start timestamp was included,
an aligned end timestamp was excluded, and a non-aligned start could be rounded down. These are
dated observations rather than a stronger provider guarantee. SessionZero therefore paginates
backward by setting the next `endTime` to the oldest returned event time, rejects non-progress,
enforces a caller-controlled maximum page count, and independently clips the final dataset to UTC
`[start, end)`.

### Sparse-window boundary verification — 2026-09-13

Follow-up direct HTTP probes for `RMRNAUSDT`, `1H`, `market`, with a page limit of 100 established
an additional provider behavior. Every response had HTTP 200, provider code `00000`, and strictly
ascending timestamps.

| Request (`startTime` → `endTime`) | Rows | Oldest | Newest | In range | Outside |
|---|---:|---|---|---:|---:|
| `1784332800000` → `1784505600000` | 48 | 2026-07-16 02:00Z | 2026-07-19 14:00Z | 2 | 46 |
| omitted → `1784505600000` | 100 | 2026-07-13 22:00Z | 2026-07-19 14:00Z | 100 | 0 |
| `1784332800000` → `1784419200000` | 24 | 2026-07-17 01:00Z | 2026-07-18 13:00Z | 1 | 23 |
| `1784419200000` → `1784505600000` | 24 | 2026-07-17 02:00Z | 2026-07-19 14:00Z | 1 | 23 |
| `1784246400000` → `1784332800000` | 24 | 2026-07-17 00:00Z | 2026-07-17 23:00Z | 24 | 0 |
| `1784505600000` → `1784592000000` | 24 | 2026-07-20 00:00Z | 2026-07-20 23:00Z | 24 | 0 |

For the exact two-day target, the 46 outside rows were every hourly timestamp from July 16 02:00Z
through July 17 23:00Z. The July 18 request returned July 17 01:00Z–23:00Z plus July 18 13:00Z.
The July 19 request returned July 17 02:00Z–23:00Z, July 18 13:00Z, and July 19 14:00Z. Thus the
provider did not apply `startTime` as a strict lower-bound filter when the target window contained
fewer candle records than its calculated row count. An end-only request and a `limit=10` request
showed that `endTime` still selected the newest available records before the boundary. The latter
returned July 17 16:00Z–23:00Z plus the two target-weekend records.

With the exact start and `endTime=1784505600001`, the response grew from 48 to 49 rows and began at
July 16 01:00Z. This matches Bitget's documented one-extra-interval rounding warning. Moving only
the start 1 ms later did not alter the 48-row response. These observations distinguish documented
end rounding from the separate, undocumented sparse-window backfill behavior.

The production adapter remains correct: it treats provider ordering as untrusted, pages backward
from the oldest returned timestamp, stops once the page reaches the requested start, and clips all
output to `[start, end)`. A live `page_limit=1` run took three pages, received the two target records
plus one older record, and retained exactly July 18 13:00Z and July 19 14:00Z. There is no pagination
defect to correct.

## Reference and source-session verification — 2026-09-12

Reference cash-market sources:

- NYSE official hours and holidays: https://www.nyse.com/trade/hours-calendars. Core trading is
  9:30 a.m.–4:00 p.m. Eastern. The 2026 calendar marks June 19 as closed and November 27 and
  December 24 as 1:00 p.m. Eastern early closes.
- Nasdaq official U.S. holiday schedule:
  https://www.nasdaq.com/market-activity/stock-market-holiday-schedule. It independently confirms
  the 2026 Juneteenth closure, 9:30 a.m.–4:00 p.m. Eastern regular hours, and the November 27 and
  December 24 early closes.
- Maintained implementation: https://pypi.org/project/exchange-calendars/ at pinned version
  `4.13.2`, using its `XNYS` calendar. Deterministic checks match the official dates above and
  verify the U.S. DST shift from a 14:30 UTC open on March 6, 2026 to 13:30 UTC on March 9.

Bitget source-session evidence:

- The official rToken trading-hours article, published `2026-06-23 07:39`, states a general 24/5
  extended schedule and warns that weekend and U.S. holiday access may be limited:
  https://www.bitget.com/support/articles/12560603887176. SessionZero conservatively uses its
  publication timestamp as the earliest supported evidence boundary and does not project it back.
- The official rollout published `2026-07-17 03:40` adds 22 named rTokens, including `rMRNA`, to
  weekend/24/7 trading and explains DST-aware weekend operation:
  https://www.bitget.com/support/articles/12560603889487. It establishes an effective transition
  for `RMRNAUSDT`; it does not establish RAAL eligibility or retroactively cover earlier dates.
- Bitget's current campaign page says rTokens are now 24/7, but it has no symbol-level historical
  effective dates: https://www.bitget.com/campaigns/bitget-rtoken. It is current marketing evidence,
  not authority for historical eligibility.

The curated capability records live in
`packages/market_data/sessionzero_market_data/data/bitget_source_sessions.json`. Each record has
symbol, effective bounds, session mode, source, evidence URL, verification timestamp, and notes.
Wildcard 24/5 evidence cannot prove that an unlisted symbol lacked a separate weekend exception;
such weekend assessments remain `UNKNOWN`. Holiday availability also remains unknown unless an
announcement explicitly establishes it.

### Historical window reinterpretation

The real `RAALUSDT` `1H` window `[2026-06-10T00:00:00Z, 2026-06-24T00:00:00Z)` still contains 216
candles over 336 interval boundaries. All 120 absent hours predate the earliest RAAL-applicable
cited session evidence. They are now `SOURCE_SESSION_UNKNOWN`: 0 proven expected closures, 0 proven
missing-while-open intervals, and 120 unknown. Their alignment with weekends and Juneteenth is
not promoted into a source-closure claim.

For comparison, the evidenced post-rollout `RMRNAUSDT` weekend
`[2026-07-18T00:00:00Z, 2026-07-20T00:00:00Z)` has 48 expected 24/7 hourly intervals. The live API
returned 48 rows but only 2 were inside the requested range (`2026-07-18T13:00:00Z` and
`2026-07-19T14:00:00Z`); 46 boundary-spillover rows were clipped. The quality result therefore
reports 46 `MISSING_WHILE_EXPECTED_OPEN` intervals and `FAIL`. Exact-window, end-only, adjacent-day,
nearby control, page-size, and alignment probes confirm that the provider's history contains only
those two target-window candle records; this is not a SessionZero pagination bug. An independent
read-only `bgc` request reproduced all 48 rows. The result is confirmed provider-history sparsity,
but the API does not establish whether each absent record means no qualifying trade, an upstream
omission, or another cause. It must not be described as a confirmed feed outage.

## Direct API / Agent Hub cross-check

Official Agent Hub source: https://github.com/Bitget-AI/agent-cli

At 2026-09-12T13:50Z, `bgc --read-only` used the same four `/api/v3/market/*` paths for
`RAALUSDT`. Instrument identity (`SPOT`, `isReality=yes`), ticker value/timestamp, and two `1H`
candle rows matched direct API behavior. `bgc` is useful for independent development verification;
the application has no runtime dependency on it.

### Agent Hub installation record

- Official repositories/docs: https://github.com/Bitget-AI/agent_hub and
  https://github.com/Bitget-AI/agent-cli
- CLI installation: `npm install -g @bitget-ai/bitget-agent-cli@3.0.0`.
- CLI package: `@bitget-ai/bitget-agent-cli` 3.0.0; `bgc --version` reports
  `bitget-agent-sdk` 3.1.0.
- Skill installation: `npx --yes @bitget-ai/bitget-agent-skill@3.2.1 --target codex`.
- Codex skill status: **VERIFIED INSTALLED** at the user Codex skill location.
- `bgc discover`: seven domains (`market`, `trade`, `account`, `funds`, `subaccount`, `loan`,
  `tax`) plus raw/auth/discovery meta tools. The market verb fronts 16 public read operations,
  including instruments, tickers, current/history candles, ordinary order books, and fills.
- Phase 0 market cross-check: **VERIFIED** with `--read-only`; no credentials.
- Agentic Account authorization: **NO — PLANNED, NOT AUTHORIZED**.

## Provenance and retention

Normalized records include source, market/category, symbol, UTC event time where the provider
supplies one, UTC ingestion time, and raw/derived status.

### Historical export contract

Run the production exporter with an explicit UTC half-open range `[start, end)`:

```bash
.venv/bin/sessionzero-export-bitget-history \
  --symbol RAALUSDT \
  --interval 1H \
  --start 2026-06-10T00:00:00Z \
  --end 2026-06-16T00:00:00Z \
  --limit 100 \
  --output artifacts/raalusdt-2026-06-10_2026-06-16-1h.jsonl
```

The command always discovers the Reality universe through `GET /api/v3/market/instruments` and
accepts a requested symbol only when current metadata identifies it as an online Reality
instrument. With no `--symbol`, it deterministically selects the lexicographically first online
Reality symbol. It then requests real `market` candles from
`GET /api/v3/market/history-candles`, normalizes every row through `MarketCandle`, filters to the
requested half-open range, rejects duplicate event times, sorts ascending by `event_time`, and
atomically publishes only a complete non-empty result. Fixtures and synthetic records are not
production inputs.

The format is canonical UTF-8 JSON Lines with one compact, key-sorted object and one LF terminator
per normalized candle. Every object contains `source`, `symbol`, `market`, `event_time`,
`ingestion_time`, `raw_or_derived`, `interval`, `open`, `high`, `low`, `close`, `volume`, and
`turnover`. Times serialize in UTC. Decimal values serialize as strings to preserve decimal
meaning. Missing provider volume or turnover serializes as JSON `null`, never zero.

For identical upstream observations and a fixed ingestion clock, record ordering and serialized
bytes are deterministic. In normal operation `ingestion_time` intentionally records the current
ingestion run, so exports from separate runs are not expected to be byte-identical; tests compare
market-record content independently of that field. Bitget may revise upstream observations, and
the historical endpoint returns at most 100 records for a request of at most 90 days, so this
exporter makes no stronger replay or completeness guarantee than that upstream response permits.

Exports belong under `artifacts/`, which is ignored by Git. They must not be committed or mixed
with deterministic test fixtures. Dataset versioning, availability timestamps, gap checks, and
point-in-time replay remain outside this slice.

## PostgreSQL persistence contract

Alembic revision `20260912_01` creates:

- `ingestion_runs`: one row per persistence attempt. `records_received` is the number of validated
  upstream observations presented to persistence; `records_written` is newly inserted normalized
  candles.
- `raw_market_observations`: the original Bitget candle array in JSONB plus endpoint, UTA version,
  source identity, UTC event/ingestion times, and owning run. Its per-run unique constraint prevents
  duplicate raw inserts inside one attempt while retaining each separate attempt as audit evidence.
- `normalized_market_candles`: exact arbitrary-precision PostgreSQL `NUMERIC` OHLC, nullable
  volume/turnover, UTC `TIMESTAMPTZ`, and a database uniqueness constraint on source, symbol,
  market, interval, and event time.

The boundary is `raw provider row → existing MarketCandle validation → normalized row`. Both data
rows are written in one transaction. An identical/retried candle leaves the existing normalized
row unchanged, including its original ingestion time. If Bitget revises a candle, the new raw row
preserves that evidence but the normalized row is conservatively not overwritten. A future
versioned revision model must be designed before revisions can replace canonical values.

PostgreSQL `TIMESTAMPTZ` stores instants independent of display timezone. SessionZero connections
set their session timezone to UTC, and tests verify UTC-aware round trips. Decimal input is never
routed through binary floating point.

## Bounded history quality contract

The one-shot workflow accepts at most a 90-day interval and a historical page size from 1 through
100. Pages are bounded by `max_pages`; empty responses terminate, and stale/non-progressing cursors
or an exhausted page budget fail explicitly. Identical records repeated across adjacent pages are
deduplicated deterministically and reported as a warning. Conflicting or same-series duplicates,
out-of-order timestamps, boundary spillover, empty datasets, impossible OHLC relationships,
non-positive prices, and negative volume/turnover are failures.

Expected timestamps are regular UTC multiples of the requested interval within `[start, end)`.
Each absent timestamp is classified through point-in-time source evidence:
`EXPECTED_SOURCE_CLOSURE` is informational and not a gap; `MISSING_WHILE_EXPECTED_OPEN` is a
warning; and `SOURCE_SESSION_UNKNOWN` is a warning that cannot be silently resolved either way.
Totals and at most ten examples are emitted per class. There is no forward fill, interpolation, or
synthetic zero-volume record. Null volume or turnover remains valid because Bitget documents those
fields as possibly absent for older Reality history.

Quality validation occurs before persistence. `FAIL` datasets are returned as structured evidence
and do not enter the raw/normalized transaction. `PASS` and `WARN` datasets persist through the
accepted transaction and idempotency contract. Migration `20260912_02` adds nullable request start,
request end, interval, page count, and quality status to ingestion runs while preserving older rows.

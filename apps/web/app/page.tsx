import Image from "next/image";
import Link from "next/link";
import { Activity, ArrowUp, ArrowUpRight, BookOpen, FlaskConical, History, Layers3, Moon, MoreHorizontal, Radio, Search, ShieldCheck, Sparkles, Split } from "lucide-react";

export default function Home() {
  return (
    <>
<header className="mx-auto flex w-full max-w-[90rem] items-center justify-between px-5 py-5 sm:px-8 lg:px-12">
      <Link href="/" className="flex items-center gap-2.5" aria-label="SessionZero home">
        <span className="relative flex size-7 items-center justify-center rounded-full bg-zinc-950">
          <span className="absolute size-2 rounded-full bg-white"></span>
          <span className="absolute size-4 rounded-full border border-white/70"></span>
        </span>
        <span className="text-base font-medium tracking-tight sm:text-lg">SessionZero</span>
      </Link>

      <nav className="hidden items-center gap-8 text-sm font-medium text-zinc-700 md:flex">
        <Link href="#platform" className="transition hover:text-zinc-950">Platform</Link>
        <Link href="#methodology" className="transition hover:text-zinc-950">
          Methodology
        </Link>
        <Link href="#markets" className="transition hover:text-zinc-950">Markets</Link>
        <Link href="#research" className="transition hover:text-zinc-950">Research</Link>
      </nav>

      <div className="flex items-center gap-2">
        <Link href="#methodology" className="hidden rounded-full border border-zinc-200 px-4 py-2.5 text-sm font-medium shadow-sm transition hover:border-zinc-300 sm:block">
          Methodology
        </Link>
        <Link href="#open" className="rounded-full bg-zinc-950 px-3 py-2.5 text-xs font-medium text-white shadow-sm transition hover:bg-zinc-800 sm:px-4 sm:text-sm">
          Open SessionZero
        </Link>
      </div>
    </header>

    <main className="overflow-hidden">
      <section className="relative pt-16 sm:pt-20 lg:pt-24">
        <div className="mx-auto max-w-5xl px-5 text-center sm:px-8">
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-zinc-200 bg-white px-3 py-1.5 font-['JetBrains_Mono'] text-[10px] font-medium text-zinc-600 shadow-sm sm:text-xs">
            <span className="size-1.5 rounded-full bg-emerald-500"></span>
            POST-CLOSE WINDOW · INTERFACE PREVIEW
          </div>

          <h1 className="mx-auto max-w-4xl text-4xl font-medium leading-[1.02] tracking-tight text-zinc-950 sm:text-5xl lg:text-7xl">
            Price discovery doesn’t stop when Wall Street closes.
          </h1>

          <p className="mx-auto mt-6 max-w-3xl text-base leading-7 text-zinc-600 sm:text-lg">
            SessionZero is the price-discovery engine for the hours when U.S.
            cash equities stop printing prices but tokenized stocks and
            continuous markets keep moving. It estimates where the underlying
            equity should reopen, determines whether the continuous market is
            actually discovering price, and separates actionable dislocation
            from noise.
          </p>
        </div>

        <div className="relative mx-auto mt-12 max-w-[90rem] pb-16 sm:mt-14 sm:pb-20">
          <div className="absolute left-1/2 top-0 z-20 w-[min(36rem,calc(100%-2.5rem))] -translate-x-1/2 rounded-2xl border border-zinc-200 bg-white/95 p-2 shadow-[0_16px_40px_rgba(0,0,0,0.12)] backdrop-blur">
            <div className="flex items-center gap-3 px-3 py-2">
              <Search className="size-4 text-zinc-400" strokeWidth={1.5} aria-hidden="true" />
              <span className="flex-1 text-left text-sm text-zinc-400">
                Inspect a symbol, reopen estimate, state, or gap…
              </span>
              <div className="flex size-8 items-center justify-center rounded-full bg-zinc-950 text-white">
                <ArrowUp className="size-4" strokeWidth={1.5} aria-hidden="true" />
              </div>
            </div>
            <div className="flex items-center gap-4 border-t border-zinc-100 px-3 pt-2 pb-1 text-xs text-zinc-500">
              <span className="flex items-center gap-1.5">
                <Radio className="size-3.5" strokeWidth={1.5} aria-hidden="true" />
                SessionZero query
              </span>
              <span className="hidden sm:inline">Decision protocol: 60 min before open</span>
            </div>
          </div>

          <div className="absolute inset-x-0 top-24 h-[29rem] overflow-hidden bg-zinc-900 sm:top-28 sm:h-[34rem]">
            <Image src="/manhattan-financial-district.jpg" alt="New York Stock Exchange trading floor" width={2200} height={1467} className="h-full w-full object-cover object-center opacity-80 grayscale" priority />
            <div className="absolute inset-0 bg-gradient-to-b from-zinc-950/10 via-zinc-950/5 to-white"></div>
            <div className="absolute inset-x-0 bottom-0 h-2/3 bg-gradient-to-t from-white via-white/25 to-transparent"></div>

            <div className="absolute left-[10%] top-[29%] hidden border-l border-white/45 pl-3 text-left text-white lg:block">
              <p className="font-['JetBrains_Mono'] text-xs text-white/70">
                NEW YORK · POST-CLOSE WINDOW
              </p>
              <p className="mt-1 text-sm font-medium">Cash session illustration</p>
            </div>
            <div className="absolute right-[9%] top-[24%] hidden rounded-full border border-white/30 bg-zinc-950/35 px-3 py-1.5 font-['JetBrains_Mono'] text-xs text-white backdrop-blur lg:block">
              Continuous discovery preview
            </div>
          </div>

          <div className="relative z-10 mx-auto w-[94%] max-w-[72rem] pt-[19rem] sm:pt-[22rem]">
            <div className="relative">
              <div className="absolute -top-11 left-1/2 z-20 flex max-w-[calc(100%-2rem)] -translate-x-1/2 items-center gap-1.5 whitespace-nowrap rounded-full border border-zinc-200 bg-white/95 p-1.5 shadow-lg backdrop-blur">
                <div className="rounded-full px-3 py-1.5 text-xs font-medium text-zinc-500">
                  Fair value
                </div>
                <div className="rounded-full bg-zinc-950 px-3 py-1.5 text-xs font-medium text-white">
                  Discovery board
                </div>
                <div className="hidden rounded-full px-3 py-1.5 text-xs font-medium text-zinc-500 sm:block">
                  21-symbol cohort
                </div>
                <div className="hidden rounded-full px-3 py-1.5 text-xs font-medium text-zinc-500 sm:block">
                  Research
                </div>
              </div>

              <div id="dashboard-preview" className="overflow-hidden rounded-t-2xl border border-zinc-200 bg-zinc-50 shadow-[0_24px_70px_rgba(0,0,0,0.20)]">
                <div className="flex items-center justify-between border-b border-zinc-200 bg-white px-4 py-3 sm:px-5">
                  <div className="flex items-center gap-3">
                    <span className="flex size-6 items-center justify-center rounded-md bg-zinc-950 text-white">
                      <Activity className="size-3.5" strokeWidth={1.5} aria-hidden="true" />
                    </span>
                    <div>
                      <p className="text-sm font-medium">SessionZero Discovery Monitor</p>
                      <p className="font-['JetBrains_Mono'] text-xs text-zinc-500">
                        INTERFACE PREVIEW · STATIC DATA
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="hidden items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 font-['JetBrains_Mono'] text-xs font-medium text-emerald-700 sm:flex">
                      <span className="size-1.5 rounded-full bg-amber-500"></span>
                      PREVIEW
                    </span>
                    <div className="flex size-7 items-center justify-center rounded-md border border-zinc-200 text-zinc-500">
                      <MoreHorizontal className="size-4" strokeWidth={1.5} aria-hidden="true" />
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-px bg-zinc-200 sm:grid-cols-4">
                  <div className="bg-white p-3 sm:p-4">
                    <p className="font-['JetBrains_Mono'] text-xs text-zinc-500">CASH ANCHOR</p>
                    <p className="mt-1 text-lg font-medium tracking-tight">Previous close</p>
                    <p className="mt-1 text-xs text-zinc-500">Native regular session</p>
                  </div>
                  <div className="bg-white p-3 sm:p-4">
                    <p className="font-['JetBrains_Mono'] text-xs text-zinc-500">FAIR VALUE</p>
                    <p className="mt-1 text-lg font-medium tracking-tight">Next-open estimate</p>
                    <p className="mt-1 text-xs text-zinc-500">Model output · versioned</p>
                  </div>
                  <div className="bg-white p-3 sm:p-4">
                    <p className="font-['JetBrains_Mono'] text-xs text-zinc-500">DISCOVERY STATE</p>
                    <p className="mt-1 text-lg font-medium tracking-tight text-emerald-700">DISCOVERY</p>
                    <p className="mt-1 text-xs text-zinc-500">One of four locked states</p>
                  </div>
                  <div className="bg-white p-3 sm:p-4">
                    <p className="font-['JetBrains_Mono'] text-xs text-zinc-500">SESSIONZERO GAP</p>
                    <p className="mt-1 text-lg font-medium tracking-tight text-amber-700">Fair value − market</p>
                    <p className="mt-1 text-xs text-zinc-500">Interpreted with confidence</p>
                  </div>
                </div>

                <div className="grid gap-3 p-3 sm:grid-cols-[1.75fr_1fr] sm:p-4">
                  <section className="rounded-xl bg-zinc-950 p-4 text-white sm:p-5">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="text-sm font-medium">Continuous discovery path</p>
                        <p className="mt-1 font-['JetBrains_Mono'] text-xs text-zinc-400">
                          CASH CLOSE → SESSIONZERO DECISION TIME
                        </p>
                      </div>
                      <span className="rounded-full bg-emerald-500/15 px-2.5 py-1 font-['JetBrains_Mono'] text-xs font-medium text-emerald-300">
                        DISCOVERY
                      </span>
                    </div>

                    <div className="mt-5 flex h-28 items-end gap-1.5 sm:h-32">
                      <div className="h-[35%] flex-1 rounded-t-sm bg-zinc-700"></div>
                      <div className="h-[42%] flex-1 rounded-t-sm bg-zinc-700"></div>
                      <div className="h-[30%] flex-1 rounded-t-sm bg-zinc-700"></div>
                      <div className="h-[48%] flex-1 rounded-t-sm bg-zinc-600"></div>
                      <div className="h-[45%] flex-1 rounded-t-sm bg-zinc-600"></div>
                      <div className="h-[58%] flex-1 rounded-t-sm bg-emerald-700"></div>
                      <div className="h-[66%] flex-1 rounded-t-sm bg-emerald-600"></div>
                      <div className="h-[60%] flex-1 rounded-t-sm bg-emerald-600"></div>
                      <div className="h-[78%] flex-1 rounded-t-sm bg-emerald-500"></div>
                      <div className="h-[73%] flex-1 rounded-t-sm bg-emerald-500"></div>
                      <div className="h-[86%] flex-1 rounded-t-sm bg-emerald-400"></div>
                      <div className="h-[81%] flex-1 rounded-t-sm bg-emerald-400"></div>
                    </div>
                    <div className="mt-2 flex justify-between font-['JetBrains_Mono'] text-xs text-zinc-500">
                      <span>16:00</span>
                      <span>16:08</span>
                      <span>16:16</span>
                      <span>16:24 ET</span>
                    </div>
                  </section>

                  <section className="rounded-xl border border-zinc-200 bg-white p-4 sm:p-5">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium">Decision layer</p>
                        <p className="mt-1 font-['JetBrains_Mono'] text-xs text-zinc-500">
                          STATE + CONFIDENCE + GAP
                        </p>
                      </div>
                      <Sparkles className="size-4 text-zinc-400" strokeWidth={1.5} aria-hidden="true" />
                    </div>
                    <div className="mt-5 space-y-4">
                      <div>
                        <div className="mb-1.5 flex justify-between text-xs">
                          <span className="text-zinc-600">Discovery confidence</span>
                          <span className="font-medium">Model-derived</span>
                        </div>
                        <div className="h-1.5 rounded-full bg-zinc-100">
                          <div className="h-full w-[68%] rounded-full bg-zinc-950"></div>
                        </div>
                      </div>
                      <div>
                        <div className="mb-1.5 flex justify-between text-xs">
                          <span className="text-zinc-600">Conviction gate</span>
                          <span className="font-medium">Not forced</span>
                        </div>
                        <div className="h-1.5 rounded-full bg-zinc-100">
                          <div className="h-full w-[54%] rounded-full bg-zinc-950"></div>
                        </div>
                      </div>
                      <div className="flex items-center justify-between border-t border-zinc-100 pt-3">
                        <span className="text-xs text-zinc-600">
                          Default action
                        </span>
                        <span className="text-xs font-medium text-emerald-700">
                          WAIT / ABSTAIN
                        </span>
                      </div>
                    </div>
                  </section>
                </div>

                <div className="grid gap-3 px-3 pb-4 sm:grid-cols-3 sm:px-4">
                  <section className="rounded-xl border border-zinc-200 bg-white p-4">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium">Dynamic source leadership</p>
                      <Layers3 className="size-4 text-zinc-400" strokeWidth={1.5} aria-hidden="true" />
                    </div>
                    <div className="mt-3 space-y-2 text-xs">
                      <div className="flex justify-between"><span className="text-zinc-600">Bitget Reality</span><span className="font-medium">Continuous signal</span></div>
                      <div className="flex justify-between"><span className="text-zinc-600">Native SIP</span><span className="font-medium">Cash anchor</span></div>
                      <div className="flex justify-between"><span className="text-zinc-600">Session evidence</span><span className="font-medium">Eligibility</span></div>
                    </div>
                  </section>

                  <section className="rounded-xl border border-zinc-200 bg-white p-4">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium">Market state</p>
                      <Moon className="size-4 text-zinc-400" strokeWidth={1.5} aria-hidden="true" />
                    </div>
                    <div className="mt-3">
                      <p className="font-['JetBrains_Mono'] text-xs text-zinc-500">XNYS CALENDAR</p>
                      <p className="mt-1 text-sm font-medium">Cash closed · continuous market eligible</p>
                      <p className="mt-2 text-xs text-zinc-500">DST, holidays, and session boundaries are calendar-derived.</p>
                    </div>
                  </section>

                  <section className="rounded-xl border border-zinc-200 bg-white p-4">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium">Action policy</p>
                      <ShieldCheck className="size-4 text-zinc-400" strokeWidth={1.5} aria-hidden="true" />
                    </div>
                    <div className="mt-3 grid grid-cols-2 gap-2 font-['JetBrains_Mono'] text-xs">
                      <span className="rounded-md bg-zinc-100 px-2 py-1.5 text-center">LONG</span>
                      <span className="rounded-md bg-zinc-100 px-2 py-1.5 text-center">SHORT</span>
                      <span className="rounded-md bg-zinc-100 px-2 py-1.5 text-center">WAIT</span>
                      <span className="rounded-md bg-zinc-950 px-2 py-1.5 text-center text-white">ABSTAIN</span>
                    </div>
                  </section>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div id="open" className="mx-auto max-w-3xl px-5 pb-20 text-center sm:px-8 sm:pb-28">
          <div className="flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link href="#dashboard-preview" className="inline-flex w-full items-center justify-center gap-2 rounded-full bg-zinc-950 px-5 py-3 text-sm font-medium text-white shadow-sm transition hover:bg-zinc-800 sm:w-auto">
              Open SessionZero
              <ArrowUpRight className="size-4" strokeWidth={1.5} aria-hidden="true" />
            </Link>
            <Link href="#methodology" className="inline-flex w-full items-center justify-center gap-2 rounded-full border border-zinc-200 bg-white px-5 py-3 text-sm font-medium text-zinc-800 shadow-sm transition hover:border-zinc-300 sm:w-auto">
              Explore Methodology
              <BookOpen className="size-4" strokeWidth={1.5} aria-hidden="true" />
            </Link>
          </div>
          <p className="mt-4 font-['JetBrains_Mono'] text-xs text-zinc-500">
            Built for continuous markets around tokenized U.S. equities
          </p>
        </div>
      </section>
      <section id="platform" className="border-t border-zinc-200 bg-zinc-50 py-20 sm:py-24 lg:py-28">
        <div className="mx-auto max-w-5xl px-5 sm:px-8">
          <div className="max-w-3xl">
            <p className="font-['JetBrains_Mono'] text-xs font-medium text-zinc-500">
              OVERVIEW
            </p>
            <h2 className="mt-4 text-3xl font-medium tracking-tight text-zinc-950 sm:text-4xl lg:text-5xl">
              The market keeps moving after the bell
            </h2>
            <div className="mt-6 space-y-5 text-base leading-7 text-zinc-600 sm:text-lg">
              <p>
                The U.S. cash market closes. Information does not. Earnings,
                macro events, sector moves, crypto volatility, overseas trading,
                and continuous tokenized markets can all reshape expectations
                before the next U.S. opening print.
              </p>
              <p>
                Yet most market tools still treat the cash close as the end of
                price discovery.
              </p>
              <p>SessionZero focuses on the period in between.</p>
              <p className="font-medium text-zinc-950">
                Session Zero is the market before the market.
              </p>
            </div>
          </div>

          <div id="markets" className="mt-16 border-t border-zinc-200 pt-12 sm:mt-20 sm:pt-16">
            <div className="max-w-3xl">
              <div className="inline-flex items-center gap-2 rounded-full border border-zinc-200 bg-white px-3 py-1.5 font-['JetBrains_Mono'] text-xs font-medium text-zinc-600 shadow-sm">
                <span className="size-1.5 rounded-full bg-amber-500"></span>
                SIGNAL INTERPRETATION
              </div>
              <h3 className="mt-5 text-2xl font-medium tracking-tight text-zinc-950 sm:text-3xl">
                Not every gap is alpha
              </h3>
              <p className="mt-4 text-base leading-7 text-zinc-600 sm:text-lg">
                A tokenized equity trading away from the last cash-market close
                does not automatically mean it is mispriced.
              </p>
              <p className="mt-8 font-['JetBrains_Mono'] text-xs font-medium text-zinc-500">
                THE CONTINUOUS MARKET MAY BE:
              </p>
            </div>

            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <div className="group rounded-xl border border-zinc-950 bg-zinc-950 p-5 text-left text-white shadow-sm transition hover:bg-zinc-800">
                <div className="flex items-center justify-between">
                  <span className="font-['JetBrains_Mono'] text-xs font-medium text-emerald-300">
                    01
                  </span>
                  <span className="rounded-full bg-emerald-500/15 px-2.5 py-1 font-['JetBrains_Mono'] text-xs font-medium text-emerald-300">
                    ACTIVE
                  </span>
                </div>
                <p className="mt-7 text-base font-medium">DISCOVERY</p>
                <p className="mt-2 text-sm leading-6 text-zinc-400">
                  Actively incorporating information ahead of the next cash
                  open.
                </p>
              </div>
              <div className="group rounded-xl border border-zinc-200 bg-white p-5 text-left shadow-sm transition hover:border-zinc-300 hover:bg-zinc-50">
                <div className="flex items-center justify-between">
                  <span className="font-['JetBrains_Mono'] text-xs font-medium text-zinc-400">
                    02
                  </span>
                  <span className="size-2 rounded-full bg-amber-500"></span>
                </div>
                <p className="mt-7 text-base font-medium text-zinc-950">
                  UNDERREACTION
                </p>
                <p className="mt-2 text-sm leading-6 text-zinc-600">
                  Moving in the right direction, but not far enough.
                </p>
              </div>
              <div className="group rounded-xl border border-zinc-200 bg-white p-5 text-left shadow-sm transition hover:border-zinc-300 hover:bg-zinc-50">
                <div className="flex items-center justify-between">
                  <span className="font-['JetBrains_Mono'] text-xs font-medium text-zinc-400">
                    03
                  </span>
                  <span className="size-2 rounded-full bg-amber-500"></span>
                </div>
                <p className="mt-7 text-base font-medium text-zinc-950">
                  OVERSHOOT
                </p>
                <p className="mt-2 text-sm leading-6 text-zinc-600">
                  Repricing beyond what the available evidence supports.
                </p>
              </div>
              <div className="group rounded-xl border border-zinc-200 bg-white p-5 text-left shadow-sm transition hover:border-zinc-300 hover:bg-zinc-50">
                <div className="flex items-center justify-between">
                  <span className="font-['JetBrains_Mono'] text-xs font-medium text-zinc-400">
                    04
                  </span>
                  <span className="size-2 rounded-full bg-zinc-300"></span>
                </div>
                <p className="mt-7 text-base font-medium text-zinc-950">NOISE</p>
                <p className="mt-2 text-sm leading-6 text-zinc-600">
                  Moving without enough reliable information to justify
                  conviction.
                </p>
              </div>
            </div>

            <div className="mt-8 rounded-xl border border-zinc-200 bg-white p-5 shadow-sm sm:flex sm:items-center sm:justify-between sm:gap-8 sm:p-6">
              <p className="max-w-3xl text-base font-medium leading-7 text-zinc-950">
                SessionZero models the state behind the price difference before
                deciding whether the gap matters.
              </p>
              <span className="mt-4 inline-flex shrink-0 items-center gap-2 font-['JetBrains_Mono'] text-xs text-zinc-500 sm:mt-0">
                <Activity className="size-4" strokeWidth={1.5} aria-hidden="true" />
                STATE MODEL
              </span>
            </div>
          </div>
        </div>
      </section>

      <section id="methodology" className="border-t border-zinc-200 bg-white py-20 sm:py-24 lg:py-28">
        <div className="mx-auto max-w-5xl px-5 sm:px-8">
          <div className="max-w-3xl">
            <p className="font-['JetBrains_Mono'] text-xs font-medium text-zinc-500">SYSTEM</p>
            <h2 className="mt-4 text-3xl font-medium tracking-tight text-zinc-950 sm:text-4xl lg:text-5xl">From continuous prices to an explainable decision</h2>
            <p className="mt-6 text-base leading-7 text-zinc-600 sm:text-lg">SessionZero does not treat every post-close move as a trade. It follows a fixed sequence that separates observation, estimation, interpretation, and action.</p>
          </div>

          <div className="mt-12 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-5"><p className="font-['JetBrains_Mono'] text-xs text-zinc-500">01 · SENSE</p><h3 className="mt-5 text-lg font-medium">Observe the off-session market</h3><p className="mt-2 text-sm leading-6 text-zinc-600">Collect continuous-market prices, session evidence, native cash anchors, and data-quality context.</p></div>
            <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-5"><p className="font-['JetBrains_Mono'] text-xs text-zinc-500">02 · FAIR VALUE</p><h3 className="mt-5 text-lg font-medium">Estimate the next cash reopen</h3><p className="mt-2 text-sm leading-6 text-zinc-600">Produce a versioned estimate for the next regular-session opening level using only eligible inputs.</p></div>
            <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-5"><p className="font-['JetBrains_Mono'] text-xs text-zinc-500">03 · STATE</p><h3 className="mt-5 text-lg font-medium">Explain the move</h3><p className="mt-2 text-sm leading-6 text-zinc-600">Classify discovery as DISCOVERY, UNDERREACTION, OVERSHOOT, or NOISE.</p></div>
            <div className="rounded-xl border border-zinc-200 bg-white p-5"><p className="font-['JetBrains_Mono'] text-xs text-zinc-500">04 · GAP</p><h3 className="mt-5 text-lg font-medium">Measure the dislocation</h3><p className="mt-2 text-sm leading-6 text-zinc-600">Compare continuous pricing with Fair Value, then interpret the distance through state and data quality.</p></div>
            <div className="rounded-xl border border-zinc-200 bg-white p-5"><p className="font-['JetBrains_Mono'] text-xs text-zinc-500">05 · CONVICTION</p><h3 className="mt-5 text-lg font-medium">Decide how much to trust it</h3><p className="mt-2 text-sm leading-6 text-zinc-600">Combine Gap, State, and Discovery Confidence rather than hardcoding conviction from price alone.</p></div>
            <div className="rounded-xl border border-zinc-950 bg-zinc-950 p-5 text-white"><p className="font-['JetBrains_Mono'] text-xs text-zinc-400">06 · EXECUTE</p><h3 className="mt-5 text-lg font-medium">LONG · SHORT · WAIT · ABSTAIN</h3><p className="mt-2 text-sm leading-6 text-zinc-400">Execution is downstream of evidence. Weak confidence is allowed to end in no trade.</p></div>
          </div>
        </div>
      </section>

      <section className="border-t border-zinc-200 bg-zinc-950 py-20 text-white sm:py-24 lg:py-28">
        <div className="mx-auto grid max-w-5xl gap-12 px-5 sm:px-8 lg:grid-cols-[1.1fr_.9fr] lg:items-start">
          <div>
            <p className="font-['JetBrains_Mono'] text-xs font-medium text-zinc-400">FAIR VALUE</p>
            <h2 className="mt-4 text-3xl font-medium tracking-tight sm:text-4xl lg:text-5xl">Where should the equity reopen?</h2>
            <p className="mt-6 max-w-2xl text-base leading-7 text-zinc-400 sm:text-lg">SessionZero Fair Value estimates the next regular-session opening level. It is a prediction target, not a trade recommendation. The system then asks whether the continuous market is leading, lagging, overshooting, or simply noisy.</p>
          </div>
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-5 shadow-2xl sm:p-6">
            <p className="font-['JetBrains_Mono'] text-xs text-zinc-500">DYNAMIC SOURCE LEADERSHIP</p>
            <div className="mt-5 space-y-4">
              <div className="border-b border-zinc-800 pb-4"><div className="flex items-center justify-between"><span className="text-sm">Continuous market</span><span className="font-['JetBrains_Mono'] text-xs text-emerald-300">PRICE DISCOVERY</span></div><p className="mt-2 text-sm leading-6 text-zinc-500">Can lead when new information is being incorporated while cash markets are closed.</p></div>
              <div className="border-b border-zinc-800 pb-4"><div className="flex items-center justify-between"><span className="text-sm">Native cash market</span><span className="font-['JetBrains_Mono'] text-xs text-zinc-300">ANCHOR / OUTCOME</span></div><p className="mt-2 text-sm leading-6 text-zinc-500">Provides the previous close and the later reopening outcome used for evaluation.</p></div>
              <div><div className="flex items-center justify-between"><span className="text-sm">Session evidence</span><span className="font-['JetBrains_Mono'] text-xs text-amber-300">ELIGIBILITY</span></div><p className="mt-2 text-sm leading-6 text-zinc-500">Determines whether an observation belongs to a known, supported trading session rather than assuming 24/7 continuity.</p></div>
            </div>
          </div>
        </div>
      </section>

      <section className="border-t border-zinc-200 bg-white py-20 sm:py-24 lg:py-28">
        <div className="mx-auto max-w-5xl px-5 sm:px-8">
          <div className="grid gap-12 lg:grid-cols-2 lg:items-center">
            <div>
              <p className="font-['JetBrains_Mono'] text-xs font-medium text-zinc-500">ABSTENTION</p>
              <h2 className="mt-4 text-3xl font-medium tracking-tight sm:text-4xl">Sometimes the correct signal is no signal</h2>
              <p className="mt-6 text-base leading-7 text-zinc-600 sm:text-lg">SessionZero treats uncertainty as information. If the discovery state is noisy, inputs are stale, or confidence is weak, the system can WAIT or ABSTAIN rather than manufacture conviction.</p>
            </div>
            <div className="rounded-2xl border border-zinc-200 bg-zinc-50 p-6">
              <div className="flex items-center justify-between"><span className="font-['JetBrains_Mono'] text-xs text-zinc-500">DECISION GATE</span><span className="rounded-full border border-zinc-200 bg-white px-3 py-1 font-['JetBrains_Mono'] text-xs">NOISE</span></div>
              <div className="mt-8 grid grid-cols-2 gap-3">
                <div className="rounded-xl border border-zinc-200 bg-white p-4"><p className="text-sm text-zinc-500">Gap</p><p className="mt-1 font-medium">Present</p></div>
                <div className="rounded-xl border border-zinc-200 bg-white p-4"><p className="text-sm text-zinc-500">Confidence</p><p className="mt-1 font-medium">Insufficient</p></div>
                <div className="col-span-2 rounded-xl bg-zinc-950 p-4 text-white"><p className="text-sm text-zinc-400">Output</p><p className="mt-1 text-xl font-medium">ABSTAIN</p></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="research" className="border-t border-zinc-200 bg-zinc-50 py-20 sm:py-24 lg:py-28">
        <div className="mx-auto max-w-5xl px-5 sm:px-8">
          <div className="max-w-3xl">
            <p className="font-['JetBrains_Mono'] text-xs font-medium text-zinc-500">RESEARCH & REPLAY</p>
            <h2 className="mt-4 text-3xl font-medium tracking-tight sm:text-4xl lg:text-5xl">Built to be replayed, challenged, and measured</h2>
            <p className="mt-6 text-base leading-7 text-zinc-600 sm:text-lg">SessionZero keeps research identity, dataset versions, decision times, target definitions, and experiment outputs explicit so historical claims can be reproduced instead of hand-written after the fact.</p>
          </div>
          <div className="mt-12 grid gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-zinc-200 bg-white p-5"><History className="size-5 text-zinc-500" strokeWidth={1.5} aria-hidden="true" /><h3 className="mt-5 font-medium">Historical replay</h3><p className="mt-2 text-sm leading-6 text-zinc-600">Reconstruct the SessionZero window against frozen data and explicit session boundaries.</p></div>
            <div className="rounded-xl border border-zinc-200 bg-white p-5"><Split className="size-5 text-zinc-500" strokeWidth={1.5} aria-hidden="true" /><h3 className="mt-5 font-medium">Untouched final OOS</h3><p className="mt-2 text-sm leading-6 text-zinc-600">Development and validation are separated from the final chronological out-of-sample period.</p></div>
            <div className="rounded-xl border border-zinc-200 bg-white p-5"><FlaskConical className="size-5 text-zinc-500" strokeWidth={1.5} aria-hidden="true" /><h3 className="mt-5 font-medium">Ablation first</h3><p className="mt-2 text-sm leading-6 text-zinc-600">The full system must prove whether State and Confidence improve on Fair Value alone after realistic costs.</p></div>
          </div>
          <div className="mt-8 rounded-xl border border-amber-200 bg-amber-50 p-5 text-sm leading-6 text-amber-950"><span className="font-['JetBrains_Mono'] text-xs font-medium">CURRENT CLAIM BOUNDARY</span><p className="mt-2">Retrospective model diagnostics remain <strong>RETROSPECTIVE ESTIMATED</strong> while immutable prospective observations accumulate. SessionZero does not relabel incomplete evidence as a verified backtest.</p></div>
        </div>
      </section>

      <section className="border-t border-zinc-200 bg-white py-20 sm:py-24 lg:py-28">
        <div className="mx-auto max-w-5xl px-5 sm:px-8">
          <div className="grid gap-12 lg:grid-cols-[.9fr_1.1fr] lg:items-start">
            <div>
              <p className="font-['JetBrains_Mono'] text-xs font-medium text-zinc-500">PRODUCTION INTEGRITY</p>
              <h2 className="mt-4 text-3xl font-medium tracking-tight sm:text-4xl">The demo and the product are the same system</h2>
            </div>
            <div className="grid gap-px overflow-hidden rounded-2xl border border-zinc-200 bg-zinc-200 sm:grid-cols-2">
              <div className="bg-zinc-50 p-5"><p className="font-['JetBrains_Mono'] text-xs text-zinc-500">REMOTE DATA</p><p className="mt-3 text-sm leading-6 text-zinc-700">Persistent PostgreSQL, remote workers, versioned observations, and production scheduling.</p></div>
              <div className="bg-zinc-50 p-5"><p className="font-['JetBrains_Mono'] text-xs text-zinc-500">FAIL CLOSED</p><p className="mt-3 text-sm leading-6 text-zinc-700">Missing or gated market inputs remain unavailable rather than being replaced with hidden mock data.</p></div>
              <div className="bg-zinc-50 p-5"><p className="font-['JetBrains_Mono'] text-xs text-zinc-500">POINT-IN-TIME</p><p className="mt-3 text-sm leading-6 text-zinc-700">Prospective snapshots preserve what was actually observed before the decision rather than rewriting history later.</p></div>
              <div className="bg-zinc-50 p-5"><p className="font-['JetBrains_Mono'] text-xs text-zinc-500">AUDITABLE</p><p className="mt-3 text-sm leading-6 text-zinc-700">Dataset, cohort, calendar, model, and experiment versions stay attached to every reproducible result.</p></div>
            </div>
          </div>
        </div>
      </section>

      <section className="border-t border-zinc-200 bg-zinc-950 py-20 text-white sm:py-24">
        <div className="mx-auto max-w-5xl px-5 text-center sm:px-8">
          <p className="font-['JetBrains_Mono'] text-xs text-zinc-500">SESSION ZERO</p>
          <h2 className="mx-auto mt-4 max-w-3xl text-3xl font-medium tracking-tight sm:text-4xl lg:text-5xl">See what the market is discovering before Wall Street prints again.</h2>
          <p className="mx-auto mt-5 max-w-2xl text-base leading-7 text-zinc-400">Explore the product interface, methodology, and research framework behind SessionZero.</p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link href="#dashboard-preview" className="inline-flex w-full items-center justify-center gap-2 rounded-full bg-white px-5 py-3 text-sm font-medium text-zinc-950 sm:w-auto">Open SessionZero <ArrowUpRight className="size-4" strokeWidth={1.5} aria-hidden="true" /></Link>
            <Link href="#methodology" className="inline-flex w-full items-center justify-center gap-2 rounded-full border border-zinc-700 px-5 py-3 text-sm font-medium text-white sm:w-auto">Explore Methodology <BookOpen className="size-4" strokeWidth={1.5} aria-hidden="true" /></Link>
          </div>
        </div>
      </section>
    </main>

    <footer className="border-t border-zinc-200 bg-white">
      <div className="mx-auto flex max-w-[90rem] flex-col gap-4 px-5 py-8 text-sm text-zinc-500 sm:px-8 md:flex-row md:items-center md:justify-between lg:px-12">
        <div className="flex items-center gap-2.5"><span className="relative flex size-6 items-center justify-center rounded-full bg-zinc-950"><span className="absolute size-1.5 rounded-full bg-white"></span><span className="absolute size-3.5 rounded-full border border-white/70"></span></span><span className="font-medium text-zinc-900">SessionZero</span></div>
        <p className="font-['JetBrains_Mono'] text-xs">Price discovery beyond the cash close.</p>
      </div>
    </footer>
    </>
  );
}

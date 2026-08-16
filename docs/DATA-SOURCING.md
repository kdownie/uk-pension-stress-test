# The data question

**15 August 2026.** Last session I called data "the real blocker." Having gone at
it properly, that was half right. It splits into two problems, and only the small
one actually needs a dataset.

---

## The split

| | Worth | Needs a dataset? |
|---|---:|---|
| **A. The return assumption** — what the pot compounds at | **±12 pp** | **No** |
| **B. The path shape** — sequence, clustering, drawdown texture | **~2 pp** | Yes |

The expensive, licence-encumbered data is needed only for the part worth two
percentage points. The part worth twelve is published free by the regulator.

## A. The return assumption is already solved, by the FCA

**COBS 13 Annex 2** prescribes the rates a firm *must* use when projecting a
personal pension. Nominal: **2% / 5% / 8%**. Price inflation: **0% / 2% / 4%**.
Deflating by the intermediate inflation rate gives real returns of **0.00% /
2.94% / 5.88%**.

That is UK-specific, authoritative, free, public, and it is the standard a
regulator would measure the site against. For a tool whose selling point is
transparency, "here is the regulator's own central assumption, and here is the
box where you disagree with it" is a stronger position than any historical series.

It is also sobering. The prototype ran at 4.09% real. The FCA's central
assumption is 2.94%. Same plan, both engines:

| Assumption | Real return | Plan succeeds |
|---|---:|---:|
| Prototype's synthetic history | 4.09% | 46.4% |
| **FCA centre** | **2.94%** | **35.9%** |
| FCA lower | 0.00% | 9.6% |
| FCA higher | 5.88% | 70.2% |

Sustainable income at 90% confidence drops from £21,717 to **£20,719** net real.
Most consumer calculators default to something nearer the FCA's *higher* rate.

Implemented as `FCAPrescribed` in `returns.py`. No dataset, no licence, no blocker.

**Caveat:** the FCA prescribes returns, not **volatility**. That number has no
regulatory backing and has to be a stated user assumption. Which leads to the trap
below.

## The arithmetic/geometric trap

While testing the above I hit a result that looked wrong: raising volatility
*improved* the success rate. It isn't a bug, and it's worth building the site
around.

"Expected return 5%" is ambiguous. Pin it as a **geometric** mean (what the pot
actually compounds at) and volatility adds dispersion without lowering the centre,
so more paths clear the bar. Pin it as an **arithmetic** mean and volatility drags
the compound rate down. Same headline number, opposite conclusion about risk:

| Volatility | Geometric pinned at 2.94% | Arithmetic pinned at 2.94% |
|---:|---:|---:|
| 5% | 19.4% | 16.4% |
| 10% | 31.6% | 23.8% |
| 15% | 35.2% | 23.2% |
| 20% | 37.3% | 21.4% |
| 25% | 37.9% | 18.2% |

Under arithmetic pinning the real compound return at 25% vol is **−0.23%** — the
stated "2.94%" has entirely evaporated into variance drag. The FCA doesn't specify
which convention its rates use. Nor does any consumer calculator I'm aware of.
Making the user choose, and showing them the table above, is exactly the kind of
thing an independent site exists to do.

## B. The licensed part — what I actually verified

| Source | Licence | Verified | Coverage | Verdict |
|---|---|---|---|---|
| **JST Macrohistory** (R6) | **CC BY-NC-SA 4.0** | Yes — stated on macrohistory.net | 18 countries, 1870–, returns on equities/bonds/bills/housing + CPI | Ready-made and excellent, but see below |
| **BoE "Millennium of Macroeconomic Data"** (Thomas & Dimsdale 2017, v3.1) | datahub.io publishes it as **OGL v3.0** | **No — third-party assertion only** | UK, prices from 1209, rates from 1694, ~130 series | Best option *if* the licence holds |
| **ONS** (CPI/RPI) | OGL v3.0 | Standard ONS terms | UK inflation | Safe |
| **FCA Handbook** COBS 13 Annex 2 | Public Handbook | Yes — fetched from the live Handbook | Prescribed rates | Safe to cite |
| Barclays Equity Gilt Study | Proprietary | — | UK 1899– | Out |
| DMS / UBS Global Investment Returns Yearbook | Proprietary (via Morningstar) | — | 35 countries 1900– | Out; headline stats citable, data isn't |
| FTSE All-Share | FTSE Russell licence | — | — | Out |

### The JST problem

JST is the obvious technical choice — real total returns, ready to use, no
construction needed. But **NonCommercial-ShareAlike** has teeth:

- The site could never carry ads, affiliate links, sponsorship or a paid tier.
  Not "shouldn't" — couldn't, without breaching. You said not-for-profit, so that
  may be fine, but it's a permanent decision made early.
- **ShareAlike** means an adapted database must be released under the same terms,
  which propagates the restriction into anything derived from it.
- The terms explicitly forbid commercial providers integrating any part of it.

A free, ad-free public information site is very likely within the NonCommercial
boundary. But "very likely" is doing real work in that sentence, and the boundary
is genuinely fuzzy in CC's own guidance.

### The BoE option, and its one open question

Open Government Licence v3.0 permits commercial use, redistribution and adaptation
with attribution — everything JST forbids. If the BoE dataset really is OGL, it's
strictly better, and it's UK-specific rather than a UK slice of an international
panel.

**But I could only verify OGL from datahub.io, a third party.** The Bank's own
research-datasets page states no licence at all, and I couldn't reach its terms
page. That's not good enough to build on. It also needs total returns
*constructed* from a price index plus dividend yield, rather than supplied.

One email settles it. Draft in `boe-licence-query.md`.

## Recommendation

**Ship v1 with no historical dataset at all.**

FCA prescribed rates as the default engine, user-settable return and volatility,
and the arithmetic/geometric choice made explicit. That is:

- zero licensing exposure, and no decision that forecloses future options
- more defensible to a regulator than any series you could license
- more transparent, which is the entire premise of the site
- costing about two percentage points on a number already uncertain by twelve

**Then add historical bootstrap as a labelled second engine** once the Bank
confirms the licence in writing. Use JST during development as a cross-check on
your own construction — never shipped, so NC never bites.

This inverts the original plan, and it follows from the prototype result rather
than from the licensing: engine sophistication was never where the value was.

## What I could not verify

- The BoE licence, from a Bank primary source. Treat OGL as unconfirmed.
- Whether the BoE dataset contains enough to build equity **total** returns
  (price index plus dividend yield) — the field list wasn't reachable.
- The JST variable schema in detail; the documentation PDF wouldn't fetch. The
  loader should detect columns rather than assume names.
- Whether the FCA's prescribed rates are currently under review. They're
  periodically reset, and there was 2025–26 consultation activity I didn't chase
  down. Re-check the live Handbook before launch, and build the figures as
  configuration rather than constants — which `FCAPrescribed` already does.

## Sources

- [FCA Handbook COBS 13 Annex 2 — Projections](https://handbook.fca.org.uk/handbook/COBS/13/Annex2.html)
- [Jordà-Schularick-Taylor Macrohistory Database](https://www.macrohistory.net/database/)
- [A Millennium of Macroeconomic Data for the UK — datahub.io](https://datahub.io/economic-history/millennium-macroeconomic-data-uk)
- [Bank of England — Research datasets](https://www.bankofengland.co.uk/statistics/research-datasets)
- [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/)

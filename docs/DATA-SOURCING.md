# The data question

**15 August 2026.** Last session I called data "the real blocker." Having gone at
it properly, that was half right. It splits into two problems, and only the small
one actually needs a dataset.

---

## The split

| | Worth | Needs a dataset? |
|---|---:|---|
| **A. The return assumption** — what the pot compounds at | **±12 pp** | **No** |
| **B. The path shape** — sequence, clustering, drawdown texture | **~3 pp** | Yes |

The expensive, licence-encumbered data is needed only for the part worth three
percentage points. The part worth twelve is published free by the regulator.

## A. The return assumption has a public, UK-specific reference point: the FCA's

**COBS 13 Annex 2** sets the rates a firm may use when projecting a personal
pension. Nominal: **2% / 5% / 8%**. Price inflation: **0% / 2% / 4%**. Deflating
by the intermediate inflation rate gives real returns of **0.00% / 2.94% /
5.88%**.

**Corrected 20 August 2026 — these are not "prescribed" rates.** 2.3R sets
**maximum** rates: the firm's intermediate rate "must accurately reflect the
investment potential of each of the product's underlying investment options" and
"must not exceed" the table. Only the inflation rates in 2.5R are prescribed as
fixed values. So 5% nominal is the **highest intermediate rate a firm may use**,
with the firm expected to justify it against the actual investments — a cap on
the central case, not the top of the permitted range (1.1R requires lower,
intermediate and higher to be shown, so 2/5/8 is the full span). The Handbook
caps this number; it does not endorse it. Section 4 of
[FINDINGS.md](FINDINGS.md) has the detail.

That is UK-specific, authoritative, free, public, and it is the standard a
regulator would measure the site against. For a tool whose selling point is
transparency, "here is the Handbook's own intermediate case, and here is the box
where you disagree with it" is a stronger position than any historical series.

It is also sobering. The prototype ran at 4.09% real. The Handbook's
intermediate case is 2.94%. Same plan, both engines:

| Assumption | Real return | Plan succeeds |
|---|---:|---:|
| Prototype's synthetic history | 4.09% | 46.4% |
| **FCA intermediate** | **2.94%** | **35.9%** |
| FCA lower | 0.00% | 9.6% |
| FCA higher | 5.88% | 70.2% |

Sustainable income at 90% confidence drops from £21,717 to **£20,719** net real.
Consumer calculators we looked at tended to default to something nearer the
FCA's *higher* rate; we did not survey enough of them to say "most".

Implemented as `FCAPrescribed` in `returns.py` — a name kept for compatibility
and corrected in its own docstring. No dataset, no licence, no blocker.

**Caveat:** the FCA caps returns and says nothing about **volatility**. That number has no
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
| **BoE "Millennium of Macroeconomic Data"** (Thomas & Dimsdale 2017, v3.1) | datahub.io publishes it as **OGL v3.0** | **No — third-party assertion only, and see below** | UK, prices from 1209, rates from 1694, ~130 series | Best option *if* the licence holds |
| **ONS** (CPI/RPI) | OGL v3.0 | Standard ONS terms | UK inflation | Safe |
| **FCA Handbook** COBS 13 Annex 2 | Public Handbook | Yes — fetched from the live Handbook | Maximum return rates; prescribed inflation | Safe to cite |
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

FCA projection rates as the default engine, user-settable return and volatility,
and the arithmetic/geometric choice made explicit. That is:

- zero licensing exposure, and no decision that forecloses future options
- more defensible to a regulator than any series you could license
- more transparent, which is the entire premise of the site
- costing about three percentage points on a number already uncertain by twelve

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
- Whether the FCA's maximum rates are currently under review. They're
  periodically reset, and there was 2025–26 consultation activity I didn't chase
  down. Re-check the live Handbook before launch, and build the figures as
  configuration rather than constants — which `FCAPrescribed` already does.

## G. The Bank of England licence position, as far as it is known

**Researched 20 August 2026** from [bankofengland.co.uk/legal](https://www.bankofengland.co.uk/legal).
All of it supports the decision above to ship without a historical dataset.

1. **Bank material is not Crown copyright.** Copyright is owned by "the Governor
   and Company of the Bank of England" — a distinct legal person, not a
   government department. **The Open Government Licence therefore does not apply
   by default.**
2. **The Bank's OGL statement is scoped to the "Bank of England Database"**, the
   interactive statistical database — not to research datasets. The research
   datasets page carries **no licence statement at all**.
3. **The default permission does not cover this use.** Download, display or
   print "for personal use or internal use within an individual organisation for
   non-commercial purposes". Publishing derived series on a website is neither.
   Beyond that needs the Head of Communications Division.
4. **There is precedent for carve-outs**: some exchange-rate series are excluded
   from the Bank's OGL because they are "reproduced by the Bank under licence
   from third parties". The Millennium dataset is a compilation drawn from many
   academic sources.

**So the datahub.io OGL v3.0 label is unsourced** — it links to the National
Archives licence text but cites no Bank statement. Given point 1, the mirrors are
not evidence of the Bank's position.

Correspondence is tracked in [boe-licence-query.md](boe-licence-query.md).

## Sources

- [FCA Handbook COBS 13 Annex 2 — Projections](https://handbook.fca.org.uk/handbook/COBS/13/Annex2.html)
- [Jordà-Schularick-Taylor Macrohistory Database](https://www.macrohistory.net/database/)
- [A Millennium of Macroeconomic Data for the UK — datahub.io](https://datahub.io/economic-history/millennium-macroeconomic-data-uk)
- [Bank of England — Research datasets](https://www.bankofengland.co.uk/statistics/research-datasets)
- [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/)

# What we found

**Updated 20 August 2026.** This is what came out of building the stress test:
the results that surprised us, the three bugs worth knowing about — one in how
this sort of calculator is usually written, two in our own engine — and what the
tool still doesn't model.

Everything here describes what a model produced under stated assumptions. It is
not a recommendation, and none of it is advice. Every figure below can be
reproduced from the [public repository](https://github.com/kdownie/uk-pension-stress-test);
§9 says how.

A version of this written for a general reader is at
[pensionstresstest.co.uk/findings.html](https://pensionstresstest.co.uk/findings.html).

---

## Version history

- **v0.1 — 15 August 2026.** Prototype engine, synthetic data, incomplete tax
  modelling. Internal only.
- **v1.0 — 18 August 2026.** Public release. FCA projection rates, verified UK
  tax rules, full reproducibility between the Python engine and the browser
  engine, cross-checked by `verify_web.py`.
- **v1.1 — 20 August 2026.** Every figure regenerated on a single disclosed
  return engine; the `household.py` lifetime-tax bug found and fixed (§8);
  Pfau's international results added to §2; the FCA "prescribed rates"
  description corrected throughout (§4).
- **v1.2 — 31 August 2026.** The two policy assumptions sourced from ONS data
  (§12); withdrawal ordering added to the engine.

---

## 1. The decisions that move the answer are not the ones people model

We ranked modelling choices by how far each moves a single number: the share of
runs in which a £500,000 pot delivers £30,000 of net real income from age 60 to
95.

**Assumptions, stated because the previous version of this document did not.**
2.94% real return, 15% volatility, 20,000 paths, averaged over three random
seeds. That is the scenario the browser tool loads with, so the baseline here —
**35.7%** — is the 35% the front page shows on its single seed.

| Decision | Effect on success |
|---|---:|
| Tax-free cash spent elsewhere rather than funding income | **−24.8 pp** |
| Real return assumption +1%/yr | +11.9 pp |
| Real return assumption −1%/yr | −10.7 pp |
| Retiring at 62 instead of 60 | +7.5 pp |
| Tax bands frozen for 20 years (fiscal drag) | −6.6 pp |
| State Pension at 80% of full (partial NI record) | −6.3 pp |
| Stochastic engine: historical bootstrap → i.i.d. lognormal *(different basis — see below)* | **+2.8 pp** |

The last row is a **matched pair**, not a change to the baseline: the same
scenario run through a block bootstrap and through an independent lognormal
draw, both set to 4.09% real and 16.5% volatility, scored 46.0% and 48.8%.

The last row is also the punchline. The choice of return-generating engine — the
part that looks like the hard modelling, the part with the interesting maths —
matters about a ninth as much as what happens to the tax-free cash.

We expected the opposite. The hypothesis going in was that sequence-of-returns
structure — volatility clustering, bad decades arriving in a run — would
separate a sophisticated engine from a naive one. It doesn't, and the reason is
temporal aggregation: daily volatility clustering largely washes out by the time
it is compounded into annual returns. Matched on geometric return and
volatility, the two engines' answers never diverged by more than about 3pp
anywhere on the withdrawal curve.

Three of the seven rows are UK-policy-specific: fiscal drag, the State Pension
record, and the tax treatment of the lump sum. We are not aware of a free
calculator that models any of them.

> **Correction, 20 August 2026.** The previous version of this table was
> computed on the bootstrap engine (4.09% real, 16.5% vol) while §5 used the FCA
> engine (2.94% real, 15% vol), and neither was disclosed. A reader clicking
> from a 45.9% baseline here to a calculator showing 35% had no way to reconcile
> them. Everything in this document now runs on the calculator's own default.
>
> That version also claimed the tax-free cash decision "moves the answer more
> than everything else combined". **It was false on the old table too** — −27.9
> against 34.8 for the other rows summed there, and −24.8 against 35.1 on the
> regenerated figures above. It is the largest single decision here, which is
> the defensible claim.

---

## 2. The 4% rule is a fact about one country's data

Bengen's 1994 result is the most quoted number in retirement planning: a retiree
takes 4% of the pot in the first year, uprates that amount with inflation, and
the money is said to last thirty years. His words, on a 50/50 portfolio: *"In no past case has it caused a
portfolio to be exhausted before 33 years."*

Two things about that. It came from **Ibbotson US data from 1926**, on a
portfolio half in shares and half in bonds. And it is **a count of overlapping
windows, not a probability** — it says the rule held in every stretch of
American history for which there is data, which is a different claim from "this
works 100% of the time".

### The same test, run on seventeen countries

Pfau (2010) ran Bengen's exercise across 17 developed countries on the
Dimson–Marsh–Staunton dataset, 1900–2008, allowing each country the *best
possible* asset allocation with a century of hindsight:

| Country | Highest rate that survived every 30-year window |
|---|---:|
| Canada | 4.42% |
| Sweden | 4.23% |
| Denmark | 4.08% |
| United States | 4.02% |
| **United Kingdom** | **3.77%** |

Four of seventeen reached 4%, and the United States was the fourth of them, only
just. **A British retiree drawing on British market history would have got
3.77%** — and at a full 4%, the worst British starting year, 1900, ran dry after
26 years.

This is the strongest evidence here and it is not ours. It is published, it uses
real historical data rather than a simulation, and it includes the UK.

### What our own engine adds

On a synthetic series compounding at **4.09% real** with 16.5% volatility, a 4%
gross withdrawal survived 30 years in **74.0%** of runs.

**This is not a replication of Bengen and should not be quoted as one.** Our
series is more volatile than his half-bonds portfolio and it is synthetic rather
than historical; both push the number down. `verify.py`'s own comment says so.
What it demonstrates is narrower: the relationship between the draw rate and the
rate the money actually compounds at is very nearly the whole story. A 4.00%
draw from something growing at 4.09% is a close-run thing. The 100% was never a
property of the number 4. It was a property of the data.

And all of that is before any tax, which is where the rest of this document
comes in.

---

## 3. "5% expected return" is not yet a number

Ask what a 5% expected return means and there are two answers, and they are not
close.

If 5% is the **geometric** mean — the rate the money actually compounded at —
then adding volatility around it doesn't hurt the median outcome much, and can
help it.

If 5% is the **arithmetic** mean — the average of the annual returns — then
variance drag eats it. Push volatility to 25% and a stated 2.94% real becomes
**−0.23%** actually compounded. The stated number is unchanged. The money is
gone.

Nothing in COBS 13 Annex 2 resolves this, because within the rules it never
arises: the annex governs a **single-path deterministic projection**, a rate
"compounded on an annual basis", with no distribution around it. Nothing there
tells you what to do with the number inside a stochastic model. As far as we can
tell, no consumer calculator addresses it either — they take a percentage and
run. The tool makes the user choose, because the choosing is the modelling.

---

## 4. The FCA does not prescribe the return rates — it caps them

**Corrected 20 August 2026.** This document, the README, `returns.py`,
`DATA-SOURCING.md`, the site's FAQ and the social card all described COBS 13
Annex 2 as setting "prescribed rates". Checked against the live Handbook, that
is not what it says.

- **2.3R sets *maximum* rates.** A firm's intermediate rate "must accurately
  reflect the investment potential of each of the product's underlying
  investment options", and the rates "must not exceed the following maximum
  rates" — for a personal or stakeholder pension, 2% / 5% / 8% nominal for
  lower / intermediate / higher.
- **2.5R does prescribe inflation**, as fixed values: 0% / 2% / 4%.

So the tool's default is not a figure the regulator asserts is correct. It is
**the highest intermediate rate a firm may use for a personal pension**, with
the firm expected to justify it against the actual underlying investments:

    (1.05 / 1.02) − 1 = 2.94% real

**Do not overstate this, as an earlier draft of this section did.** 5% is a cap
on the *central* case, not the top of the permitted range. **1.1R** requires a
compliant projection to show lower, intermediate and higher, so 2/5/8 is the
full span and 5 is its middle — the browser tool's own dropdown offers all
three. And because the cap is uniform across all personal pensions regardless of
asset mix, for an equity-heavy pot it is arguably a mandated understatement
rather than optimism. The defensible claim is narrow: **the Handbook caps this
number, it does not endorse it.**

**A disclaimer that turned out to be wrong.** `returns.py` and earlier versions
of this document said the 5%-with-2% pairing was "our interpretation — the
Handbook prescribes the rates, not how to combine them". It does specify.
**1.2R** requires the projection to "be in real terms" and to use "the
intermediate rate of price inflation, in accordance with COBS 13 Annex 2 2.5R".
Deflating 5% by 2% is the Handbook's own construction. The parameter stays
exposed so a user can model something else, but the default needed no apology.

One scoping note: all of the above is about **COBS 13 Annex 2**. A different UK
regime — the FRC's AS TM1, for statutory money purchase illustrations — does
prescribe accumulation rates by volatility group. Nothing here is a claim that
no UK rules prescribe projection rates.

The `FCAPrescribed` class keeps its name so existing code and saved scripts
still run; its docstring carries this correction.

---

## 5. Two personal allowances are worth more than most strategies

Same £800,000, same £40,000 net target, age 60 to 95, same assumptions as §1
(2.94% real, 15% vol, 20,000 paths, three seeds):

| | Funded to 95 | Lifetime tax |
|---|---:|---:|
| Couple, £400k each | **80.8%** | £111,500 |
| One person, £800,000 | **43.6%** | £205,700 |

Nearly double the success rate and about **£94,000 less tax**, from nothing but
having two of everything the tax system gives per person: two personal
allowances, two basic-rate bands, two State Pensions.

**Read the tax column carefully.** It is measured on the runs that funded the
income *in full to 95*, so both rows describe the same delivered income. That
distinction is not pedantry — see §8. Across *all* runs the single person's
median lifetime tax is only about £181,200, lower than the couple's, but only
because the median single-person run stops being able to withdraw at 83. Running
out of money is an effective way to reduce a tax bill.

This is not a strategy anyone can adopt — you have the household you have. It is
included because it calibrates everything else. An effect of 37pp makes the 12pp
from the return assumption look modest, and makes the 3pp from engine choice
look like what it is.

### The survivor cliff is the opposite of what people expect

The intuition is that losing a partner is a financial catastrophe for the pot.
It isn't — because the survivor spends about a third less.

What actually happens is worse, and quieter. Run a couple needing £40,000 net
against the same household after one death:

| | Gross withdrawal needed |
|---|---:|
| Couple | £18,620 |
| Survivor (67% of the couple's spending) | £17,810 |

Spending falls 33%. The withdrawal falls **4%**.

The reason is that the survivor loses one State Pension — £12,547.60 a year,
which at the full new State Pension with no protected payment is not inheritable
— and one personal allowance, £12,570 of tax-free room. Both disappear at once.
The pot has to replace them, so it drains for one person nearly as fast as it
did for two.

So the cliff is real, but it is a cliff in *income efficiency*, not in pot
survival. A model that reports only success rates will show almost nothing
happening. Ours reports both.

---

## 6. A bug in how this is usually implemented

GOV.UK presents income tax as ranges: £12,571–£50,270 at 20%, and so on. That
presentation silently assumes a full personal allowance.

The actual mechanics are different. The basic-rate band is a **width** —
£37,700 — that sits on top of whatever personal allowance survives the £100,000
taper. Once the allowance starts tapering, the 40% band starts *lower*, not at
£50,270.

Build the calculator from the published table rather than the legislation and
you understate tax across the taper region. The error is exactly 40% of the
allowance lost, so it **reaches £5,028 the moment the allowance is fully gone at
£125,140 of income, and stays at £5,028 for every income above that**. It is a
plateau, not a peak. That is precisely the range a large pot in drawdown reaches.

Our first implementation had this bug. The engine now reproduces figures
computed from the legislated rates exactly:

| Income | Tax |
|---:|---:|
| £110,000 | £33,432 |
| £150,000 | £53,703 |

Both checks run every time `verify.py` runs. Note the wording: these are
computed from the rates, not lifted from a published HMRC table — HMRC does not
publish worked totals at those incomes, so describing them as "published
figures", as earlier versions of this document and `verify.py` did, was a claim
that could not be checked.

Worth noting what kind of mistake the original was: a bug in reading a
government website correctly, not in the maths. Those are the ones that survive.

---

## 7. A bug in our own engine, and what it cost

On 18 August 2026 we found that the Python engine handed a household £100,000 of
tax-free cash out of the pot of a partner who was already dead when the
projection began. A deceased member's lump sum entitlement dies with them; the
pot passes across whole, as inherited drawdown. Nobody could have taken that
money.

**What it cost:** on £400,000 + £400,000 with a £40,000 net target and a partner
dead at the start, success was **90.1% before the fix and 88.1% after** — a
2.0pp overstatement, in the optimistic direction. That is **just under** the
engine-choice effect in §1 that we use as the threshold for whether a feature is
worth building at all. (Earlier versions of this document said "larger than".
It is not; 2.0 against 2.8.)

**Why it survived.** There are two independent implementations here — the
JavaScript that runs in your browser and a Python reference — and a script that
cross-checks them against each other. The JavaScript had the guard. The Python
didn't. The cross-check should have caught it in a moment, except that **every
couple test case passed a death age of zero**. The comparison had never once
exercised a death.

That is the finding, not the bug. Two independent implementations only protect
you on the paths you actually compare, and a coverage gap is invisible in a
green test run. The question to ask of a passing test suite is not "did it pass"
but "which combinations does it never construct".

The fix and the tests that pin it are in the repository. We checked that the new
tests fail when the guard is removed, because a test that cannot fail proves
nothing. One is deliberately deterministic — zero volatility, so the error shows
up as a flat £100,000 discrepancy in the opening balance rather than as a
statistical wobble a different random seed might have hidden.

---

## 8. A second bug, found while checking §5

**20 August 2026.** Checking the numbers for the public write-up turned up
another one, of exactly the same shape.

`tax_paid` in `household.py` accrued on the withdrawal the household
**intended** to make, not on the withdrawal its pot could actually fund:

```python
tax_paid += (R.income_tax(others[k] + splits[k], ...)
             - R.income_tax(others[k], ...)) * frac
```

Once a pot ran dry the model went on charging tax to age 95 on money nobody
withdrew. The symptom, once we looked, was unmistakable: **across 20,000 paths
`tax_paid` took exactly one value.** A run that failed at 83 and a run that paid
out in full to 95 reported the identical lifetime tax bill, and the number did
not move when the returns moved.

**Why it survived — a new variant of §7's lesson.** The browser engine does not
compute lifetime tax at all, so `verify_web.py` had nothing to cross-check it
against. §7's lesson was *which combinations do the tests never construct*. This
one adds: **which outputs does only one engine produce?** Those are the ones
nobody is checking.

**Blast radius.** No success rate moved, the live site was unaffected, and the
social card was unaffected — `tax_paid` is only ever recorded, never deducted
from a pot, so no projection depended on it. **That cuts both ways and is worth
stating**: the rescue-withdrawal tax added by the fix is accounted but not
funded, so a household rescued from an empty pot is recorded as having met its
income while being short by the tax on the rescue. It is a small optimism in the
success rate, in a corner that only arises for couples once one pot is empty.
Listed in §10. What was wrong was every statement about the
*distribution* of lifetime tax. The §5 headline survives, because that
comparison is made on runs that delivered the income in full and on those runs
the old figure was right: the difference moved from £94,275 to £94,260. What was
wrong was calling £111,450 a **median**. It was not a median of anything.

**The fix, two parts:**

1. Charge tax in proportion to what was actually taken (`taken / want`).
2. Charge tax on the *rescue* withdrawal, where one partner's empty pot is
   covered from the other's. That was previously untaxed entirely; it is now
   charged at the donor's marginal rate, computed once per person per year.

**Section G of `verify_household.py`** pins three things: that lifetime tax takes
more than one value across paths; that a run which ran out of money never
reports *more* tax than one that funded the income in full; and that a household
whose income is fully covered by State Pension pays no tax at all.

Each guard was removed in turn to confirm the checks fail without it:

| Guards | Result |
|---|---|
| Both removed (original code) | checks 1 and 2 both **FAIL**, exit 1 |
| `taken/want` removed only | check 1 **passes**; check 2 **FAILS** — £149,069 on runs that ran out against £122,721 on runs that paid in full |
| Both in place | all pass |

**Check 2 is the load-bearing one.** Check 1 alone can be satisfied by an engine
that is still wrong — the first draft of that comment claimed otherwise, and
testing it showed it was wrong.

---

## 9. How to check any of this

```bash
git clone https://github.com/kdownie/uk-pension-stress-test
cd uk-pension-stress-test/engine
pip install -r requirements.txt
python verify.py && python verify_household.py && python verify_web.py
```

- `verify.py` — tax against figures computed from the legislated rates, gross-up
  as an exact inverse of the tax function, the simulator against a closed-form
  recursion at zero volatility, monotonicity of success in the return
  assumption, and the 4% result in §2.
- `verify_household.py` — Scottish bands hand-computed from the band table,
  couples, the tax-optimal split checked against brute-force search, the
  dead-at-start guard (§7, section F) and the lifetime-tax guards (§8, section G).
- `verify_web.py` — drives the actual live page in a headless browser and
  compares the browser's numbers to the Python engine, line by line.

`engine/make_og_card.py` regenerates the social card from the engine, so the
number on the card is reproducible rather than drawn.

Every legislated figure lives in one block in `engine/uk_rules.py` with a source
URL and the date it was checked. If a number isn't there with a source, it isn't
used.

Monte Carlo figures move by a few tenths of a point between seeds; every
simulated figure in this document is averaged over three seeds.

---

## 10. What isn't modelled

Being explicit about this matters more than the features:

- **Inherited pots are treated as fully taxable drawdown.** Real rules differ by
  age at death — broadly tax-free if the member died before 75, taxed at the
  beneficiary's marginal rate after. Ours is the conservative direction. It is a
  disclosed simplification, not an error.
- **Only a partner's death is modelled, not your own.**
- **Both pots in a couple share one return path** — perfect correlation, no
  diversification benefit between partners. Again the conservative direction.
- **The rescue-withdrawal tax in §8 is accounted but not funded.** When one
  partner's empty pot is covered from the other's, the tax on that withdrawal is
  recorded in `tax_paid` but not deducted from the donor pot, so the success
  rate is very slightly optimistic in that corner. The marginal rate used is
  also computed once per person per year rather than per path.
- No National Insurance (correct for pension income, wrong the moment earned
  income is added), no MPAA or annual allowance, no DB pensions or annuities, no
  pension IHT treatment, no care costs, and no holdings outside a pension or an
  ISA.

  > CORRECTED 2026-09-01. This line read "no investment charges, no care costs,
  > no ISAs or other wrappers yet" until today. **The ISA half had been wrong
  > since 26 August**, when an ISA as a starting asset shipped (stage D) — six
  > days in which this file, `README.md` and `public/findings.html` all told a
  > reader the tool could not do something it could, while `public/index.html`
  > had already been updated. Annual charges shipped on 1 September. 10f: the
  > fix landed in one file and not its three neighbours, and nothing in the
  > neighbours was edited, so nothing looked wrong in them.
- Tax-free cash is capped at the £268,275 lump sum allowance.
- Mortality is a date you pick, not a probability.
- The State Pension defaults to the full new State Pension, which assumes a full
  NI record. Many people get less; an actual forecast is at
  [gov.uk/check-state-pension](https://www.gov.uk/check-state-pension).

---

## 11. Appendix: the detour that started it

This began as a wrapper round `neural-sde`, a neural stochastic differential
equation library, on the assumption that better return modelling was the
interesting problem. §1 is the answer to that assumption. But the negative
result is worth recording.

The neural path **cannot be used for retirement horizons as built**. It fitted
fine — 66 seconds, early stop at epoch 70 — then, extrapolated to 40 years,
produced a geometric return of −52%/yr and a maximum of +4,383,118%.

Not a tuning problem. The state variable is the raw **price level**, z-scored on
training mean and standard deviation. A century of prices is non-stationary, so
the last training price sits at z = 3.64: every forecast *starts* at the edge of
the training distribution and walks outward. Probing the learned diffusion,
implied annual volatility decayed from 15.7% at low prices to **0.0%** at high
ones, against a truth of 16% everywhere — the network learned diffusion in
absolute price units and never learned that it should scale with price.

The clearest test is scale invariance. A correct return model gives the same
one-year distribution from any starting price:

| Start price | Mean 1y return |
|---:|---:|
| 500 | −23.7% |
| 1,000 | −32.1% |
| 2,000 | −41.1% |
| 5,000 | −22.7% |

Identical rows would mean a working model. These are not close.

The fix is architectural rather than a hyperparameter: condition on stationary
features — recent realised volatility, price relative to a moving average — and
model log-returns rather than price levels.

By contrast the parametric path is excellent. `fit(model="gbm")` recovered
μ = 5.35%, σ = 16.80% against a true 5.00% / 16.00%, instantly, in closed form.

The detour was worth it. It produced the ranking in §1, and the ranking is why
this project models tax rules instead of stochastic processes.

---

## 12. What the triple lock has actually been worth

**The working for this lives on the public findings page, not here** — see
[pensionstresstest.co.uk/findings.html#s10](https://pensionstresstest.co.uk/findings.html#s10),
which carries both constructions, the table of which leg bound, and the caveats.
Restating it in two places is how §21e's family of bugs starts, so this entry is
a pointer and a summary only.

The headline: running the triple lock's own formula — the higher of prices,
earnings or 2.5% — over ONS data for 2001–2025 gives growth above inflation of
**1.3–1.4% a year** (median 1.6%), the range covering two ways of measuring it.
The **earnings** leg bound in 12 of 25 years, prices in 8, and the much-argued
**2.5% floor in only 5**.

The calculator's default is unchanged at **0%**, which is the assumption that the
lock ends now. That is a political question and not the tool's to answer; what
changed is that the default is now stated against a measured alternative instead
of standing unexplained.

**Source and licence.** ONS series D7G7 (CPI annual rate, MM23), KAB9 and A2FD
(average weekly earnings, EMP), retrieved 31 August 2026. Contains public sector
information licensed under the
[Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
**Note this is ONS, not the Bank of England's Millennium dataset** — that dataset
ends in 2016 and so cannot see 2022's 9.1% CPI, which is the observation the
inflation assumption most depends on.

---

## Sources

- W. P. Bengen, "Determining Withdrawal Rates Using Historical Data",
  *Journal of Financial Planning*, October 1994.
- W. D. Pfau, "An International Perspective on Safe Withdrawal Rates: The Demise
  of the 4 Percent Rule?", *Journal of Financial Planning*, December 2010.
- FCA Handbook, [COBS 13 Annex 2](https://www.handbook.fca.org.uk/handbook/COBS/13/Annex2.html).
- [gov.uk/income-tax-rates](https://www.gov.uk/income-tax-rates),
  [gov.uk/new-state-pension](https://www.gov.uk/new-state-pension/what-youll-get).
- ONS [D7G7](https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/d7g7/mm23)
  (CPI annual rate, MM23),
  [KAB9](https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/earningsandworkinghours/timeseries/kab9/emp)
  and [A2FD](https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/earningsandworkinghours/timeseries/a2fd/emp)
  (average weekly earnings, EMP), retrieved 31 August 2026. Contains public sector
  information licensed under the
  [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).

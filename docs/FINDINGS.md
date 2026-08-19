# What we found

**Updated 18 August 2026.** This is what came out of building the stress test:
the results that surprised us, the two bugs worth knowing about — one in how
this sort of calculator is usually written, one in our own engine — and what
the tool still doesn't model.

Everything here is a description of what the model produced under stated
assumptions. It is not a recommendation, and none of it is advice. Every figure
below can be reproduced from the [public repository](https://github.com/kdownie/uk-pension-stress-test);
§8 says how.

\---



\## Version History



\- \*\*v0.1 — 15 August 2026\*\*

&#x20; Prototype engine using synthetic data and incomplete tax modelling. Internal only.



\- \*\*v1.0 — 18 August 2026\*\*

&#x20; Public release. FCA‑prescribed projection rates, verified UK tax rules, full

&#x20; reproducibility between Python engine and browser engine, and cross-checks via

&#x20; `verify\\\_web.py`.



\---



## 1\. The decisions that move the answer are not the ones people model

We ranked modelling choices by how much each one moves a single number: the
probability that a £500,000 pot delivers £30,000 of net real income from age 60
to 95. Baseline 45.9%, 20,000 paths.

|Decision|Effect on success|
|-|-:|
|Tax-free cash spent elsewhere rather than funding income|**−27.9 pp**|
|Real return assumption ±1%/yr|**±12 pp**|
|Retiring at 62 instead of 60|+7.3 pp|
|Tax bands frozen for 20 years (fiscal drag)|−6.8 pp|
|State Pension at 80% of full (partial NI record)|−6.5 pp|
|Stochastic engine: historical bootstrap → i.i.d. lognormal|**+2.2 pp**|

The bottom row is the punchline. The choice of return-generating engine — the
part that looks like the hard modelling, the part with the interesting maths —
matters roughly a tenth as much as what happens to the tax-free cash.

We expected the opposite. The hypothesis going in was that sequence-of-returns
structure — volatility clustering, bad decades arriving in a run — would
separate a sophisticated engine from a naive one. It doesn't, and the reason is
temporal aggregation: daily volatility clustering largely washes out by the
time it is compounded into annual returns. Matched on geometric return and
volatility, the two engines' answers never diverged by more than about 3pp
anywhere on the withdrawal curve.

Three of the six rows are UK-policy-specific: fiscal drag, the State Pension
record, and the tax treatment of the lump sum. We are not aware of a free
calculator that models any of them.

\---

## 2\. The 4% rule is a fact about one dataset

On a series compounding at roughly 4% real, a 4% gross withdrawal survived 30
years in **74%** of runs. Not 100%.

Bengen's original result came from US 20th-century returns on a 50/50 portfolio
— about 5% real geometric. The rule is one dataset's arithmetic, restated as a
principle and then travelled across an ocean and a century. Draw rate against
geometric return is essentially the whole story; nearly everything else is
second order.

This is reproduced directly by `verify.py`, so it is checkable in about thirty
seconds rather than taken on trust.

\---

## 3\. "5% expected return" is not yet a number

Ask what a 5% expected return means and there are two answers, and they are not
close.

If 5% is the **geometric** mean — the rate your money actually compounded at —
then adding volatility around it doesn't hurt the median outcome much, and can
help it.

If 5% is the **arithmetic** mean — the average of the annual returns — then
variance drag eats it. Push volatility to 25% and a stated 2.94% real becomes
**−0.23%** actually compounded. The stated number is unchanged. The money is
gone.

The FCA's prescribed projection rates don't specify which mean is meant. Nor,
as far as we can tell, does any consumer calculator: they take a percentage and
run. The tool makes the user pick, because the picking is the modelling.

\---

## 4\. The survivor cliff is the opposite of what people expect

The intuition is that losing a partner is a financial catastrophe for the pot.
It isn't — because the survivor spends about a third less.

What actually happens is worse, and quieter. Run a couple needing £40,000 net
against the same household after one death:

||gross withdrawal needed|
|-|-:|
|Couple|£18,620|
|Survivor (67% of the couple's spending)|£17,810|

Spending falls 33%. The withdrawal falls **4%**.

The reason is that the survivor loses one State Pension — around £12,548 a year,
not inheritable — and one personal allowance, £12,570 of tax-free room. Both
disappear at once. The pot has to replace them, so it drains for one person
nearly as fast as it did for two.

So the cliff is real, but it is a cliff in *income efficiency*, not in pot
survival. A model that reports only success rates will show almost nothing
happening. Ours reports both.

\---

## 5\. Two personal allowances are worth more than most strategies

Same £800,000, same £40,000 net target, age 60 to 95:

||success|lifetime tax|
|-|-:|-:|
|Couple, £400k each|80.8%|—|
|One person, £800,000|43.1%|£94,000 more|

Nearly double the success rate, and £94,000 less tax over the projection, from
nothing but having two of everything the tax system gives per person: two
personal allowances, two basic-rate bands, two State Pensions.

This is not a strategy anyone can adopt — you have the household you have. It
is included because it calibrates everything else. An effect of 37pp makes the
±12pp from the return assumption look modest, and makes the 2.2pp from engine
choice look like what it is.

\---

## 6\. A bug in how this is usually implemented

GOV.UK presents income tax as ranges: £12,571–£50,270 at 20%, and so on. That
presentation silently assumes a full personal allowance.

The actual mechanics are different. The basic-rate band is a **width** —
£37,700 — that sits on top of whatever personal allowance survives the £100,000
taper. Once the allowance starts tapering, the 40% band starts *lower*, not at
£50,270.

Build the calculator from the published table rather than the legislation and
you understate tax across the taper region. The gap widens as the allowance
disappears and peaks at £125,140, where it is roughly **£5,000**. That is
precisely the range a large pot in drawdown reaches.

Our first implementation had this bug. The engine now reproduces the published
figures exactly:

|Income|Tax|
|-:|-:|
|£110,000|£33,432|
|£150,000|£53,703|

Worth noting: this was a bug in reading a government website correctly, not in
the maths. Those are the ones that survive.

\---

## 7\. A bug in our own engine, and what it cost

On 18 August 2026 we found that the Python engine handed a household £100,000
of tax-free cash out of the pot of a partner who was already dead when the
projection began. A deceased member's lump sum entitlement dies with them; the
pot passes across whole, as inherited drawdown. Nobody could have taken that
money.

**What it cost:** on £400,000 + £400,000 with a £40,000 net target and a
partner dead at the start, success was **90.1% before the fix and 88.1% after**.
A 2.0pp overstatement, in the optimistic direction — larger than the
engine-choice effect in §1 that we use as the threshold for whether a feature is
worth building at all.

**Why it survived.** There are two independent implementations here — the
JavaScript that runs in your browser and a Python reference — and a script that
cross-checks them against each other. The JavaScript had the guard. The Python
didn't. The cross-check should have caught it in a moment, except that **every
couple test case passed a death age of zero**. The comparison had never once
exercised a death.

That is the finding, not the bug. Two independent implementations only protect
you on the paths you actually compare, and a coverage gap is invisible in a
green test run. The question to ask of a passing test suite is not "did it
pass" but "which combinations does it never construct".

The fix and the tests that pin it are in the repository. We checked that the new
tests fail when the guard is removed, because a test that cannot fail proves
nothing. One of them is deliberately deterministic — zero volatility, so the
error shows up as a flat £100,000 in the opening balance rather than as a
statistical wobble that a different random seed might have hidden.

\---

## 8\. How to check any of this

```bash
git clone https://github.com/kdownie/uk-pension-stress-test
cd uk-pension-stress-test/engine
pip install -r requirements.txt
python verify.py \&\& python verify\_household.py \&\& python verify\_web.py
```

* `verify.py` — tax against published figures, gross-up as an exact inverse of
the tax function, the simulator against a closed-form recursion at zero
volatility, monotonicity of success in the return assumption.
* `verify\_household.py` — Scottish bands hand-computed from the band table,
couples, and the tax-optimal split checked against brute-force search.
* `verify\_web.py` — drives the actual live page in a headless browser and
compares the browser's numbers to the Python engine, line by line.

Every legislated figure lives in one block in `engine/uk\_rules.py` with a source
URL and the date it was checked. If a number isn't there with a source, it isn't
used.

\---

## 9\. What isn't modelled

Being explicit about this matters more than the features:

* **Inherited pots are treated as fully taxable drawdown.** Real rules differ by
age at death — broadly tax-free if the member died before 75, taxed at the
beneficiary's marginal rate after. Ours is the conservative direction. It is a
disclosed simplification, not an error.
* **Only a partner's death is modelled, not your own.**
* **Both pots in a couple share one return path** — perfect correlation, no
diversification benefit between partners. Again the conservative direction.
* No National Insurance (correct for pension income, wrong the moment earned
income is added), no MPAA or annual allowance, no DB pensions or annuities,
no pension IHT treatment, no ISAs or other wrappers yet.
* The State Pension defaults to the full new State Pension, which assumes a
full NI record. Many people get less; an actual forecast is at
[gov.uk/check-state-pension](https://www.gov.uk/check-state-pension).

\---

## 10\. Appendix: the detour that started it

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

|Start price|Mean 1y return|
|-:|-:|
|500|−23.7%|
|1,000|−32.1%|
|2,000|−41.1%|
|5,000|−22.7%|

Identical rows would mean a working model. These are not close.

The fix is architectural rather than a hyperparameter: condition on stationary
features — recent realised volatility, price relative to a moving average — and
model log-returns rather than price levels.

By contrast the parametric path is excellent. `fit(model="gbm")` recovered
μ = 5.35%, σ = 16.80% against a true 5.00% / 16.00%, instantly, in closed form.

The detour was worth it. It produced the ranking in §1, and the ranking is why
this project models tax rules instead of stochastic processes.


# Pension stress-test prototype — findings

**15 August 2026.** A working UK decumulation engine wrapped round `neural-sde`,
plus the results of actually running it. Read the caveat first.

> **The market data is synthetic.** Outbound market-data feeds are blocked in this
> sandbox and the good UK long-run series (Barclays Equity Gilt Study, DMS) are
> paywalled. Everything below is a statement about the *machinery*, not about real
> markets. The tax figures are real and checked against GOV.UK on 15/08/2026.
> Replacing the data means replacing one function: `returns.load_history()`.

---

## 1. The headline: the exotic part barely matters

Ranked by how much each modelling decision moves the probability that a £500k pot
delivers £30k net real income from 60 to 95 (baseline 45.9%, 20,000 paths):

| Decision | Effect |
|---|---:|
| Tax-free cash spent elsewhere rather than funding income | **−27.9 pp** |
| Real return assumption ±1%/yr | **±12 pp** |
| Retiring at 62 instead of 60 | +7.3 pp |
| Tax bands frozen 20 years (fiscal drag) | −6.8 pp |
| State Pension at 80% of full (partial NI record) | −6.5 pp |
| **Stochastic engine: bootstrap → i.i.d. lognormal** | **+2.2 pp** |

The choice of return-generating engine is the *least* important decision on the
list — an order of magnitude below the things that actually decide whether someone
runs out of money.

I went in expecting the opposite. The hypothesis was that sequence-of-returns
structure — volatility clustering, bad decades — would separate a sophisticated
engine from a naive one. It doesn't, and the reason is temporal aggregation: daily
volatility clustering largely washes out by the time you compound it into annual
returns. Matched on geometric return (3.99%) and volatility (16.67%), the two
engines' answers never diverge by more than ~3pp anywhere on the withdrawal curve.

**What this means for the site.** The differentiator isn't a better engine. It's
modelling the boring decisions nobody else models, and showing the assumptions.
Three of the six rows above are UK-policy-specific and absent from every free
calculator I'm aware of.

## 2. The neural path can't be used for this — and here's exactly why

Fitted fine (66s, early stop at epoch 70, val loss 1.0101). Then, extrapolated to a
retirement horizon, it fell apart: 40-year paths gave a geometric return of −52%/yr
and a maximum of +4,383,118%.

Not a tuning problem. The state variable is the **raw price level**, z-scored on
training-set mean and standard deviation. A century of prices is non-stationary —
the index runs 65 → 5,516 — so:

- The last training price sits at **z = 3.64**. Every forecast *starts* at the
  extreme edge of the training distribution and walks outward from there.
- Probing the learned diffusion across price levels, implied annual volatility
  decays from 15.7% at low prices to **0.0%** at high ones. True process: 16% at
  every level. The network learned diffusion in absolute price units and never
  learned it should scale with price.
- Scale-invariance test — a correct return model gives the same 1-year distribution
  from any starting price:

  | Start price | Mean 1y return | SD |
  |---:|---:|---:|
  | 500 | −23.7% | 0.2% |
  | 1,000 | −32.1% | 0.1% |
  | 2,000 | −41.1% | 0.1% |
  | 5,000 | −22.7% | 0.2% |

  Identical rows would mean a working model. These aren't close.

This is very likely the same root cause as the limitation the package already
documents ("drift recovery is not usable at daily sampling frequency"). It isn't
only signal-to-noise — a network conditioned on a non-stationary state spends its
capacity learning *where in history we are* rather than any reusable structure.

**Suggested fix:** condition on stationary features — recent realised volatility,
price relative to a moving average, time since drawdown — and model log-returns
rather than price levels. That's an architecture change, not a hyperparameter.

By contrast the **parametric path is excellent**: `fit(model="gbm")` recovered
μ = 5.35%, σ = 16.80% against a true 5.00% / 16.00%, instantly, in closed form.
That's what the prototype uses as its second engine.

### Two bugs worth fixing

1. `FittedModel.summary()` raises `TypeError` for neural fits — `highlevel.py:91`
   formats every param with `:.6g`, but the neural model's params dict holds a
   `NeuralSDETrainer` object.
2. Simulation speed: 50 paths × 10,080 daily steps took 435s. The per-step network
   forward runs on a tiny batch, so cost scales with steps rather than amortising
   over paths. Batching paths into a single forward per step would help a lot.

## 3. The 4% rule is a fact about a dataset, not a law

On this data — 4.09% real geometric — a 4% gross withdrawal over 30 years succeeded
**74%** of the time. Bengen's 100% came from US 20th-century returns of roughly 5%
real geometric on a 50/50 portfolio. The rule is one dataset's arithmetic, restated
as a principle. Draw rate versus geometric return is the whole story; everything
else is second order.

## 4. A tax bug worth knowing about

GOV.UK presents the bands as income ranges (£12,571–£50,270 at 20%), which silently
assumes a full personal allowance. The real mechanics: the basic-rate band is
£37,700 wide and sits on top of whatever allowance survives the £100k taper — so
above £100k the 40% band starts *lower*, not at £50,270.

My first implementation followed the GOV.UK presentation and understated tax on
£110,000 by about £5,000 — right in the range a large pot in drawdown hits. The
engine now reproduces published figures exactly (£110,000 → £33,432,
£150,000 → £53,703). Any calculator built from the published table rather than the
legislation has this bug.

---

## What's built

| File | |
|---|---|
| `uk_rules.py` | Tax, State Pension, PCLS. Every legislated figure in one block with source URL and check date. |
| `returns.py` | Return engines behind one interface + the synthetic market. `load_history()` is the swap point for real data. |
| `decumulation.py` | The annual real-terms simulation loop. |
| `verify.py` | 30 checks. Run this first. |
| `run_prototype.py` | The comparison run. |
| `results.html` | Charts. |

`verify.py` covers tax against published figures, gross-up as an exact inverse of
the tax function, the simulator against a closed-form annuity recursion at zero
volatility, and monotonicity of success rate in the return assumption. Two of my
own test-design bugs were caught by it and are documented in the file — including
one that "passed" by comparing 0.0 to 0.0.

## Not modelled

Scotland's bands · MPAA and the annual allowance · DB pensions and annuities ·
pension IHT treatment · partial-year and multi-pot PCLS sequencing · anything
resembling advice.

## The real blocker

Not the maths — **the data**. Everything above runs on a synthetic series. Free,
redistributable, long-run UK real total return data for equities and gilts is the
one thing standing between this and being genuinely useful, and it's a
sourcing/licensing problem rather than a coding one.

## Before any of this goes public

The FCA guidance/advice boundary shapes wording and framing, and it's worth a
proper look at the perimeter guidance rather than my read of it. I'm not a lawyer
and wouldn't want you building on my say-so.

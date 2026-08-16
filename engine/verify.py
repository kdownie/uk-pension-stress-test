"""
Verification. Run this before trusting anything the model says.

Three kinds of check:
  A. Tax layer against hand-computed and published figures.
  B. The simulator against a closed-form answer (zero volatility).
  C. The whole thing against a published external result (the 4% rule).
"""

from __future__ import annotations

import numpy as np

import uk_rules as R
from decumulation import Plan, simulate

PASS, FAIL = "  PASS", "  FAIL"
_failures = []


def check(name: str, got, want, tol=1e-6):
    ok = abs(got - want) <= tol
    if not ok:
        _failures.append(name)
    money = abs(want) > 1.0
    g = f"£{got:,.2f}" if money else f"{got:.6f}"
    w = f"£{want:,.2f}" if money else f"{want:.6f}"
    print(f"{PASS if ok else FAIL}  {name:<52} got {g:>14}  want {w:>14}")


print("=" * 92)
print("A. INCOME TAX  (England/Wales/NI, 2026/27)")
print("=" * 92)

check("nil income", R.income_tax(0), 0.0)
check("at personal allowance, £12,570", R.income_tax(12_570), 0.0)
check("£20,000  = 7,430 @ 20%", R.income_tax(20_000), 1_486.0, 0.01)
check("£50,270  = 37,700 @ 20%", R.income_tax(50_270), 7_540.0, 0.01)
check("£60,000  = 7,540 + 9,730 @ 40%", R.income_tax(60_000), 11_432.0, 0.01)
# Published figures — these are the ones that catch the band-structure bug.
check("£110,000 (PA tapered to 7,570) [published]",
      R.income_tax(110_000), 33_432.0, 0.01)
check("£125,140 (PA fully gone) [published]",
      R.income_tax(125_140), 42_516.0, 0.01)
check("£150,000 (additional rate) [published]",
      R.income_tax(150_000), 53_703.0, 0.01)

print("\n  personal allowance taper")
check("PA at £100,000", R.personal_allowance(100_000), 12_570.0)
check("PA at £110,000", R.personal_allowance(110_000), 7_570.0)
check("PA at £125,140", R.personal_allowance(125_140), 0.0)
check("PA at £200,000 (floors at zero)", R.personal_allowance(200_000), 0.0)

print("\nB. GROSS-UP INVERSE  (gross_for_net must invert income_tax exactly)")
print("=" * 92)
for target, other in [(10_000, 0), (30_000, 0), (30_000, 12_547.60),
                      (80_000, 0), (95_000, 12_547.60), (5_000, 100_000)]:
    g = R.gross_for_net(target, other)
    delivered = R.net_income(other + g) - R.net_income(other)
    check(f"net £{target:,} on top of £{other:,.0f} other income",
          delivered, float(target), 0.01)

print("\nC. TAX-FREE CASH")
print("=" * 92)
check("25% of £400,000 pot", R.pcls(400_000), 100_000.0)
check("£1.5m pot capped at lump sum allowance",
      R.pcls(1_500_000), 268_275.0)
check("£1,073,100 pot — exactly at the cap",
      R.pcls(1_073_100), 268_275.0, 0.01)

print("\nD. SIMULATOR vs CLOSED FORM  (zero volatility => deterministic)")
print("=" * 92)
# With a fixed real return and no state pension, the pot must follow an
# exact annuity recursion. Any discrepancy is a bug in the loop.
plan = Plan(pot=1_000_000, retire_age=60, end_age=90, target_net_income=25_000,
            state_pension_age=200, take_pcls=False)
rate = 0.04
res = simulate(plan, np.full((3, plan.years), rate), "deterministic")

pot = 1_000_000.0
gross = R.gross_for_net(25_000, 0.0)
for _ in range(plan.years):
    pot = (pot - min(pot, gross)) * (1 + rate)
# Must be a SURVIVING case, else both sides are trivially zero and the test
# has no teeth. (First draft of this compared 0.0 to 0.0 and "passed".)
assert pot > 1_000, "closed-form case must not deplete, or the test is vacuous"
check("30y run, 4% real, £25k net p.a.", res.balances[0, -1], pot, 0.01)
check("all paths identical (no rng leakage)",
      float(res.balances.std(axis=0).max()), 0.0, 1e-9)

print("\n  gross-up sanity: £25,000 net costs")
print(f"        £{gross:,.2f} gross  "
      f"(effective rate {1 - 25_000/gross:.1%})")

print("\nE. STATE PENSION INTERACTION")
print("=" * 92)
sp = R.STATE_PENSION_ANNUAL
check("full new State Pension, annual", sp, 12_547.60, 0.01)
check("...is below the personal allowance, so tax on it alone is nil",
      R.income_tax(sp), 0.0)
# Once state pension starts, the pot only has to fund the gap — and every
# pound from the pot is now taxed from the first pound.
g_before = R.gross_for_net(30_000, 0.0)
g_after = R.gross_for_net(30_000 - R.net_income(sp), sp)
print(f"        £30k net before SP age: £{g_before:,.0f} gross from pot")
print(f"        £30k net after  SP age: £{g_after:,.0f} gross from pot"
      f"   (saving £{g_before - g_after:,.0f}/yr)")

print("\nF. 4% RULE vs PUBLISHED RESULT")
print("=" * 92)
# Bengen's finding: a 4% initial withdrawal, inflation-adjusted, survived
# 30 years in every rolling US historical period. This is a smell test on
# the whole pipeline, not a replication — our data is synthetic, and Bengen
# used a 50/50 balanced portfolio whereas our series is all-equity-like at
# ~16% vol, so somewhat below 100% is the RIGHT answer here.
#
# The comparison must be like-for-like on the GROSS draw: Bengen's 4% is a
# gross withdrawal. simulate() takes a NET income target and grosses it up,
# so we invert to get exactly £40,000 gross off a £1m pot.
from returns import load_history, HistoricalBootstrap

_, annual = load_history()
boot = HistoricalBootstrap(annual, block_years=5)
net_for_40k_gross = R.net_income(40_000.0)
plan4 = Plan(pot=1_000_000, retire_age=60, end_age=90,
             target_net_income=net_for_40k_gross, state_pension_age=200,
             take_pcls=False)
r4 = simulate(plan4, boot.sample(5_000, plan4.years, seed=1), "4% rule")
check("gross draw is exactly 4.0% of the pot",
      R.gross_for_net(net_for_40k_gross, 0.0) / 1_000_000, 0.04, 1e-6)

geo = float(np.expm1(np.log1p(annual).mean()))
sr = r4.success_rate
print(f"        history: arithmetic {annual.mean():+.2%}, "
      f"GEOMETRIC {geo:+.2%}, sd {annual.std(ddof=1):.2%}")
print(f"        4% gross draw, 30 years: success {sr:.1%}")
print(f"        -> the draw rate (4.00%) vs the geometric return "
      f"({geo:.2%}) is the whole story.")
print("        Bengen's 100% survival came from US 20th-century returns of")
print("        roughly 5% real geometric on a 50/50 portfolio. On a series")
print("        that only compounds at ~4% real, a 4% draw is a coin-flip-ish")
print("        proposition. The 4% rule is a fact about a dataset, not a law.")

# The real engine test is DIRECTIONAL: success must rise monotonically with
# the return assumption, and must straddle the geometric-return threshold.
print("\n  monotonicity: success rate vs assumed constant real return")
prev, mono_ok = -1.0, True
for cr in [0.00, 0.02, 0.03, 0.04, 0.05, 0.07]:
    rr = simulate(plan4, np.full((200, plan4.years), cr))
    s = rr.success_rate
    if s < prev - 1e-9:
        mono_ok = False
    prev = s
    print(f"        {cr:5.1%} constant real return -> success {s:6.1%}")
if not mono_ok:
    _failures.append("success rate not monotonic in return")
print(f"{PASS if mono_ok else FAIL}  success rate monotonic in assumed return")

# At a constant real return equal to the draw rate on a NET basis the pot
# must be nearly exhausted but not fail: a sharp knife-edge test of the loop.
knife = simulate(plan4, np.full((10, plan4.years), 0.04))
ke_ok = knife.success_rate == 1.0 and knife.balances[0, -1] < 1_000_000
if not ke_ok:
    _failures.append("knife-edge case")
print(f"{PASS if ke_ok else FAIL}  4% return / 4% draw survives but does not "
      f"grow  (end pot £{knife.balances[0,-1]:,.0f})")

print("\n" + "=" * 92)
if _failures:
    print(f"FAILED {len(_failures)} check(s): " + "; ".join(_failures))
    raise SystemExit(1)
print("ALL CHECKS PASSED")
print("=" * 92)

"""
Checks for the region and household layers.

The splitting rule is the risky part: a greedy sort is only optimal if the
tax function really is convex in income. So it is checked against brute force,
not merely asserted.
"""
from __future__ import annotations

import itertools

import numpy as np

import uk_rules as R
from household import Household, Person, optimal_split, simulate_household

fails = []


def chk(name, got, want, tol=0.01):
    ok = abs(got - want) <= tol
    if not ok:
        fails.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name:<54} {got:>13,.2f} vs {want:>13,.2f}")


print("=" * 92)
print("A. SCOTTISH INCOME TAX — hand-computed from the published band table")
print("=" * 92)
# £30,000: starter 3,967@19% + basic 12,989@20% + intermediate 474@21%
chk("Scotland £30,000", R.income_tax(30_000, "scotland"),
    3_967 * .19 + 12_989 * .20 + 474 * .21)
# £60,000: + intermediate full 14,136@21% + higher 16,338@42%
chk("Scotland £60,000", R.income_tax(60_000, "scotland"),
    3_967 * .19 + 12_989 * .20 + 14_136 * .21 + 16_338 * .42)
# £150,000: PA gone, every band shifts down by 12,570
chk("Scotland £150,000", R.income_tax(150_000, "scotland"),
    3_967 * .19 + 12_989 * .20 + 14_136 * .21 + 31_338 * .42
    + (125_140 - 62_430) * .45 + (150_000 - 125_140) * .48)
chk("Scotland at the personal allowance", R.income_tax(12_570, "scotland"), 0.0)
chk("rUK unchanged by the refactor (£110,000)",
    R.income_tax(110_000), 33_432.0)
chk("rUK unchanged by the refactor (£150,000)",
    R.income_tax(150_000), 53_703.0)

print("\n  Scotland vs rUK on the same income")
for inc in [20_000, 30_000, 50_000, 75_000, 125_140]:
    a, b = R.income_tax(inc), R.income_tax(inc, "scotland")
    print(f"        £{inc:>8,}  rUK £{a:>9,.0f}   Scotland £{b:>9,.0f}   "
          f"difference {b - a:>+8,.0f}")

print("\nB. TAX-OPTIMAL SPLIT vs BRUTE FORCE")
print("=" * 92)
# The greedy rule claims optimality. Verify by exhaustive search on a grid:
# no other split may deliver the same net for less gross.
for region in ("ruk", "scotland"):
    for need, others in [(30_000, [0.0, 0.0]),
                         (30_000, [12_548, 12_548]),
                         (60_000, [12_548, 0.0]),
                         (90_000, [0.0, 30_000]),
                         (40_000, [95_000, 0.0])]:
        g = optimal_split(need, others, region)
        delivered = sum(R.net_income(o + w, region) - R.net_income(o, region)
                        for o, w in zip(others, g))
        chk(f"{region}: delivers £{need:,} net (others {others})",
            delivered, float(need), 0.5)

        total = sum(g)
        best = total
        for f in np.linspace(0, 1, 401):
            # brute force: any split of the same net requirement
            lo, hi = 0.0, 500_000.0
            for _ in range(60):
                mid = (lo + hi) / 2
                w = [mid * f, mid * (1 - f)]
                d = sum(R.net_income(o + x, region) - R.net_income(o, region)
                        for o, x in zip(others, w))
                if d < need:
                    lo = mid
                else:
                    hi = mid
            best = min(best, (lo + hi) / 2)
        ok = total <= best + 1.0
        if not ok:
            fails.append(f"split optimality {region} {need}")
        print(f"  {'PASS' if ok else 'FAIL'}  "
              f"{region}: greedy gross £{total:,.0f} <= best found "
              f"£{best:,.0f}")

print("\nC. THE COUPLE ADVANTAGE — two allowances vs one")
print("=" * 92)
for region in ("ruk", "scotland"):
    single = R.gross_for_net(40_000, 0.0, region)
    couple = sum(optimal_split(40_000, [0.0, 0.0], region))
    print(f"  {region:<9} £40,000 net costs a single person £{single:,.0f} gross, "
          f"a couple £{couple:,.0f} — saving £{single - couple:,.0f}/yr")
    ok = couple < single
    if not ok:
        fails.append("couple advantage " + region)

print("\nD. HOUSEHOLD SIMULATION SANITY")
print("=" * 92)
# Parameters chosen so success lands mid-range. A test where every case
# returns 0% (or 100%) cannot detect anything — an earlier draft of this
# file did exactly that and "passed".
# Constant returns make every path identical, so success is necessarily 0% or
# 100% and comparisons are meaningless. Use the stochastic engine here.
from returns import FCAPrescribed
rets = FCAPrescribed("centre", vol=0.15).sample(4_000, 35, seed=11)
POT, TARGET = 800_000, 40_000
both = Household(people=[Person(pot=POT / 2, age=60), Person(pot=POT / 2, age=60)],
                 target_net_income=TARGET, end_age=95)
r_both = simulate_household(both, rets)
solo = Household(people=[Person(pot=POT, age=60)],
                 target_net_income=TARGET, end_age=95)
r_solo = simulate_household(solo, rets)
print(f"  couple, £{POT:,} between them, £{TARGET:,} net : "
      f"success {r_both.success_rate:6.1%}, "
      f"lifetime tax £{np.median(r_both.tax_paid):,.0f}")
print(f"  one person, £{POT:,}, £{TARGET:,} net          : "
      f"success {r_solo.success_rate:6.1%}, "
      f"lifetime tax £{np.median(r_solo.tax_paid):,.0f}")
disc = 0.0 < r_both.success_rate < 1.0 or 0.0 < r_solo.success_rate < 1.0
if not disc:
    fails.append("scenario not discriminating")
print(f"  {'PASS' if disc else 'FAIL'}  scenario is discriminating "
      f"(not all-pass / all-fail)")
ok = np.median(r_both.tax_paid) < np.median(r_solo.tax_paid)
if not ok:
    fails.append("couple should pay less tax")
print(f"  {'PASS' if ok else 'FAIL'}  the couple pays less tax on the same income "
      f"(£{np.median(r_solo.tax_paid) - np.median(r_both.tax_paid):,.0f} less)")

print("\nE. THE SURVIVOR CLIFF")
print("=" * 92)
print(f"{'first death at age':>20}{'success':>10}{'lifetime tax':>15}{'vs no death':>14}")
base = None
for d in [None, 85, 80, 75, 70]:
    hh = Household(
        people=[Person(pot=POT / 2, age=60),
                Person(pot=POT / 2, age=60, dies_at_age=d)],
        target_net_income=TARGET, end_age=95)
    res = simulate_household(hh, rets)
    s = res.success_rate
    if base is None:
        base = s
    lbl = "neither dies" if d is None else str(d)
    print(f"{lbl:>20}{s:>10.1%}£{np.median(res.tax_paid):>13,.0f}"
          f"{(s - base) * 100:>+13.1f}pp")
print("  Note: the survivor spends 33% less, so an earlier death can leave the")
print("  pot in better shape. The cliff is about the survivor's INCOME, not the")
print("  pot's survival — which is why the gross-withdrawal figures below matter.")

print("\n  what the survivor actually loses, in the year after first death")
sp = R.STATE_PENSION_ANNUAL
print(f"        State Pension gone (not inheritable) : £{sp:,.0f}/yr")
print(f"        personal allowance gone              : "
      f"£{R.ASSUMPTIONS['personal_allowance']['value']:,.0f} of tax-free room")
g2 = sum(optimal_split(40_000 - 2 * R.net_income(sp), [sp, sp]))
g1 = R.gross_for_net(40_000 * 0.67 - R.net_income(sp), sp)
print(f"        gross needed before  (couple, £40k)  : £{g2:,.0f}")
print(f"        gross needed after   (survivor, 67%) : £{g1:,.0f}")
print(f"        so spending falls 33% but the pot only gets "
      f"{(1 - g1 / g2) * 100:.0f}% relief")

print("\n" + "=" * 92)
if fails:
    print(f"FAILED {len(fails)}: " + "; ".join(map(str, fails)))
    raise SystemExit(1)
print("ALL CHECKS PASSED")
print("=" * 92)

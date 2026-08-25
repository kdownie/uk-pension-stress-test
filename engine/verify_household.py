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

print("\nF. A PERSON ALREADY DEAD AT THE START TAKES NO TAX-FREE CASH")
print("=" * 92)
# The entitlement dies with the member: an inherited pot passes across whole,
# as drawdown. Without the guard the household is handed 25% of a dead
# partner's pot as money nobody could have taken.
#
# These are DELIBERATELY deterministic checks. pcls_spent=True means any lump
# leaves the household entirely, so the opening balance becomes a direct
# read-out of whether a lump was taken — no Monte Carlo noise to hide behind.
# Only the partner (person B) takes a lump here, so the whole difference
# between the two cases is B's £100,000.
LUMP = R.pcls(400_000)


def _opening(death_age, take_pcls=True):
    hh = Household(
        people=[Person(pot=400_000, age=60, take_pcls=False),
                Person(pot=400_000, age=60, dies_at_age=death_age,
                       take_pcls=take_pcls, pcls_spent=True)],
        target_net_income=TARGET, end_age=95)
    return simulate_household(hh, rets)


dead_at_start = _opening(60)
dies_later = _opening(80)
chk("opening balance, partner dead at the start",
    dead_at_start.balances[0, 0], 800_000.0)
chk("opening balance, partner dies at 80",
    dies_later.balances[0, 0], 800_000.0 - LUMP)
chk("the difference is exactly the lump",
    dead_at_start.balances[0, 0] - dies_later.balances[0, 0], LUMP)

# And the behavioural consequence: for a partner who is already dead,
# take_pcls must make no difference at all to the outcome.
no_pcls = _opening(60, take_pcls=False)
chk("dead-at-start success is unchanged by take_pcls",
    dead_at_start.success_rate * 100, no_pcls.success_rate * 100)

print("\nG. LIFETIME TAX MUST DEPEND ON THE PATH")
print("=" * 92)
# Found 20 August 2026. tax_paid accrued on the withdrawal the household
# INTENDED to make, not on the withdrawal it could actually fund. A path whose
# pot ran dry at 83 went on being charged tax to 95 on money it never took, so
# tax_paid collapsed to a SINGLE value identical on every path — a run that
# failed at 83 and a run that paid out in full to 95 reported the same lifetime
# tax bill.
#
# It survived because nothing compared it. The browser engine does not compute
# lifetime tax at all, so verify_web.py had nothing to cross-check it against —
# the same shape of gap as section F: an output no test ever exercised.
#
# Two guards, and each check pins a different one. Verified by removing them:
#   both removed (the original code) : check 1 FAILS (one distinct value) and
#                                      check 2 FAILS. Exit 1.
#   taken/want factor removed only   : check 1 PASSES — taxing the rescue
#                                      withdrawal alone makes tax path-dependent
#                                      — but check 2 FAILS loudly, reporting
#                                      MORE tax on runs that ran out of money
#                                      than on runs that paid out in full.
# So check 1 alone is not sufficient. Check 2 is the load-bearing one: it states
# a thing that cannot be true of any correct engine.
_g = np.random.default_rng(7).standard_normal((4_000, 35))
_g = (_g - _g.mean()) / _g.std()
_rets = np.expm1(np.log1p(0.0294) + 0.15 * _g)

_hh = Household(
    people=[Person(pot=400_000, age=60, state_pension=R.STATE_PENSION_ANNUAL,
                   sp_age=67),
            Person(pot=400_000, age=60, state_pension=R.STATE_PENSION_ANNUAL,
                   sp_age=67)],
    target_net_income=40_000, end_age=95)
_r = simulate_household(_hh, _rets)
_t, _d = _r.tax_paid, _r.depleted_age

_distinct = len(np.unique(np.round(_t, 2)))
print(f"        distinct lifetime-tax values across 4,000 paths: {_distinct:,}")
if _distinct <= 1:
    fails.append("lifetime tax is identical on every path")
    print(f"  FAIL  lifetime tax varies across paths"
          f"{'':>26} got {_distinct:>14} want          > 1")
else:
    print(f"  PASS  lifetime tax varies across paths"
          f"{'':>26} got {_distinct:>14} want          > 1")

# A run that ran out of money cannot have paid MORE tax than one that funded
# the income in full — it stopped withdrawing, so it stopped being taxed.
if (_d > 0).any() and (_d < 0).any():
    _dry, _ok = float(np.median(_t[_d > 0])), float(np.median(_t[_d < 0]))
    print(f"        median tax, ran out    : £{_dry:,.0f}")
    print(f"        median tax, funded to 95: £{_ok:,.0f}")
    if _dry >= _ok:
        fails.append("depleted paths pay at least as much tax as surviving ones")
        print("  FAIL  depleted paths pay less tax than surviving ones")
    else:
        print("  PASS  depleted paths pay less tax than surviving ones")

# Zero tax must be charged when nothing is ever withdrawn: a household whose
# whole income is covered by two State Pensions touches neither pot.
_free = Household(
    people=[Person(pot=400_000, age=60, state_pension=R.STATE_PENSION_ANNUAL,
                   sp_age=60),
            Person(pot=400_000, age=60, state_pension=R.STATE_PENSION_ANNUAL,
                   sp_age=60)],
    target_net_income=20_000, end_age=95)
chk("no withdrawal needed -> no lifetime tax",
    float(simulate_household(_free, _rets).tax_paid.max()), 0.0)

print("\nH. THE SPLIT MUST DELIVER WHAT IT PROMISES  (regression, 22 Aug 2026)")
print("=" * 92)
# The bug this pins: optimal_split used to sort marginal-rate rungs by rate and
# sum their GROSS capacities. The £100,000-£125,140 allowance taper makes the
# rate sequence 0, 20, 40, 60, 45 — non-monotonic — so the sort put the 45% rung
# (above £125,140) ahead of the 60% rung (below it) and filled a band that
# cannot be reached without first filling the one it skipped. The gross returned
# then under-delivered, and nothing downstream noticed: the engine withdraws the
# gross and counts the year a success either way.
#
# Section B did not catch it for the reason section F was missed — coverage, not
# logic. B's grid stops at £90,000 of need and only ever runs uprate = 1.0, so
# every case sat below the break point. THE FREEZE DIMENSION IS THE POINT: a
# band freeze scales the thresholds down and drags the fault into ordinary
# incomes. At a 35-year freeze it bit at a £30,000 target, which is the default
# on the live page.
_H_CASES = 0
_H_WORST = 0.0
for _region in ("ruk", "scotland"):
    for _yrs in (0, 10, 20, 35):
        _up = 1.0 / (1.03 ** _yrs)
        for _others in ([0.0], [0.0, 0.0], [12_000.0], [12_000.0, 25_000.0],
                        [95_000.0, 0.0], [110_000.0, 5_000.0],
                        [R.STATE_PENSION_ANNUAL, R.STATE_PENSION_ANNUAL]):
            for _need in (5_000, 30_000, 40_000, 60_000, 80_000, 90_000,
                          150_000, 220_000):
                _g = optimal_split(_need, _others, _region, _up)
                _got = sum(R.net_income(o + g, _region, _up)
                           - R.net_income(o, _region, _up)
                           for o, g in zip(_others, _g))
                _H_CASES += 1
                _H_WORST = max(_H_WORST, abs(_got - _need))
print(f"        {_H_CASES} splits across 2 regions x 4 band freezes x 7 income "
      f"profiles x 8 targets")
chk("every split delivers the net it was asked for", _H_WORST, 0.0)

# The two cases that failed loudest before the fix, pinned by name so a
# regression cannot hide inside an aggregate.
for _need, _want_short in ((80_000, 2_027.0), (90_000, 3_771.0)):
    _g = optimal_split(_need, [0.0], "ruk", 1.0)
    _got = R.net_income(_g[0], "ruk", 1.0)
    chk(f"single person, £{_need:,} net, no freeze", _got, float(_need))

# The default target under a long freeze — the case that made this urgent.
_g = optimal_split(30_000, [0.0], "ruk", 1.0 / (1.03 ** 35))
chk("default £30,000 target, 35-year band freeze",
    R.net_income(_g[0], "ruk", 1.0 / (1.03 ** 35)), 30_000.0)

# Optimality, not merely feasibility: no other split may deliver the same net
# for less gross. Brute force on a fine grid, inside the taper zone and under a
# freeze — the region section B never reaches.
_H_EXCESS = 0.0
for _region in ("ruk", "scotland"):
    for _yrs in (0, 20, 35):
        _up = 1.0 / (1.03 ** _yrs)
        for _others in ([0.0, 0.0], [95_000.0, 0.0], [20_000.0, 40_000.0]):
            for _need in (45_000, 90_000, 130_000):
                _mine = sum(optimal_split(_need, _others, _region, _up))
                _best = min(
                    (R.gross_for_net(_need * k / 400, _others[0], _region, _up)
                     if k else 0.0)
                    + (R.gross_for_net(_need - _need * k / 400, _others[1],
                                       _region, _up) if k < 400 else 0.0)
                    for k in range(401))
                _H_EXCESS = max(_H_EXCESS, _mine - _best)
chk("no cheaper split exists (brute force, taper zone + freeze)",
    max(0.0, _H_EXCESS), 0.0, tol=1.0)


print("\nI. WHAT RETAINED TAX-FREE CASH DOES WHILE IT WAITS  (24 Aug 2026)")
print("=" * 92)
# Until 24 Aug 2026 the retained lump sat at 0% while the pots compounded, and
# nothing said so. It is now Household.pcls_held_as, and the point of these
# checks is that the DEFAULT must not have moved anything: "cash" at 0% real is
# the old behaviour, exactly, not approximately.
# Zero volatility, one path -> fully deterministic. The income target is set
# low enough that nothing depletes: a test whose balances are all zero cannot
# tell 1% from 0%, which is how the first draft of this section passed one
# check it should have failed.
_I_RET = np.zeros((1, 35))

def _hh_cash(held, rate):
    return Household(
        people=[Person(pot=400_000, age=60, state_pension=R.STATE_PENSION_ANNUAL,
                       sp_age=67, take_pcls=True, pcls_spent=False)],
        target_net_income=13_000, end_age=95,
        pcls_held_as=held, pcls_cash_real=rate)

# 1. the default is bit-for-bit the old behaviour: with a flat zero return and
#    0% real on the cash, nothing anywhere may grow.
_base = simulate_household(_hh_cash("cash", 0.0), _I_RET)
chk("default (cash, 0% real) — opening balance", float(_base.balances[0, 0]),
    400_000.0)

# 2. a positive cash rate must leave MORE, and an invested pot at zero return
#    must leave the SAME as cash at 0% — the two knobs must not interact.
_c1  = simulate_household(_hh_cash("cash", 0.01), _I_RET)
_inv = simulate_household(_hh_cash("invested", 0.0), _I_RET)
chk("invested at a 0% return == cash at 0% real",
    float(_inv.balances[0, -1]), float(_base.balances[0, -1]))
if float(_c1.balances[0, -1]) <= float(_base.balances[0, -1]):
    fails.append("a positive cash rate did not increase the closing balance")
    print("  FAIL  1% real on cash leaves more than 0%")
else:
    print(f"  PASS  1% real on cash leaves more than 0%              "
          f"{_c1.balances[0,-1]:>13,.2f} vs {_base.balances[0,-1]:>13,.2f}")

# 3. under a real return, "invested" must beat "cash at 0%" — and the gap is
#    the whole reason this setting exists.
_R2 = np.full((1, 35), 0.0294)
_bc = simulate_household(_hh_cash("cash", 0.0), _R2)
_bi = simulate_household(_hh_cash("invested", 0.0), _R2)
if float(_bi.balances[0, -1]) <= float(_bc.balances[0, -1]):
    fails.append("invested tax-free cash did not beat cash at 0% real")
    print("  FAIL  invested beats cash at 0% real under a 2.94% return")
else:
    print(f"  PASS  invested beats cash at 0% real (2.94% return)   "
          f"{_bi.balances[0,-1]:>13,.2f} vs {_bc.balances[0,-1]:>13,.2f}")

# 4. and it must make NO difference at all when there is no retained lump:
#    spend it, or never take it, and the setting is inert. This is the guard
#    against the setting leaking into scenarios it has no business touching.
for _lab, _kw in (("PCLS spent", dict(take_pcls=True, pcls_spent=True)),
                  ("no PCLS taken", dict(take_pcls=False, pcls_spent=False))):
    _a = simulate_household(Household(
            people=[Person(pot=400_000, age=60,
                           state_pension=R.STATE_PENSION_ANNUAL, sp_age=67, **_kw)],
            target_net_income=13_000, end_age=95,
            pcls_held_as="cash", pcls_cash_real=0.0), _R2)
    _b = simulate_household(Household(
            people=[Person(pot=400_000, age=60,
                           state_pension=R.STATE_PENSION_ANNUAL, sp_age=67, **_kw)],
            target_net_income=13_000, end_age=95,
            pcls_held_as="invested", pcls_cash_real=0.03), _R2)
    chk(f"setting is inert when there is no retained lump ({_lab})",
        float(_b.balances[0, -1]), float(_a.balances[0, -1]))


print("\n" + "=" * 92)
if fails:
    print(f"FAILED {len(fails)}: " + "; ".join(map(str, fails)))
    raise SystemExit(1)
print("ALL CHECKS PASSED")
print("=" * 92)

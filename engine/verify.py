"""
Verification. Run this before trusting anything the model says.

Three kinds of check:
  A. Tax layer against figures computed from the legislated rates.
  B. The simulator against a closed-form answer (zero volatility).
  C. The whole thing against a published external result (the 4% rule).

NOTE on wording, 2026-08-20: the section A targets below are computed from the
legislated rates, NOT lifted from a published HMRC table — HMRC publishes no
worked totals at these incomes. Earlier versions marked them [published],
which was a claim nobody could check.
"""

from __future__ import annotations

import numpy as np

import pathlib

import uk_rules as R
from decumulation import Plan, simulate, WITHDRAWAL_ORDERS

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
check("£110,000 (PA tapered to 7,570) [from rates]",
      R.income_tax(110_000), 33_432.0, 0.01)
check("£125,140 (PA fully gone) [from rates]",
      R.income_tax(125_140), 42_516.0, 0.01)
check("£150,000 (additional rate) [from rates]",
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
print("        Bengen's 100% came from Ibbotson US data from 1926 on a 50/50")
print("        portfolio, and is a COUNT of overlapping windows, not a")
print("        probability. On a series compounding at ~4% real, a 4% draw is")
print("        a coin-flip-ish proposition.")
print("        The like-for-like historical check is Pfau (2010), 17 countries")
print("        on Dimson-Marsh-Staunton 1900-2008, best allocation in")
print("        hindsight: US 4.02%, UNITED KINGDOM 3.77%, only 4 of 17 at or")
print("        above 4%. The 4% rule is a fact about a dataset, not a law.")

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

# ==========================================================================
# G. THE VECTORISED TAX CURVE  (uk_rules.tax_curve)
#
# tax_curve interpolates the net-from-gross map on its kinks. Because income
# tax is piecewise linear, that interpolation is not an approximation of the
# tax function — it IS the tax function. This section is what entitles the
# ordering code to rely on it, and it checks against the INDEPENDENT bisection
# in gross_for_net rather than against itself.
# ==========================================================================
print("\nG. THE VECTORISED TAX CURVE  (must invert gross_for_net exactly)")
print("=" * 92)

_worst_inv = _worst_fwd = 0.0
_cases = 0
for _region in ("ruk", "scotland"):
    for _up in (1.0, 1.0 / 1.03 ** 20, 1.0 / 1.03 ** 35):
        for _other in (0.0, 11_502.0, 12_548.0, 25_000.0, 60_000.0,
                       99_000.0, 130_000.0):
            _gk, _nk = R.tax_curve(_other, _region, _up)
            for _tn in (1.0, 5_000.0, 12_570.0, 30_000.0, 47_000.0,
                        80_000.0, 90_000.0, 150_000.0, 300_000.0):
                _cases += 1
                _exact = R.gross_for_net(_tn, _other, _region, _up)
                _g = float(np.interp(_tn, _nk, _gk))
                _worst_inv = max(_worst_inv, abs(_exact - _g))
                _delivered = (R.net_income(_other + _g, _region, _up)
                              - R.net_income(_other, _region, _up))
                _worst_fwd = max(_worst_fwd, abs(_delivered - _tn))
_inv_ok = _worst_inv < 1e-4 and _worst_fwd < 1e-4
if not _inv_ok:
    _failures.append("tax_curve does not match gross_for_net")
print(f"{PASS if _inv_ok else FAIL}  {_cases} cases (both regions, taper zone, "
      f"35-year freeze)")
print(f"        worst inverse error £{_worst_inv:.9f}, "
      f"worst delivery error £{_worst_fwd:.9f}")

# The taper zone is the case that broke optimal_split in 20, so name it.
_gk, _nk = R.tax_curve(99_000.0, "ruk", 1.0)
_g60 = float(np.interp(20_000.0, _nk, _gk))
_taper_ok = abs(_g60 - R.gross_for_net(20_000.0, 99_000.0, "ruk", 1.0)) < 1e-4
if not _taper_ok:
    _failures.append("tax_curve wrong in the taper zone")
print(f"{PASS if _taper_ok else FAIL}  taper zone: £20,000 net on top of "
      f"£99,000 costs £{_g60:,.2f} gross ({1 - 20_000.0/_g60:.1%} effective)")

# ==========================================================================
# H. WITHDRAWAL ORDER  (Plan.withdrawal_order — stage E, 23e/36d)
#
# The measurement discipline here is 10d's, and it is not optional: lifetime
# tax across all paths is CENSORED, because a pot that runs dry stops paying
# tax. Every comparison below is made on a case asserted NOT to deplete.
# ==========================================================================
print("\nH. WITHDRAWAL ORDER")
print("=" * 92)

_R3 = np.full((1, 40), 0.03)


def _ord(order, **kw):
    return simulate(Plan(end_age=95, withdrawal_order=order, **kw), _R3)


def _uncensored(tag, results):
    for _o, _r in results.items():
        if _r.depleted_age[0] > 0:
            _failures.append(f"{tag} censored: {_o} depleted")


# H1. With NO tax-free pool there is only one place to draw from, so every
# order must give BYTE-IDENTICAL results.
_h1 = {o: _ord(o, pot=900_000.0, target_net_income=30_000.0,
               pcls_spent_immediately=True) for o in WITHDRAWAL_ORDERS}
_uncensored("H1", _h1)
_b = [float(r.balances[0, -1]) for r in _h1.values()]
_t = [float(r.tax_paid[0]) for r in _h1.values()]
_h1_ok = max(_b) - min(_b) < 0.01 and max(_t) - min(_t) < 0.01
if not _h1_ok:
    _failures.append("orders differ with no tax-free pool")
print(f"{PASS if _h1_ok else FAIL}  no tax-free pool => all four orders "
      f"coincide  (spread £{max(_b)-min(_b):.6f})")

# H2. The default MUST reproduce the shipped engine, linear `frac` and all.
_d = Plan(pot=500_000.0, target_net_income=30_000.0, end_age=95)
_h2_ok = _d.withdrawal_order == "tax_free_first" and _d.exact_gross_up is False
if not _h2_ok:
    _failures.append("default plan no longer reproduces the shipped engine")
print(f"{PASS if _h2_ok else FAIL}  default is tax_free_first with the shipped "
      f"linear re-grossing")

# H3. An unknown order must be REFUSED, not silently treated as the default.
try:
    Plan(withdrawal_order="cheapest")
    _h3_ok = False
    _failures.append("unknown withdrawal_order accepted")
except ValueError:
    _h3_ok = True
print(f"{PASS if _h3_ok else FAIL}  an unknown order is refused, not silently "
      f"defaulted")

# H4. EFFECT ASSERTION — the order must change the answer where 23b says it
# can, i.e. once the tax-free pools grow. 24c: a parameter both engines ignore
# identically agrees perfectly and means nothing.
_h4 = {o: _ord(o, pot=900_000.0, target_net_income=30_000.0,
               pcls_held_as="invested") for o in WITHDRAWAL_ORDERS}
_uncensored("H4", _h4)
_fin = {o: float(r.balances[0, -1]) for o, r in _h4.items()}
_h4_ok = max(_fin.values()) - min(_fin.values()) > 1_000.0
if not _h4_ok:
    _failures.append("withdrawal_order made no difference")
print(f"{PASS if _h4_ok else FAIL}  the order changes the answer when the "
      f"tax-free pools grow")
for _o in WITHDRAWAL_ORDERS:
    print(f"        {_o:<16} final £{_fin[_o]:>12,.0f}   "
          f"lifetime tax £{_h4[_o].tax_paid[0]:>10,.0f}")

# H5. 23b's finding, re-asserted as a guard: with the tax-free pools at 0%
# real, spending them first is optimal or within a whisker. If a future change
# makes the shipped default look bad on ITS OWN assumptions, that is a bug in
# the change, not a discovery.
_h5 = {o: _ord(o, pot=900_000.0, target_net_income=30_000.0)
       for o in WITHDRAWAL_ORDERS}
_uncensored("H5", _h5)
_ftf = float(_h5["tax_free_first"].balances[0, -1])
_fbest = max(float(r.balances[0, -1]) for r in _h5.values())
_h5_ok = _fbest - _ftf < 0.02 * _ftf
if not _h5_ok:
    _failures.append("tax_free_first no longer near-optimal at 0% real")
print(f"{PASS if _h5_ok else FAIL}  at 0% real on the tax-free pools the "
      f"shipped order is within 2% of the best (23b)")

# H6. 23e's mechanism: fill_allowance earns its advantage BEFORE State Pension
# age and loses it after, because the State Pension fills the allowance itself.
_rb = R.allowance_room(0.0, "ruk", 1.0)
_ra = R.allowance_room(R.STATE_PENSION_ANNUAL, "ruk", 1.0)
_h6_ok = _rb > 12_000.0 and _ra < 100.0
if not _h6_ok:
    _failures.append("allowance room does not collapse at State Pension age")
print(f"{PASS if _h6_ok else FAIL}  allowance room collapses at State Pension "
      f"age: £{_rb:,.0f} -> £{_ra:,.0f}")

# H7. Lifetime tax must be a real read-out, and exact on the shipped path even
# when the pot depletes — the obvious linear version is wrong precisely there.
_dep = _ord("tax_free_first", pot=200_000.0, target_net_income=30_000.0)
_h7_ok = _dep.depleted_age[0] > 0 and _dep.tax_paid[0] > 0
if not _h7_ok:
    _failures.append("tax_paid not reported on a depleting path")
print(f"{PASS if _h7_ok else FAIL}  lifetime tax is reported on a depleting "
      f"path too  (£{_dep.tax_paid[0]:,.0f} to age {_dep.depleted_age[0]:.0f})")

# ==========================================================================
# I. THE PUBLISHED ONS FIGURES  (findings.html section 10, index.html hints)
#
# findings.html says "every figure on this page comes out of code that anyone
# can run". Section 10 publishes figures, so this section is what keeps that
# sentence true. Every number asserted here appears on a public page.
# ==========================================================================
print("\nI. THE PUBLISHED ONS FIGURES")
print("=" * 92)

import statistics as _st
import ons_data as O

# I1. The headline: the triple lock's real value, both constructions. The page
# publishes a RANGE (1.3-1.4%) rather than one number, precisely because the
# choice of price index is a real modelling decision. Assert the range is
# honest — that it brackets both methods rather than being picked from one.
_lockA = list(O.triple_lock_real_uprating("A").values())
_lockB = list(O.triple_lock_real_uprating("B").values())
_mA, _mB = _st.mean(_lockA), _st.mean(_lockB)
_i1_ok = (1.30 <= round(_mA, 2) <= 1.40 and 1.30 <= round(_mB, 2) <= 1.45
          and abs(_mA - _mB) < 0.10)
if not _i1_ok:
    _failures.append("published triple-lock range no longer brackets both methods")
print(f"{PASS if _i1_ok else FAIL}  triple lock real uprating: A {_mA:.2f}%/yr, "
      f"B {_mB:.2f}%/yr, spread {abs(_mA-_mB):.2f}pp")
print(f"        page publishes '1.3-1.4% a year' — brackets both, as it must")

# I2. The medians agree EXACTLY. That is the strongest single statement on the
# page: the answer does not depend on which price index is used.
_medA, _medB = _st.median(_lockA), _st.median(_lockB)
_i2_ok = abs(_medA - _medB) < 1e-9 and abs(_medA - 1.60) < 0.005
if not _i2_ok:
    _failures.append("medians no longer agree at 1.60%")
print(f"{PASS if _i2_ok else FAIL}  medians agree exactly: A {_medA:.2f}%, "
      f"B {_medB:.2f}%  (page says 1.6%)")

# I3. Which leg bound — the counterintuitive half of the finding.
_legs = O.binding_leg("B")
_i3_ok = (_legs["earnings"] == 12 and _legs["prices"] == 8
          and _legs["floor"] == 5)
if not _i3_ok:
    _failures.append(f"binding-leg counts moved: {_legs}")
print(f"{PASS if _i3_ok else FAIL}  binding leg — earnings {_legs['earnings']}, "
      f"prices {_legs['prices']}, 2.5% floor {_legs['floor']}  (page says 12/8/5)")

# I4. The inflation figures quoted beside the slider.
_cpi_era = [O.CPI_ANNUAL_RATE[y] for y in range(1993, 2026)]
_i4_ok = (abs(round(_st.mean(_cpi_era), 1) - 2.5) < 0.001
          and max(_cpi_era) == 9.1 and min(_cpi_era) == 0.0
          and O.CPI_ANNUAL_RATE[2022] == 9.1 and O.CPI_ANNUAL_RATE[2015] == 0.0)
if not _i4_ok:
    _failures.append("CPI figures quoted on the page do not match the series")
print(f"{PASS if _i4_ok else FAIL}  CPI 1993-2025: mean {_st.mean(_cpi_era):.2f}%, "
      f"range {min(_cpi_era):.1f}%-{max(_cpi_era):.1f}%  (page says 2.5%, 0.0-9.1)")

# I5. THE REASON THE MILLENNIUM DATASET IS NOT USED, asserted so that a future
# session cannot quietly revert to it without this test explaining why not.
# That dataset ends in 2016; the inflation assumption depends most on 2022.
_pre2016 = [O.CPI_ANNUAL_RATE[y] for y in range(1993, 2017)]
_i5_ok = max(_pre2016) == 4.5 and max(_cpi_era) == 9.1
if not _i5_ok:
    _failures.append("the 2016-cutoff argument no longer holds")
print(f"{PASS if _i5_ok else FAIL}  data ending 2016 would cap the range at "
      f"{max(_pre2016):.1f}% and miss 2022's {O.CPI_ANNUAL_RATE[2022]:.1f}%")

# I6. The lock can never deliver NEGATIVE real growth — it is a max() against
# prices. So the slider's negative half means something different from its
# positive half, and that is a claim the page makes.
_i6_ok = min(_lockA) >= 0.0 and min(_lockB) >= 0.0
if not _i6_ok:
    _failures.append("triple lock produced negative real uprating — impossible")
print(f"{PASS if _i6_ok else FAIL}  the lock never delivers negative real growth "
      f"(min {min(_lockB):.2f}%) — it is a max() against prices")

# ==========================================================================
print("\nJ. DATED FIGURES — scheduled changes and staleness (26g, 36e.2, 48k)")
print("=" * 92)

import datetime as _dt


def _ok(name, cond, detail=""):
    if not cond:
        _failures.append(name)
    print(f"{PASS if cond else FAIL}  {name:<52} {detail}")


# J1. THE MECHANISM IS INERT BY DEFAULT. Nothing this engine has ever produced
# can move, because _a() is untouched and there are no scheduled entries.
_today = _dt.date.today()
_inert = all(R.value_at(k, _today) == R.ASSUMPTIONS[k]["value"]
             for k in R.ASSUMPTIONS)
_ok("value_at == _a for every figure today", _inert,
    f"{len(R.ASSUMPTIONS)} figures, 0 moved")

# J2. Belt and braces on the three published numbers a reader would check.
_ok("published figures unmoved by the dated layer",
    R.value_at("personal_allowance", _today) == 12_570.0
    and R.value_at("basic_rate_limit", _today) == 50_270.0
    and R.value_at("lump_sum_allowance", _today) == 268_275.0,
    "PA 12,570 / BRL 50,270 / LSA 268,275")

# J3. THE REAL TEST OF THE LOOKUP. A fixture with two scheduled values, listed
# deliberately OUT of date order so the sort is exercised too. If value_at
# ignored `scheduled` entirely, every row below except the first would fail —
# which is the point: J5 alone would not catch that.
R.ASSUMPTIONS["_fixture"] = {
    "value": 100.0,
    "source": "fixture — verify.py J, never shipped as a real figure",
    "checked": "2026-09-03",
    "scheduled": [
        {"from": "2028-04-06", "value": 300.0},   # later one listed FIRST
        {"from": "2027-04-06", "value": 200.0},
    ],
}
try:
    _cases = [("2027-04-05", 100.0, "day before the first change"),
              ("2027-04-06", 200.0, "ON the first change — `from` is inclusive"),
              ("2027-12-31", 200.0, "between the two"),
              ("2028-04-06", 300.0, "ON the second change"),
              ("2030-01-01", 300.0, "after the last change")]
    for _d, _want, _why in _cases:
        _got = R.value_at("_fixture", _d)
        _ok(f"fixture at {_d}", _got == _want, f"{_got:g} — {_why}")

    # J4. scheduled_changes() reports both, in date order, for disclosure.
    _ch = [c for c in R.scheduled_changes() if c["key"] == "_fixture"]
    _ok("scheduled_changes lists both, date-ordered", len(_ch) == 2
        and _ch[0]["from"] < _ch[1]["from"],
        f"{len(_ch)} changes, first {_ch[0]['from'] if _ch else '-'}")

    # J5. DEGENERATE, NOT A TEST (10h). A figure with NO scheduled entries
    # returns its base value — which would also be true if the whole mechanism
    # were deleted. Stated separately so nobody mistakes it for coverage.
    _ok("DEGENERATE, not a test: no schedule => base value",
        R.value_at("personal_allowance", "2099-01-01") == 12_570.0,
        "would pass with value_at() gutted — J3 is the real check")
finally:
    del R.ASSUMPTIONS["_fixture"]

_ok("fixture removed from ASSUMPTIONS", "_fixture" not in R.ASSUMPTIONS,
    "the suite must not leave state behind")

# J6. Errors assert on the MESSAGE, never merely on the exception (10h) —
# 37f is the precedent: a downstream crash imitated a guard perfectly.
def _msg(fn):
    try:
        fn()
    except Exception as e:                                    # noqa: BLE001
        return f"{type(e).__name__}: {e}"
    return ""


_e1 = _msg(lambda: R.value_at("no_such_figure", "2027-01-01"))
_ok("unknown figure is refused by name", "no such assumption" in _e1, _e1[:44])
_e2 = _msg(lambda: R.value_at("personal_allowance", "6 April 2027"))
_ok("a non-ISO date is refused", "YYYY-MM-DD" in _e2, _e2[:44])
_e3 = _msg(lambda: R.value_at("personal_allowance", 2027))
_ok("an int is refused, not silently coerced", "TypeError" in _e3, _e3[:44])

# J7. The expiry is DERIVED from tax_year, not hard-coded — proved by moving
# tax_year and watching it follow. A hard-coded date would fail this row.
_real_ty = R.ASSUMPTIONS["tax_year"]["value"]
try:
    R.ASSUMPTIONS["tax_year"]["value"] = "2031/32"
    _derived = R.figures_expire_on() == _dt.date(2032, 4, 5)
finally:
    R.ASSUMPTIONS["tax_year"]["value"] = _real_ty
_ok("expiry follows tax_year, so it cannot drift from it", _derived,
    f"'2031/32' -> 2032-04-05; real: {R.figures_expire_on().isoformat()}")

# J8. THE STALENESS TRIPWIRE — the mechanism's one REAL consumer, firing on a
# real date against real figures. This row is DESIGNED to go red once the tax
# year turns. That is not a bug in the suite: it is the whole point, and the
# message says so. 41d — a warning that cannot fire is one switched off where
# nobody will notice.
_current = R.figures_are_current()
_ok("figures are the tax year in force", _current, R.staleness_note()[:70])

# J8b. AND THE TRIPWIRE CAN ACTUALLY FIRE. The row above passes today whether
# or not the check works — a stubbed `return True` would satisfy it — so it is
# not evidence on its own. This one asks the question at a date PAST expiry,
# where the answer must flip. 41d: a warning that cannot fire is not a safe
# warning, it is one switched off where nobody will notice.
_past = _dt.date(R.figures_expire_on().year + 1, 4, 6)
_fires = (not R.figures_are_current(_past)) and \
         R.staleness_note(_past).startswith("STALE:")
_ok("the tripwire fires once the tax year turns", _fires,
    f"at {_past.isoformat()}: {R.staleness_note(_past)[:38]}")
# And the boundary itself: in force ON the last day, stale the next morning.
_edge = (R.figures_are_current(R.figures_expire_on())
         and not R.figures_are_current(
             R.figures_expire_on() + _dt.timedelta(days=1)))
# J9. THE SAME FIGURE LIVES IN THREE FILES (10f). uk_rules now guards its own
# staleness, but `tax_year` is also written into README.md and index.html, and
# nothing held them together — which is exactly 10f's shape: a claim stated in
# two places needs a test holding them, or one of them goes stale alone.
# Resolved relative to this file, as verify_web does, so it runs anywhere.
_root = pathlib.Path(__file__).resolve().parent.parent
_ty = str(R.ASSUMPTIONS["tax_year"]["value"])
for _rel in ("README.md", "public/index.html"):
    _f = _root / _rel
    # A missing file must FAIL, never skip: a check that quietly skips is a
    # check that proves nothing (10i).
    _found = _f.exists() and _ty in _f.read_text(encoding="utf-8")
    _ok(f"{_rel} carries tax year {_ty}", _found,
        "present" if _found else ("FILE MISSING" if not _f.exists()
                                  else f"{_ty} not found — it has gone stale"))

_ok("in force on the last day, stale the next", _edge,
    f"{R.figures_expire_on().isoformat()} / "
    f"{(R.figures_expire_on() + _dt.timedelta(days=1)).isoformat()}")
if not _current:
    print("         ^ NOT an arithmetic failure. Re-check the ASSUMPTIONS block "
          "against GOV.UK,")
    print("           update the values and their 'checked' dates, and move "
          "tax_year forward.")

print("\n" + "=" * 92)
if _failures:
    print(f"FAILED {len(_failures)} check(s): " + "; ".join(_failures))
    raise SystemExit(1)
print("ALL CHECKS PASSED")
print("=" * 92)

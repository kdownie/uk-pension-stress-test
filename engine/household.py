"""
Household decumulation: one person or a couple, with the survivor cliff.

WHY THIS MATTERS MORE THAN IT LOOKS
-----------------------------------
Two State Pensions is the obvious part. Two PERSONAL ALLOWANCES is the part
that actually moves the number: a couple can pull roughly £25,140 a year out
of their pensions before a penny of income tax, where a single person gets
£12,570.

And the risk nobody models: on first death the household loses one State
Pension permanently — the new State Pension is based on your own NI record
and is NOT inheritable (only half of any "protected payment" passes across).
It loses one personal allowance too. But the survivor's living costs do not
halve. That gap is the survivor cliff, and it lands on whichever partner is
least able to do anything about it.

Sources:
  https://www.gov.uk/new-state-pension/inheriting-or-increasing-state-pension-from-a-spouse-or-civil-partner
  https://www.gov.uk/scottish-income-tax
Checked 2026-08-15.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

import uk_rules as R


# --------------------------------------------------------------------------
# Tax-optimal income splitting
# --------------------------------------------------------------------------

def _breakpoints(region: str, uprate: float) -> list[float]:
    """
    Total-income levels where the marginal rate changes.

    Includes the £100,000–£125,140 taper zone, where losing 50p of allowance
    per extra £1 creates an effective marginal rate far above the headline
    one (60% in rUK, 62%+ in Scotland). Any splitting rule that ignores that
    zone will happily push a partner into it.
    """
    reg = R.REGIONS[region]
    pa = R.ASSUMPTIONS["personal_allowance"]["value"] * uprate
    bps = [0.0, pa]
    x = pa
    for width, _ in reg["bands"]:
        if width is None:
            break
        x += width * uprate
        bps.append(x)
    bps += [R.ASSUMPTIONS["pa_taper_threshold"]["value"] * uprate,
            reg["top_from"] * uprate]
    return sorted(set(b for b in bps if b >= 0))


def _segments(other_income: float, region: str, uprate: float,
              ceiling: float = 400_000.0):
    """
    Ladder of (marginal_rate, capacity) rungs available to one person,
    starting from whatever taxable income they already have.
    """
    bps = [b for b in _breakpoints(region, uprate) if b > other_income]
    bps.append(ceiling)
    segs, lo = [], other_income
    for hi in bps:
        if hi <= lo:
            continue
        mid = (lo + hi) / 2
        rate = R.marginal_rate(mid, region, uprate, step=1.0)
        segs.append([rate, hi - lo])
        lo = hi
    return segs


def optimal_split(need_net: float, others: list[float], region: str = "ruk",
                  uprate: float = 1.0) -> list[float]:
    """
    Gross withdrawal for each person that delivers `need_net` in total, at
    the lowest possible household tax bill.

    Because income tax is progressive, every extra pound costs at least as
    much as the last. So filling the cheapest rungs across BOTH people first
    is optimal — no search required, just a sort.

    Returns one gross figure per person, in the order given.
    """
    if need_net <= 0:
        return [0.0] * len(others)

    ladder = []
    for i, o in enumerate(others):
        for rate, cap in _segments(o, region, uprate):
            ladder.append((rate, cap, i))
    ladder.sort(key=lambda s: s[0])

    gross = [0.0] * len(others)
    remaining = need_net
    for rate, cap, i in ladder:
        if remaining <= 1e-9:
            break
        net_here = cap * (1.0 - rate)
        if net_here <= remaining:
            gross[i] += cap
            remaining -= net_here
        else:
            gross[i] += remaining / (1.0 - rate) if rate < 1 else 0.0
            remaining = 0.0
    return gross


# --------------------------------------------------------------------------
# Model
# --------------------------------------------------------------------------

@dataclass
class Person:
    pot: float = 250_000.0
    age: int = 60
    state_pension: float = R.STATE_PENSION_ANNUAL
    sp_age: int = 67
    other_income: float = 0.0          # DB pension etc., real terms
    dies_at_age: int | None = None     # None = survives the whole projection
    take_pcls: bool = True
    pcls_spent: bool = False


@dataclass
class Household:
    people: list[Person]
    target_net_income: float = 40_000.0     # while everyone is alive
    survivor_fraction: float = 0.67         # see note below
    end_age: int = 95                       # of person[0]
    region: str = "ruk"
    band_freeze_years: int = 0
    assumed_inflation: float = 0.03

    # survivor_fraction: a one-person household does not cost half a
    # two-person one — rent, heating, council tax and car do not halve.
    # 0.67 is the OECD-modified equivalence scale (1.0 + 0.5 for a second
    # adult, so the survivor needs 1/1.5). It is an assumption, and it is
    # exposed so it can be argued with.

    @property
    def years(self) -> int:
        return self.end_age - self.people[0].age


@dataclass
class HouseholdResult:
    hh: Household
    balances: np.ndarray
    depleted_age: np.ndarray
    success_rate: float
    tax_paid: np.ndarray
    first_death_year: int | None

    def summary(self) -> str:
        out = [f"  success rate                  : {self.success_rate:6.1%}",
               f"  median lifetime tax paid      : "
               f"£{np.median(self.tax_paid):,.0f}"]
        d = self.depleted_age[self.depleted_age > 0]
        if len(d):
            out.append(f"  median age the pot runs dry   : {np.median(d):.0f}")
        return "\n".join(out)


def simulate_household(hh: Household, annual_returns: np.ndarray
                       ) -> HouseholdResult:
    n_paths, avail = annual_returns.shape
    years = hh.years
    if avail < years:
        raise ValueError(f"need {years} years of returns, got {avail}")
    r = annual_returns[:, :years]
    n_people = len(hh.people)

    pots = np.array([[p.pot for p in hh.people]] * n_paths, dtype=float)
    cash = np.zeros(n_paths)
    for j, p in enumerate(hh.people):
        # A person already dead when the projection starts takes no tax-free
        # cash. The entitlement dies with the member: the pot passes across
        # whole, as inherited drawdown. Without this guard the household is
        # handed 25% of a dead partner's pot as money nobody could have taken,
        # which flatters the success rate by ~2pp. Mirrors bDeadAtStart in
        # public/index.html — the two engines must agree here.
        dead_at_start = p.dies_at_age is not None and p.age >= p.dies_at_age
        if p.take_pcls and not dead_at_start:
            lump = R.pcls(p.pot)
            pots[:, j] -= lump
            if not p.pcls_spent:
                cash += lump

    balances = np.empty((n_paths, years + 1))
    balances[:, 0] = pots.sum(axis=1) + cash
    depleted = np.full(n_paths, -1)
    tax_paid = np.zeros(n_paths)
    first_death_year = None

    for y in range(years):
        base_age = hh.people[0].age + y
        uprate = 1.0 / ((1.0 + hh.assumed_inflation)
                        ** min(y, hh.band_freeze_years))

        # Track indices explicitly. Person is a dataclass, so two partners with
        # identical fields compare EQUAL — people.index(p) would return 0 for
        # both and quietly drain one pot while the other sat untouched.
        idx, others = [], []
        for j, p in enumerate(hh.people):
            a = p.age + (base_age - hh.people[0].age)
            if p.dies_at_age is not None and a >= p.dies_at_age:
                continue
            idx.append(j)
            others.append(p.other_income + (p.state_pension
                                            if a >= p.sp_age else 0.0))
        alive = idx
        if not alive:
            balances[:, y + 1] = balances[:, y]
            continue
        if len(alive) < n_people and first_death_year is None:
            first_death_year = y

        target = (hh.target_net_income if len(alive) == n_people
                  else hh.target_net_income * hh.survivor_fraction)
        net_from_other = sum(R.net_income(o, hh.region, uprate) for o in others)
        need_net = max(0.0, target - net_from_other)

        splits = optimal_split(need_net, others, hh.region, uprate)

        # Tax-free cash first: no tax, so it stretches furthest.
        from_cash = np.minimum(cash, need_net)
        cash -= from_cash
        frac = np.where(need_net > 0,
                        (need_net - from_cash) / max(need_net, 1e-9), 0.0)

        # On first death the deceased's pot passes to the survivor and is
        # pooled — pensions normally sit outside the estate and can be kept
        # in drawdown by a nominated beneficiary.
        if len(alive) < n_people:
            keep = idx[0]
            for j in range(n_people):
                if j != keep:
                    pots[:, keep] += pots[:, j]
                    pots[:, j] = 0.0

        shortfall = np.zeros(n_paths)
        for k, j in enumerate(idx):
            want = splits[k] * frac
            taken = np.minimum(pots[:, j], want)
            pots[:, j] -= taken
            shortfall += want - taken
            # Tax is charged on what was ACTUALLY withdrawn, not on what the
            # household intended to withdraw. Without the `taken/want` factor a
            # path whose pot ran dry at 83 keeps accruing tax to 95 on money it
            # never took, and tax_paid collapses to a single number identical on
            # every path — which is exactly how this was found. The `* frac`
            # term is the existing linear-in-withdrawal approximation for the
            # tax-free-cash mechanic; this factor is the same idea applied to a
            # pot that could not deliver the full split.
            taken_frac = np.where(want > 1e-9, taken / np.maximum(want, 1e-9), 0.0)
            tax_paid += (R.income_tax(others[k] + splits[k], hh.region, uprate)
                         - R.income_tax(others[k], hh.region, uprate)) * frac * taken_frac

        # If one pot ran dry, try the others before declaring failure. That
        # rescue withdrawal is taxable too, and charging it is what stops a
        # couple looking artificially cheap: it lands on TOP of the donor's own
        # split, so it is charged at the donor's marginal rate there, computed
        # once per person per year rather than per path.
        if len(idx) > 1:
            marginal = []
            for k, j in enumerate(idx):
                at = others[k] + splits[k]
                step = 1.0
                marginal.append(
                    (R.income_tax(at + step, hh.region, uprate)
                     - R.income_tax(at, hh.region, uprate)) / step)
            for k, j in enumerate(idx):
                if not shortfall.any():
                    break
                take = np.minimum(pots[:, j], shortfall)
                pots[:, j] -= take
                shortfall -= take
                tax_paid += take * marginal[k]

        newly_dry = (shortfall > 1e-6) & (depleted < 0)
        depleted[newly_dry] = base_age

        pots *= (1.0 + r[:, y])[:, None]
        np.maximum(pots, 0.0, out=pots)
        balances[:, y + 1] = pots.sum(axis=1) + cash

    return HouseholdResult(
        hh=hh, balances=balances, depleted_age=depleted,
        success_rate=float((depleted < 0).mean()), tax_paid=tax_paid,
        first_death_year=first_death_year,
    )

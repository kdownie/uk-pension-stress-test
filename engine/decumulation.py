"""
UK decumulation simulator.

Everything is in REAL (today's-money) terms. Returns are real, the income
target is real, and by default tax bands are assumed to rise with inflation.
That last assumption is a choice, not a fact — see `band_freeze_years`.

Order of events within each year (stated because it changes the answer by
roughly 0.2-0.4pp of success rate and every calculator hides it):
    1. State pension received, if in payment (taxable)
    2. Income drawn from the pot to top up to the target, grossed up for tax
    3. Whatever is left in the pot earns that year's return

Drawing BEFORE the return is the conservative convention: the money spent
is not exposed to that year's growth.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

import uk_rules as R


@dataclass
class Plan:
    pot: float = 500_000.0
    retire_age: int = 60
    end_age: int = 100
    target_net_income: float = 30_000.0      # real, per year, after tax
    state_pension_age: int = 67
    state_pension_annual: float = R.STATE_PENSION_ANNUAL
    take_pcls: bool = True
    pcls_spent_immediately: bool = False     # if False, PCLS is held as cash
    # What retained tax-free cash DOES while it waits. Until 24 Aug 2026 the
    # answer was "nothing", silently: the lump sat at 0% nominal while the
    # pension compounded. That is an assumption, not a fact, and it was not
    # disclosed anywhere. It is now a choice.
    #   "cash"     — held as savings, earning pcls_cash_real in REAL terms.
    #                0.0 is the textbook cash assumption (keeps pace with
    #                inflation, no more) and reproduces the pre-2026-08-24
    #                behaviour exactly.
    #   "invested" — rides the same return path as the pension, which is what
    #                someone who moves it into an ISA and invests it gets.
    pcls_held_as: str = "cash"               # "cash" | "invested"
    pcls_cash_real: float = 0.0              # real return on retained cash
    other_taxable_income: float = 0.0        # e.g. a DB pension, real terms
    band_freeze_years: int = 0               # years bands stay nominally frozen
    region: str = "ruk"                      # "ruk" or "scotland"
    assumed_inflation: float = 0.03          # only used for the band freeze

    @property
    def years(self) -> int:
        return self.end_age - self.retire_age


@dataclass
class Result:
    plan: Plan
    engine_name: str
    balances: np.ndarray          # (n_paths, years+1) end-of-year pot
    depleted_age: np.ndarray      # age when pot hit zero, or -1
    shortfall: np.ndarray         # (n_paths,) total real income not delivered
    returns: np.ndarray

    @property
    def n_paths(self) -> int:
        return self.balances.shape[0]

    @property
    def success_rate(self) -> float:
        """Fraction of paths that delivered the full income to end_age."""
        return float((self.depleted_age < 0).mean())

    def depletion_quantiles(self, qs=(0.05, 0.25, 0.50)):
        d = self.depleted_age[self.depleted_age > 0]
        if len(d) == 0:
            return {}
        return {q: float(np.quantile(d, q)) for q in qs}

    def summary(self) -> str:
        p = self.plan
        lines = [
            f"{self.engine_name}",
            f"  success rate (income to age {p.end_age}) : {self.success_rate:6.1%}",
        ]
        fails = self.depleted_age > 0
        if fails.any():
            dq = self.depletion_quantiles()
            lines.append(
                f"  of the {fails.sum():,} failures, pot ran dry at age: "
                f"{dq[0.05]:.0f} (worst 5%) / {dq[0.25]:.0f} (25th) / "
                f"{dq[0.50]:.0f} (median)"
            )
            lines.append(
                f"  median real income shortfall when it fails    : "
                f"£{np.median(self.shortfall[fails]):,.0f}"
            )
        final = self.balances[:, -1]
        lines.append(
            f"  real pot at age {p.end_age} — 10th/50th/90th pct : "
            f"£{np.quantile(final,0.10):,.0f} / £{np.quantile(final,0.50):,.0f} "
            f"/ £{np.quantile(final,0.90):,.0f}"
        )
        return "\n".join(lines)


def _band_uprating(plan: Plan, year: int) -> float:
    """Real-terms scale factor on tax thresholds for a given year."""
    frozen = min(year, plan.band_freeze_years)
    return 1.0 / ((1.0 + plan.assumed_inflation) ** frozen)


def simulate(plan: Plan, annual_returns: np.ndarray,
             engine_name: str = "") -> Result:
    """
    annual_returns: (n_paths, years) real simple returns.
    """
    n_paths, years = annual_returns.shape
    if years < plan.years:
        raise ValueError(f"need {plan.years} years of returns, got {years}")
    r = annual_returns[:, :plan.years]

    pot = np.full(n_paths, float(plan.pot))
    cash = np.zeros(n_paths)

    if plan.take_pcls:
        lump = R.pcls(plan.pot)
        pot -= lump
        if not plan.pcls_spent_immediately:
            cash += lump

    balances = np.empty((n_paths, plan.years + 1))
    balances[:, 0] = pot + cash
    depleted = np.full(n_paths, -1)
    shortfall = np.zeros(n_paths)

    # Gross-up is a scalar solve per (year, other-income) combination, not
    # per path, so we cache it. This is what makes 20k paths x 40 years cheap.
    gross_cache: dict[tuple[int, float], float] = {}

    for y in range(plan.years):
        age = plan.retire_age + y
        uprate = _band_uprating(plan, y)

        other = plan.other_taxable_income
        if age >= plan.state_pension_age:
            other += plan.state_pension_annual

        net_from_other = R.net_income(other, plan.region, uprate)
        need_net = max(0.0, plan.target_net_income - net_from_other)

        key = (y, other)
        if key not in gross_cache:
            gross_cache[key] = R.gross_for_net(need_net, other,
                                               plan.region, uprate)
        gross_needed = gross_cache[key]

        # Tax-free cash is spent first — no tax, so it stretches furthest.
        from_cash = np.minimum(cash, need_net)
        cash -= from_cash
        still_net = need_net - from_cash
        # Re-gross only the remaining net requirement. The linear scaling is
        # exact when from_cash is 0 or the whole need; between those it is a
        # simplification. Disclosed in uk_rules.LIMITATIONS — an earlier
        # version of this comment claimed that and it was not true, which is
        # its own kind of bug: a comment asserting a disclosure nobody wrote.
        frac = np.where(need_net > 0, still_net / np.maximum(need_net, 1e-9), 0.0)
        draw = gross_needed * frac

        taken = np.minimum(pot, draw)
        unmet = draw - taken
        shortfall += unmet
        pot -= taken

        newly_dry = (pot <= 1e-6) & (cash <= 1e-6) & (depleted < 0) & (unmet > 0)
        depleted[newly_dry] = age

        pot *= (1.0 + r[:, y])
        pot = np.maximum(pot, 0.0)
        # Retained tax-free cash grows too — see Plan.pcls_held_as.
        if plan.pcls_held_as == "invested":
            cash = cash * (1.0 + r[:, y])
        elif plan.pcls_cash_real:
            cash = cash * (1.0 + plan.pcls_cash_real)
        balances[:, y + 1] = pot + cash

    return Result(plan=plan, engine_name=engine_name, balances=balances,
                  depleted_age=depleted, shortfall=shortfall, returns=r)

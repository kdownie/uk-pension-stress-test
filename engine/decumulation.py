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


# Withdrawal orders. See Plan.withdrawal_order. Mirrors WITHDRAWAL_ORDERS in
# public/index.html — the two engines must agree, and 10c is the reason: a
# constant only one engine can express is a constant nobody is checking.
WITHDRAWAL_ORDERS = ("tax_free_first", "fill_allowance",
                     "proportional", "pension_first")


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
    # State Pension growth ABOVE inflation, per year, compounding from the start
    # of the projection. 0.0 reproduces the behaviour shipped before 25 August
    # 2026 — which was not a neutral choice but the silent assumption that the
    # triple lock ends immediately and the State Pension is thereafter uprated
    # by CPI exactly, for the whole horizon. Current policy is the triple lock:
    # the higher of CPI, average earnings growth, or 2.5%. Worth ~5.7pp at
    # 0.75%/yr on the default scenario. Mirrors spGrowth in public/index.html.
    sp_real_growth: float = 0.0
    # STAGE D — an ISA as a STARTING asset (34e). A second tax-free pool, held
    # from the outset rather than created by taking tax-free cash.
    #
    # It carries its OWN treatment rather than inheriting pcls_held_as, and that
    # is a measured decision, not a preference: a retained lump sum in a bank
    # account beside an invested ISA is an ordinary household, and one shared
    # control cannot express it. Forcing it wrong costs 2-23pp (34d).
    #
    # DEFAULT IS "invested", unlike pcls_held_as which defaults to "cash".
    # Nobody holds an ISA at 0% real by choice, and inheriting that default
    # would make a user entering their true position watch the answer FALL.
    #
    # HOUSEHOLD-LEVEL, NOT PER-PERSON, deliberately (34g). Ownership buys the
    # GBP20,000 subscription cap and the death rules (APS, the three-year
    # continuing-account window) and nothing else, and both are stage G. The JS
    # is household-level too; keeping them the same avoids adding a second
    # degree of freedom one engine cannot express.
    isa: float = 0.0                         # tax-free starting balance
    isa_held_as: str = "invested"            # "cash" | "invested"
    isa_real: float = 0.0                    # real return when held as cash
    # STAGE E — WITHDRAWAL ORDER (23b, 23e, 36d). Which pool is spent first.
    #
    #   "tax_free_first"  retained tax-free cash, then ISA, then pension.
    #                     THE SHIPPED ORDER and the default. Reproduces
    #                     behaviour before 31 August 2026 exactly.
    #   "fill_allowance"  draw from the PENSION up to the personal allowance
    #                     first — that slice is taxed at 0% — then tax-free
    #                     pools, then the pension again. 23e: this wins before
    #                     State Pension age and does almost nothing after it,
    #                     because the State Pension fills the allowance itself.
    #   "proportional"    draw from every pool pro rata to its SPENDABLE value
    #                     (the pension counted net of the tax it would bear).
    #   "pension_first"   pension, then tax-free cash, then ISA.
    #
    # 23b: ordering is worth NOTHING while tax-free money earns nothing — a
    # pot at 0% real is a depreciating asset, so spending it first is
    # unambiguously right. It became worth something only when 24 and 35 let
    # the two tax-free pools grow. Do not quote an ordering figure without
    # stating the growth assumption it was measured under.
    withdrawal_order: str = "tax_free_first"
    # Whether the taxable withdrawal is re-grossed EXACTLY when tax-free money
    # covers part of the year's requirement, or scaled linearly as the shipped
    # engine does (`frac` below; 23c prices the difference at ~0.1pp).
    #
    # False reproduces shipped behaviour and is only available for
    # "tax_free_first"; the other orders require exact re-grossing and set
    # this themselves. See the note on `frac` in the loop.
    exact_gross_up: bool = False

    def __post_init__(self):
        if self.withdrawal_order not in WITHDRAWAL_ORDERS:
            raise ValueError(
                f"withdrawal_order must be one of {WITHDRAWAL_ORDERS}, "
                f"got {self.withdrawal_order!r}")
        # An order other than the shipped one cannot use the linear `frac`
        # scaling: fill_allowance deliberately aims at a particular tax band,
        # and scaling a whole-year gross-up linearly would not respect it.
        if self.withdrawal_order != "tax_free_first":
            self.exact_gross_up = True

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
    # Lifetime income tax paid on pension withdrawals, per path. Added with
    # the withdrawal orders (36d), because tax is the whole measurable
    # consequence of the ordering choice in the absence of a care event —
    # and because 15c's rule cuts the other way here: lifetime tax existed
    # only in household.py, so for a single person nobody was checking it.
    tax_paid: np.ndarray = None

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
    isa = np.zeros(n_paths) + plan.isa

    if plan.take_pcls:
        lump = R.pcls(plan.pot)
        pot -= lump
        if not plan.pcls_spent_immediately:
            cash += lump

    balances = np.empty((n_paths, plan.years + 1))
    balances[:, 0] = pot + cash + isa
    depleted = np.full(n_paths, -1)
    shortfall = np.zeros(n_paths)

    # Gross-up is a scalar solve per (year, other-income) combination, not
    # per path, so we cache it. This is what makes 20k paths x 40 years cheap.
    gross_cache: dict[tuple[int, float], float] = {}
    # The same idea for the exact path: the (gross, net) knots depend only on
    # (year, other income), never on the path, so they are solved once too.
    curve_cache: dict[tuple[int, float], tuple] = {}
    tax_paid = np.zeros(n_paths)

    for y in range(plan.years):
        age = plan.retire_age + y
        uprate = _band_uprating(plan, y)

        other = plan.other_taxable_income
        if age >= plan.state_pension_age:
            other += plan.state_pension_annual * (
                (1.0 + plan.sp_real_growth) ** y)

        net_from_other = R.net_income(other, plan.region, uprate)
        need_net = max(0.0, plan.target_net_income - net_from_other)

        key = (y, other)
        if key not in gross_cache:
            gross_cache[key] = R.gross_for_net(need_net, other,
                                               plan.region, uprate)
        gross_needed = gross_cache[key]

        if not plan.exact_gross_up:
            # ---------- THE SHIPPED PATH, unchanged ----------
            # Tax-free cash is spent first — no tax, so it stretches furthest.
            from_cash = np.minimum(cash, need_net)
            cash -= from_cash
            # The ISA is drawn AFTER retained tax-free cash and BEFORE the
            # pension. Placing it second keeps isa = 0 identical to the
            # shipped engine.
            from_isa = np.minimum(isa, need_net - from_cash)
            isa -= from_isa
            still_net = need_net - from_cash - from_isa
            # Re-gross only the remaining net requirement. The linear scaling
            # is exact when from_cash is 0 or the whole need; between those it
            # is a simplification. Disclosed in uk_rules.LIMITATIONS — an
            # earlier version of this comment claimed that and it was not
            # true, which is its own kind of bug: a comment asserting a
            # disclosure nobody wrote.
            frac = np.where(need_net > 0,
                            still_net / np.maximum(need_net, 1e-9), 0.0)
            draw = gross_needed * frac

            taken = np.minimum(pot, draw)
            unmet = draw - taken
            shortfall += unmet
            pot -= taken
            # Tax is a READ-OUT here, not a driver: it is reported, never fed
            # back into the balances, so computing it exactly cannot disturb
            # the shipped path. Doing so matters — the obvious linear version
            # (scale the year's tax by taken/draw) is wrong precisely on the
            # paths that deplete, because net-from-gross is not linear in the
            # gross drawn. That put a spurious £0.42 between this path and the
            # exact one in a case where the two are identical by construction.
            if key not in curve_cache:
                curve_cache[key] = tuple(
                    np.asarray(a, dtype=float)
                    for a in R.tax_curve(other, plan.region, uprate))
            _gk, _nk = curve_cache[key]
            tax_paid += taken - np.interp(taken, _gk, _nk)
        else:
            # ---------- EXACT RE-GROSSING, and the ordering strategies ------
            # Every pension draw below stacks on the ones before it in the
            # same year, so the gross needed for an EXTRA slice of net depends
            # on what has already been drawn. That is why the pension draw is
            # tracked cumulatively and re-solved on the cumulative curve
            # rather than slice by slice: drawing 5k then 5k more is not two
            # independent 5k draws, and treating it as such would understate
            # the tax on the second.
            if key not in curve_cache:
                curve_cache[key] = tuple(
                    np.asarray(a, dtype=float)
                    for a in R.tax_curve(other, plan.region, uprate))
            gk, nk = curve_cache[key]

            pot_gross = np.zeros(n_paths)   # cumulative gross drawn this year
            pot_net = np.zeros(n_paths)     # cumulative net it delivered

            def draw_pension(want_net, cap_net=None):
                """Take an EXTRA `want_net` of net income from the pension."""
                nonlocal pot, pot_gross, pot_net
                w = np.maximum(want_net, 0.0)
                if cap_net is not None:
                    w = np.minimum(w, np.maximum(cap_net, 0.0))
                target_gross = np.interp(pot_net + w, nk, gk)
                taken = np.minimum(pot, np.maximum(target_gross - pot_gross,
                                                   0.0))
                pot -= taken
                pot_gross += taken
                new_net = np.interp(pot_gross, gk, nk)
                delivered = new_net - pot_net
                pot_net = new_net
                return delivered

            def draw_free(pool, want_net):
                """Take from a tax-free pool. Returns (taken, new balance)."""
                t = np.minimum(pool, np.maximum(want_net, 0.0))
                return t, pool - t

            got = np.zeros(n_paths)         # net delivered so far this year
            order = plan.withdrawal_order

            if order == "fill_allowance":
                # The 0%-rate slice of the pension first. Once the State
                # Pension is in payment this room is near zero, which is 23e:
                # the best order changes at State Pension age.
                room = R.allowance_room(other, plan.region, uprate)
                got += draw_pension(need_net - got, cap_net=room)
                t, cash = draw_free(cash, need_net - got); got += t
                t, isa = draw_free(isa, need_net - got); got += t
                got += draw_pension(need_net - got)
            elif order == "pension_first":
                got += draw_pension(need_net - got)
                t, cash = draw_free(cash, need_net - got); got += t
                t, isa = draw_free(isa, need_net - got); got += t
            elif order == "proportional":
                # Pro rata by SPENDABLE value, not by balance: a pound in the
                # pension is worth less than a pound in an ISA, and weighting
                # by face value would quietly over-draw the pension.
                v_pot = np.interp(pot, gk, nk)
                total = cash + isa + v_pot
                safe = np.maximum(total, 1e-9)
                got += draw_pension(need_net * v_pot / safe)
                t, cash = draw_free(cash, need_net * cash / safe); got += t
                t, isa = draw_free(isa, need_net * isa / safe); got += t
                # A pool that could not deliver its share leaves a residual;
                # mop it up in the default order rather than failing early.
                t, cash = draw_free(cash, need_net - got); got += t
                t, isa = draw_free(isa, need_net - got); got += t
                got += draw_pension(need_net - got)
            else:   # "tax_free_first", exactly re-grossed
                t, cash = draw_free(cash, need_net - got); got += t
                t, isa = draw_free(isa, need_net - got); got += t
                got += draw_pension(need_net - got)

            unmet_net = np.maximum(need_net - got, 0.0)
            # Shortfall stays in GROSS terms, as on the shipped path: the
            # gross that would have been needed to deliver what was missed.
            shortfall += np.maximum(
                np.interp(pot_net + unmet_net, nk, gk) - pot_gross, 0.0)
            tax_paid += pot_gross - pot_net
            unmet = unmet_net

        newly_dry = ((pot <= 1e-6) & (cash <= 1e-6) & (isa <= 1e-6)
                     & (depleted < 0) & (unmet > 0))
        depleted[newly_dry] = age

        pot *= (1.0 + r[:, y])
        pot = np.maximum(pot, 0.0)
        # Retained tax-free cash grows too — see Plan.pcls_held_as.
        if plan.pcls_held_as == "invested":
            cash = cash * (1.0 + r[:, y])
        elif plan.pcls_cash_real:
            cash = cash * (1.0 + plan.pcls_cash_real)
        # The ISA grows by its OWN rule, never by pcls_held_as.
        if plan.isa_held_as == "invested":
            isa = isa * (1.0 + r[:, y])
        elif plan.isa_real:
            isa = isa * (1.0 + plan.isa_real)
        balances[:, y + 1] = pot + cash + isa

    return Result(plan=plan, engine_name=engine_name, balances=balances,
                  depleted_age=depleted, shortfall=shortfall, returns=r,
                  tax_paid=tax_paid)

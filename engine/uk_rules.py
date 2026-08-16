"""
UK pension and income tax rules — the deliberately boring, auditable layer.

DESIGN RULE: every number that comes from legislation lives in ASSUMPTIONS
below, with a source URL and the date it was checked. Nothing is hard-coded
further down. If a figure is not in that block with a source, it does not
belong in this file.

Scope: England, Wales and Northern Ireland. Scotland has different income
tax bands and is NOT modelled here — see LIMITATIONS.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# ASSUMPTIONS  — all figures checked against GOV.UK on 2026-08-15
# --------------------------------------------------------------------------

ASSUMPTIONS = {
    "tax_year": {
        "value": "2026/27",
        "note": "6 April 2026 to 5 April 2027",
        "source": "https://www.gov.uk/income-tax-rates",
        "checked": "2026-08-15",
    },
    "personal_allowance": {
        "value": 12_570.0,
        "source": "https://www.gov.uk/income-tax-rates",
        "checked": "2026-08-15",
    },
    "pa_taper_threshold": {
        "value": 100_000.0,
        "note": "PA reduced by £1 for every £2 of adjusted net income above this",
        "source": "https://www.gov.uk/income-tax-rates",
        "checked": "2026-08-15",
    },
    "basic_rate_limit": {
        "value": 50_270.0,
        "note": "top of the 20% band, measured as total income",
        "source": "https://www.gov.uk/income-tax-rates",
        "checked": "2026-08-15",
    },
    "higher_rate_limit": {
        "value": 125_140.0,
        "note": "top of the 40% band; PA is fully tapered away at this point",
        "source": "https://www.gov.uk/income-tax-rates",
        "checked": "2026-08-15",
    },
    "rates": {
        "value": {"basic": 0.20, "higher": 0.40, "additional": 0.45},
        "source": "https://www.gov.uk/income-tax-rates",
        "checked": "2026-08-15",
    },
    "state_pension_weekly": {
        "value": 241.30,
        "note": "full NEW State Pension. Assumes a full NI record — many people "
                "get less. £241.30 x 52 = £12,547.60/yr, which sits just under "
                "the £12,570 personal allowance.",
        "source": "https://www.gov.uk/new-state-pension/what-youll-get",
        "checked": "2026-08-15",
    },
    "lump_sum_allowance": {
        "value": 268_275.0,
        "note": "cash cap on total tax-free lump sums. Higher if protection held.",
        "source": "https://www.gov.uk/guidance/find-out-the-rules-around-individual-lump-sum-allowances",
        "checked": "2026-08-15",
    },
    "pcls_fraction": {
        "value": 0.25,
        "note": "standard 25% tax-free pension commencement lump sum, subject "
                "to the lump sum allowance cap above",
        "source": "https://www.gov.uk/tax-on-pension",
        "checked": "2026-08-15",
    },
}

LIMITATIONS = [
    "Scotland: different income tax bands, not modelled.",
    "No National Insurance — not charged on pension income, so correct here, "
    "but wrong the moment earned income is added.",
    "No MPAA, annual allowance or taper — this is a decumulation model only.",
    "No DB pensions, annuities, or death benefits.",
    "No pension IHT treatment.",
    "Tax bands assumed to move with inflation by default. That is NOT current "
    "policy — see freeze_bands_until in DecumulationParams.",
    "Full State Pension assumed if state_pension_weekly is left at default. "
    "Most people should check an actual forecast at "
    "https://www.gov.uk/check-state-pension.",
]


def _a(key: str):
    return ASSUMPTIONS[key]["value"]


STATE_PENSION_ANNUAL = _a("state_pension_weekly") * 52.0


# --------------------------------------------------------------------------
# REGIONS
#
# Both GOV.UK tables present bands as income RANGES, which silently assumes a
# full personal allowance. The real mechanics are band WIDTHS stacked on top of
# whatever allowance survives the £100k taper. Widths are what we store.
#
# Scotland sets rates on non-savings non-dividend income, which is what pension
# income is. The personal allowance itself stays UK-wide and tapers identically.
# --------------------------------------------------------------------------

REGIONS = {
    "ruk": {
        "label": "England, Wales & Northern Ireland",
        # (width above the allowance, rate). Final entry: width None = to the
        # additional-rate threshold, then top_rate applies above it.
        "bands": [(37_700.0, 0.20), (None, 0.40)],
        "top_rate": 0.45,
        "top_from": 125_140.0,
        "source": "https://www.gov.uk/income-tax-rates",
        "checked": "2026-08-15",
    },
    "scotland": {
        "label": "Scotland",
        "bands": [
            (3_967.0, 0.19),    # starter    12,571–16,537
            (12_989.0, 0.20),   # basic      16,538–29,526
            (14_136.0, 0.21),   # intermediate 29,527–43,662
            (31_338.0, 0.42),   # higher     43,663–75,000
            (None, 0.45),       # advanced   75,001–125,140
        ],
        "top_rate": 0.48,       # top        above 125,140
        "top_from": 125_140.0,
        "source": "https://www.gov.uk/scottish-income-tax",
        "checked": "2026-08-15",
    },
}


# --------------------------------------------------------------------------
# Income tax
# --------------------------------------------------------------------------

def personal_allowance(taxable_income: float) -> float:
    """Personal allowance after the £100k taper."""
    pa = _a("personal_allowance")
    threshold = _a("pa_taper_threshold")
    if taxable_income <= threshold:
        return pa
    return max(0.0, pa - (taxable_income - threshold) / 2.0)


def income_tax(taxable_income: float, region: str = "ruk",
               band_uprating: float = 1.0) -> float:
    """
    Income tax due on `taxable_income` (England/Wales/NI, pension income).

    NOTE ON MECHANICS — this is the bit most naive implementations get wrong.
    GOV.UK presents the bands as income ranges (£12,571-£50,270 at 20%) which
    silently assumes a full personal allowance. The actual mechanics are:
    the basic rate BAND is £37,700 wide and sits on top of whatever personal
    allowance you have left. So once the allowance tapers away above £100k,
    the 40% band starts LOWER, not at £50,270.

    Getting this wrong understates tax on £100k-£125k income by about £5,000
    — precisely the range a large pot in drawdown can hit.

    Checked against published figures: £110,000 -> £33,432, £150,000 -> £53,703.

    band_uprating scales every threshold. Used to model band freezes in a
    real-terms model: if bands are frozen in nominal terms and inflation has
    been 20% cumulatively, pass band_uprating=1/1.20 to shrink them in real
    terms. Pass 1.0 (default) for bands that keep pace with inflation.
    """
    if taxable_income <= 0.0:
        return 0.0

    reg = REGIONS[region]
    pa = personal_allowance(taxable_income / band_uprating) * band_uprating
    top_from = reg["top_from"] * band_uprating

    tax = 0.0
    lower = pa
    for width, rate in reg["bands"]:
        upper = top_from if width is None else lower + width * band_uprating
        upper = min(upper, top_from)
        seg = min(taxable_income, upper) - lower
        if seg > 0:
            tax += seg * rate
        lower = upper
        if taxable_income <= lower:
            return tax
    if taxable_income > top_from:
        tax += (taxable_income - top_from) * reg["top_rate"]
    return tax


def marginal_rate(taxable_income: float, region: str = "ruk",
                  band_uprating: float = 1.0, step: float = 1.0) -> float:
    """Tax on the next £1. Used to decide which partner should draw next."""
    return (income_tax(taxable_income + step, region, band_uprating)
            - income_tax(taxable_income, region, band_uprating)) / step


def net_income(taxable_income: float, region: str = "ruk",
               band_uprating: float = 1.0) -> float:
    return taxable_income - income_tax(taxable_income, region, band_uprating)


def gross_for_net(target_net: float, other_taxable: float = 0.0,
                  region: str = "ruk", band_uprating: float = 1.0,
                  tol: float = 1e-7) -> float:
    """
    Gross taxable withdrawal needed so that (withdrawal + other_taxable),
    after tax, leaves `target_net` net from the withdrawal itself.

    Solved by bisection: tax is monotonic non-decreasing in income, so net
    income is monotonic increasing and the root is unique.
    """
    if target_net <= 0.0:
        return 0.0

    base_net = net_income(other_taxable, region, band_uprating)

    def shortfall(gross: float) -> float:
        total_net = net_income(other_taxable + gross, region, band_uprating)
        return (total_net - base_net) - target_net

    lo, hi = 0.0, max(target_net * 2.0, 1.0)
    # Expand upper bound until it overshoots (45% top rate => <2.5x is enough,
    # but the taper region can need more).
    guard = 0
    while shortfall(hi) < 0.0:
        hi *= 2.0
        guard += 1
        if guard > 200:
            raise RuntimeError("gross_for_net failed to bracket a solution")

    while hi - lo > tol:
        mid = (lo + hi) / 2.0
        if shortfall(mid) < 0.0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


# --------------------------------------------------------------------------
# Tax-free cash
# --------------------------------------------------------------------------

def pcls(pot: float, allowance_used: float = 0.0) -> float:
    """
    Tax-free pension commencement lump sum available from `pot`:
    25% of the pot, capped by remaining lump sum allowance.
    """
    headroom = max(0.0, _a("lump_sum_allowance") - allowance_used)
    return min(pot * _a("pcls_fraction"), headroom)


def describe_assumptions() -> str:
    lines = [f"UK RULES — tax year {_a('tax_year')} "
             f"(England/Wales/NI), checked 2026-08-15", ""]
    for k, v in ASSUMPTIONS.items():
        val = v["value"]
        val = f"{val:,.2f}" if isinstance(val, float) else str(val)
        lines.append(f"  {k:<24} {val}")
        if "note" in v:
            lines.append(f"  {'':<24} note: {v['note']}")
        lines.append(f"  {'':<24} src:  {v['source']}")
    lines += ["", "NOT MODELLED:"]
    lines += [f"  - {x}" for x in LIMITATIONS]
    return "\n".join(lines)


if __name__ == "__main__":
    print(describe_assumptions())

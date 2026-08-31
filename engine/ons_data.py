"""
ONS series used to source the two policy assumptions on the page.

WHY THIS FILE EXISTS
--------------------
findings.html says "every figure on this page comes out of code that anyone can
run". Section 10 of that page publishes a figure — what the triple lock has been
worth in real terms — so the data behind it has to be here, or that sentence
stops being true. This is the file that keeps it true.

WHY ONS AND NOT THE BANK OF ENGLAND'S MILLENNIUM DATASET (37/38)
----------------------------------------------------------------
The plan of record (32f) was to source these ranges from the Millennium dataset,
for which a non-commercial permission was obtained in August 2026. Two reasons
it is not used here:

  1. IT ENDS IN 2016. The inflation assumption depends most on 2022, when CPI
     hit 9.1%. Sourced from Millennium data the range would top out at 4.5% —
     and the page's own hint text already names 2022. The dataset cannot see
     the observation that matters.
  2. LICENCE. The Bank's permission is non-commercial; this repository is MIT,
     which grants commercial rights. Shipping Bank data here would mean
     sublicensing on terms the author does not hold (27c). ONS publishes under
     the Open Government Licence v3.0, which permits commercial use and
     redistribution with attribution, so the conflict does not arise and no
     download-script or data carve-out is needed.

ATTRIBUTION, required by the OGL and reproduced on both public pages:
    Contains public sector information licensed under the Open Government
    Licence v3.0.  https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/

All three series retrieved 31 August 2026.
"""

from __future__ import annotations

# ONS series D7G7 — "CPI ANNUAL RATE 00: ALL ITEMS 2015=100", per cent, annual.
# Dataset MM23.
# https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/d7g7/mm23
CPI_ANNUAL_RATE = {
    1989: 5.2, 1990: 7.0, 1991: 7.5, 1992: 4.2, 1993: 2.5, 1994: 2.0,
    1995: 2.6, 1996: 2.4, 1997: 1.8, 1998: 1.6, 1999: 1.3, 2000: 0.8,
    2001: 1.2, 2002: 1.3, 2003: 1.4, 2004: 1.3, 2005: 2.1, 2006: 2.3,
    2007: 2.3, 2008: 3.6, 2009: 2.2, 2010: 3.3, 2011: 4.5, 2012: 2.8,
    2013: 2.6, 2014: 1.5, 2015: 0.0, 2016: 0.7, 2017: 2.7, 2018: 2.5,
    2019: 1.8, 2020: 0.9, 2021: 2.6, 2022: 9.1, 2023: 7.3, 2024: 2.5,
    2025: 3.4,
}

# ONS series KAB9 — "AWE: Whole Economy Level (£): Seasonally Adjusted Total Pay
# Excluding Arrears", annual. Dataset EMP. NOMINAL, and published rounded to
# whole pounds — which is why it is not used alone (see METHOD B below).
# https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/earningsandworkinghours/timeseries/kab9/emp
AWE_NOMINAL = {
    2000: 313, 2001: 329, 2002: 339, 2003: 350, 2004: 365, 2005: 382,
    2006: 400, 2007: 420, 2008: 434, 2009: 434, 2010: 444, 2011: 455,
    2012: 461, 2013: 466, 2014: 471, 2015: 482, 2016: 494, 2017: 505,
    2018: 520, 2019: 538, 2020: 547, 2021: 580, 2022: 616, 2023: 659,
    2024: 694, 2025: 728,
}

# ONS series A2FD — "AWE: Whole Economy Real Terms Index: Seasonally Adjusted
# Total Pay", 2015 = 100, annual. Dataset EMP. ONS deflates this by CPIH.
# https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/earningsandworkinghours/timeseries/a2fd/emp
AWE_REAL_INDEX = {
    2000: 88.4, 2001: 91.5, 2002: 93.0, 2003: 94.7, 2004: 97.5, 2005: 99.9,
    2006: 102.0, 2007: 104.5, 2008: 104.5, 2009: 102.4, 2010: 102.2,
    2011: 100.8, 2012: 99.6, 2013: 98.4, 2014: 98.0, 2015: 100.0,
    2016: 101.4, 2017: 101.1, 2018: 101.8, 2019: 103.5, 2020: 104.3,
    2021: 107.8, 2022: 106.1, 2023: 106.3, 2024: 108.4, 2025: 109.4,
}

TRIPLE_LOCK_FLOOR = 2.5    # per cent, the third leg of the lock


def real_earnings_growth(method: str = "A") -> dict[int, float]:
    """
    Growth in average earnings ABOVE prices, per cent per year.

    Two constructions, because the choice of price index is a real modelling
    decision and the honest thing is to show it does not change the answer:

      "A"  from A2FD, the real-terms index ONS publishes. ONS deflates it by
           CPIH, so this mixes CPIH-deflated earnings with the CPI series used
           everywhere else on the page.
      "B"  nominal earnings (KAB9) less CPI (D7G7). One price index throughout,
           at the cost of KAB9's whole-pound rounding.

    Neither is obviously right. They differ by 0.09pp on the mean and agree
    exactly on the median — see verify.py section I.
    """
    if method == "A":
        ys = sorted(AWE_REAL_INDEX)
        return {y: (AWE_REAL_INDEX[y] / AWE_REAL_INDEX[y - 1] - 1) * 100.0
                for y in ys[1:]}
    if method == "B":
        ys = sorted(AWE_NOMINAL)
        return {y: (AWE_NOMINAL[y] / AWE_NOMINAL[y - 1] - 1) * 100.0
                   - CPI_ANNUAL_RATE[y]
                for y in ys[1:] if y in CPI_ANNUAL_RATE}
    raise ValueError("method must be 'A' or 'B'")


def triple_lock_real_uprating(method: str = "A") -> dict[int, float]:
    """
    Growth above inflation the triple lock formula delivers, per cent per year.

    The lock uprates by the higher of prices, earnings or 2.5%, so the growth
    ABOVE prices is  max(0, real earnings growth, 2.5% - inflation).

    NOTE this is the FORMULA applied to the data, not the policy as enacted:
    the triple lock began in 2011 and was suspended for 2022-23. Applying it
    back to 2001 measures what the rule delivers on this data, not what
    pensioners actually received. Stated on findings.html as well.
    """
    g = real_earnings_growth(method)
    return {y: max(0.0, g[y], TRIPLE_LOCK_FLOOR - CPI_ANNUAL_RATE[y])
            for y in sorted(g) if y in CPI_ANNUAL_RATE}


def binding_leg(method: str = "B") -> dict[str, int]:
    """Which leg of the lock set the uprating, counted over the period."""
    g = real_earnings_growth(method)
    out = {"earnings": 0, "prices": 0, "floor": 0}
    for y, v in triple_lock_real_uprating(method).items():
        if v <= 1e-9:
            out["prices"] += 1
        elif abs(v - g[y]) < 1e-9:
            out["earnings"] += 1
        else:
            out["floor"] += 1
    return out

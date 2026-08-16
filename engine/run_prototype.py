"""
The comparison run.

Two working engines on the same plan, same seed budget, same everything:

  A. Historical bootstrap (5-year blocks)  — PRESERVES sequence structure
  B. Parametric GBM via neural_sde         — DESTROYS sequence structure
                                              (i.i.d. lognormal, which is what
                                              essentially every free calculator
                                              uses under the bonnet)

Both are calibrated to the SAME underlying data, and both land on ~4.0% real
geometric return. So any difference in outcome is caused by path shape alone,
not by a different return assumption. That is the experiment.

The neural engine is excluded — see FINDINGS.md for the diagnostic.
"""

from __future__ import annotations

import json

import numpy as np

import uk_rules as R
from decumulation import Plan, simulate
from returns import HistoricalBootstrap, load_history

N_PATHS = 20_000
SEED = 20260815

print("=" * 78)
print(R.describe_assumptions())
print("=" * 78)

daily, annual = load_history()
boot = HistoricalBootstrap(annual, block_years=5)

from neural_sde import fit, forecast
gbm = fit(daily, dt=1 / 252, model="gbm")


def gbm_annual(n_paths: int, n_years: int, seed: int) -> np.ndarray:
    fc = forecast(gbm, horizon=n_years * 252, n_paths=n_paths,
                  antithetic=True, engine="exact", seed=seed)
    p = np.asarray(fc.paths)
    if p.shape[0] != n_paths:
        p = p.T
    y = p[:, ::252][:, :n_years + 1]
    return y[:, 1:] / y[:, :-1] - 1.0


plan = Plan(
    pot=500_000, retire_age=60, end_age=95,
    target_net_income=30_000, state_pension_age=67,
    take_pcls=True, pcls_spent_immediately=False,
)

print("\nPLAN")
print(f"  pot £{plan.pot:,.0f}, retire at {plan.retire_age}, "
      f"target £{plan.target_net_income:,.0f} net real to age {plan.end_age}")
print(f"  State Pension £{plan.state_pension_annual:,.0f} from age "
      f"{plan.state_pension_age}")
print(f"  tax-free cash taken at outset: £{R.pcls(plan.pot):,.0f} "
      f"(held as cash, spent first)")

r_boot = boot.sample(N_PATHS, plan.years, seed=SEED)
r_gbm = gbm_annual(N_PATHS, plan.years, SEED)

print("\nRETURN ENGINES — calibrated to the same data")
for nm, r in [("Historical bootstrap", r_boot), ("Parametric GBM", r_gbm)]:
    geo = np.expm1(np.log1p(np.clip(r, -0.99, None)).mean())
    # Serial correlation of squared returns = volatility clustering.
    x = r - r.mean()
    ac1 = float(np.mean([np.corrcoef(p[:-1] ** 2, p[1:] ** 2)[0, 1]
                         for p in x[:2000]]))
    print(f"  {nm:<22} geometric {geo:+.2%}   sd {r.std():.2%}   "
          f"vol-clustering (autocorr of r^2) {ac1:+.3f}")

res_b = simulate(plan, r_boot, "A. Historical bootstrap (sequence preserved)")
res_g = simulate(plan, r_gbm, "B. Parametric GBM (sequence destroyed)")

print("\n" + "=" * 78)
print("RESULTS")
print("=" * 78)
for res in (res_b, res_g):
    print(res.summary())
    print()

gap = res_g.success_rate - res_b.success_rate
print(f"  >>> The i.i.d. model is {gap:+.1%} more optimistic about this plan.")
print("      Same return assumption. Same tax. Same everything but path shape.")

# ---------------------------------------------------------------- sweep
print("\n" + "=" * 78)
print("SUSTAINABLE INCOME — where the two engines disagree")
print("=" * 78)
print(f"{'target net income':>19} {'bootstrap':>11} {'GBM':>9} {'gap':>8}")
sweep = []
for target in range(18_000, 42_001, 2_000):
    p = Plan(**{**plan.__dict__, "target_net_income": float(target)})
    a = simulate(p, r_boot).success_rate
    b = simulate(p, r_gbm).success_rate
    sweep.append({"target": target, "bootstrap": a, "gbm": b})
    print(f"{target:>19,} {a:>10.1%} {b:>8.1%} {b - a:>+8.1%}")


def safe_income(engine_returns, conf=0.90):
    lo, hi = 5_000.0, 80_000.0
    for _ in range(40):
        mid = (lo + hi) / 2
        p = Plan(**{**plan.__dict__, "target_net_income": mid})
        if simulate(p, engine_returns).success_rate >= conf:
            lo = mid
        else:
            hi = mid
    return lo


si_b, si_g = safe_income(r_boot), safe_income(r_gbm)
print(f"\n  Income sustainable at 90% confidence:")
print(f"    bootstrap : £{si_b:,.0f} net real")
print(f"    GBM       : £{si_g:,.0f} net real   "
      f"(£{si_g - si_b:,.0f} more, on identical return assumptions)")

# ------------------------------------------------------- fiscal drag
print("\n" + "=" * 78)
print("FISCAL DRAG — what a nominal band freeze costs (bootstrap engine)")
print("=" * 78)
drag = []
for yrs in [0, 5, 10, 20, plan.years]:
    p = Plan(**{**plan.__dict__, "band_freeze_years": yrs})
    s = simulate(p, r_boot).success_rate
    drag.append({"freeze_years": yrs, "success": s})
    lbl = "no freeze (bands track inflation)" if yrs == 0 else \
          f"bands frozen {yrs} years"
    print(f"  {lbl:<40} success {s:6.1%}")

json.dump(
    {
        "plan": {k: v for k, v in plan.__dict__.items()},
        "n_paths": N_PATHS,
        "headline": {
            "bootstrap_success": res_b.success_rate,
            "gbm_success": res_g.success_rate,
            "safe_income_bootstrap": si_b,
            "safe_income_gbm": si_g,
        },
        "sweep": sweep,
        "fiscal_drag": drag,
        "fan_bootstrap": {
            str(q): np.quantile(res_b.balances, q, axis=0).tolist()
            for q in (0.05, 0.25, 0.50, 0.75, 0.95)
        },
        "fan_gbm": {
            str(q): np.quantile(res_g.balances, q, axis=0).tolist()
            for q in (0.05, 0.25, 0.50, 0.75, 0.95)
        },
    },
    open("results.json", "w"), indent=1,
)
print("\nwrote results.json")

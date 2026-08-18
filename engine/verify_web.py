"""
Cross-verification: the JavaScript engine in tool/index.html must agree with
the Python engine that verify.py already validates.

Two independent implementations of the same rules is only useful if they are
actually checked against each other — otherwise it is two chances to be wrong.
"""
import asyncio, json, pathlib
from playwright.async_api import async_playwright

# Resolve index.html relative to this file so the check runs anywhere the
# repository is cloned, not just on the machine it was written on.
PAGE = (pathlib.Path(__file__).resolve().parent.parent / "public" / "index.html").as_uri()

import uk_rules as R
from decumulation import Plan, simulate
import numpy as np

fails = []


def chk(name, got, want, tol=0.01):
    ok = abs(got - want) <= tol
    if not ok:
        fails.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name:<50} js {got:>14,.2f}  py {want:>14,.2f}")


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page()
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        await pg.goto(PAGE)
        await pg.wait_for_timeout(1500)

        print("=" * 86)
        print("A. JS TAX FUNCTION vs PYTHON (which is verified against GOV.UK figures)")
        print("=" * 86)
        for inc in [0, 12_570, 20_000, 50_270, 60_000, 99_000, 110_000,
                    125_140, 150_000, 300_000]:
            js = await pg.evaluate(f"incomeTax({inc},1,'ruk')")
            chk(f"income tax on £{inc:,}", js, R.income_tax(inc))

        print("\nB. JS TAX WITH FROZEN BANDS (uprate < 1)")
        print("=" * 86)
        for inc, up in [(30_000, 0.8), (60_000, 0.7), (120_000, 0.6)]:
            js = await pg.evaluate(f"incomeTax({inc},{up},'ruk')")
            chk(f"£{inc:,} at uprate {up}", js, R.income_tax(inc, "ruk", up))

        print("\nC. JS GROSS-UP")
        print("=" * 86)
        for tgt, oth in [(10_000, 0), (30_000, 0), (30_000, 12_548), (80_000, 0),
                         (25_000, 100_000)]:
            js = await pg.evaluate(f"grossForNet({tgt},{oth},1,'ruk')")
            chk(f"net £{tgt:,} on top of £{oth:,}", js, R.gross_for_net(tgt, oth))

        print("\nD. TAX-FREE CASH")
        print("=" * 86)
        for pot in [400_000, 1_073_100, 1_500_000]:
            js = await pg.evaluate(f"pcls({pot})")
            chk(f"PCLS on £{pot:,}", js, R.pcls(pot))

        print("\nE. FULL SIMULATION — zero volatility, must match the closed form")
        print("=" * 86)
        cfg = dict(pot=1_000_000, retire=60, end=90, target=25_000, sp=0, spAge=200,
                   other=0, takePcls=False, pclsSpend=False, real=0.04, vol=0.0,
                   conv="geo", freeze=0, paths=200, couple=False, region="ruk",
                   pot2=0, retire2=0, sp2=0, spAge2=200, other2=0, deathAge=0,
                   survFrac=0.67)
        js = await pg.evaluate(
            "cfg => { const r = simulate(cfg); "
            "return {end: r.bal[(r.years+1)-1], succ: r.successRate}; }", cfg)
        pot = 1_000_000.0
        gross = R.gross_for_net(25_000, 0.0)
        for _ in range(30):
            pot = (pot - min(pot, gross)) * 1.04
        chk("final pot after 30y at 4% real", js["end"], pot, 1.0)
        chk("success rate", js["succ"], 1.0, 1e-9)

        print("\nF. FULL SIMULATION — stochastic, vs Python on identical assumptions")
        print("=" * 86)
        for tgt in [24_000, 30_000, 36_000]:
            c = dict(pot=500_000, retire=60, end=95, target=tgt, sp=12_548,
                     spAge=67, other=0, takePcls=True, pclsSpend=False,
                     real=0.0294, vol=0.15, conv="geo", freeze=0, paths=20_000,
                     couple=False, region="ruk", pot2=0, retire2=0, sp2=0,
                     spAge2=200, other2=0, deathAge=0, survFrac=0.67)
            jsr = await pg.evaluate("cfg => simulate(cfg).successRate", c)
            plan = Plan(pot=500_000, retire_age=60, end_age=95,
                        target_net_income=tgt, state_pension_age=67,
                        state_pension_annual=12_548, take_pcls=True)
            rng = np.random.default_rng(7)
            z = rng.standard_normal((20_000, 35)); z = (z - z.mean()) / z.std()
            rets = np.expm1(np.log1p(0.0294) + 0.15 * z)
            pyr = simulate(plan, rets).success_rate
            # Different RNG streams, so agreement is statistical: the standard
            # error on 20k paths is ~0.35pp, so 1.5pp is a generous 4-sigma band.
            chk(f"success at £{tgt:,} net (±1.5pp MC tolerance)",
                jsr * 100, pyr * 100, 1.5)

        print("\nF2. SCOTLAND — JS vs PYTHON")
        print("=" * 86)
        for inc in [20_000, 30_000, 50_000, 75_000, 125_140, 150_000]:
            js = await pg.evaluate(f"incomeTax({inc},1,'scotland')")
            chk(f"Scottish tax on £{inc:,}", js, R.income_tax(inc, "scotland"))

        print("\nF3. TAX-OPTIMAL SPLIT — JS vs PYTHON")
        print("=" * 86)
        from household import optimal_split
        for region in ("ruk", "scotland"):
            for need, oth in [(30_000, [0, 0]), (30_000, [12_548, 12_548]),
                              (60_000, [12_548, 0]), (90_000, [0, 30_000])]:
                js = await pg.evaluate(
                    "a => optimalSplit(a[0],a[1],a[2],1)", [need, oth, region])
                py = optimal_split(need, [float(x) for x in oth], region)
                chk(f"{region} split of £{need:,} — partner A", js[0], py[0], 0.5)
                chk(f"{region} split of £{need:,} — partner B", js[1], py[1], 0.5)

        print("\nF4. DEATH SCENARIOS — JS vs PYTHON (the gap that hid a real bug)")
        print("=" * 86)
        # Every couple case above passes deathAge=0, so until this section
        # existed the cross-check had never once exercised a death. That is how
        # the dead-at-start tax-free-cash bug survived two engines: two
        # implementations only help on the paths you actually compare.
        from household import Household, Person, simulate_household

        def _py_couple(death_age, pcls_spent=False, vol=0.15, paths=20_000):
            hh = Household(
                people=[Person(pot=400_000, age=60, state_pension=12_548,
                               sp_age=67, take_pcls=True,
                               pcls_spent=pcls_spent),
                        Person(pot=400_000, age=60, state_pension=12_548,
                               sp_age=67, take_pcls=True,
                               pcls_spent=pcls_spent,
                               dies_at_age=death_age)],
                target_net_income=40_000, survivor_fraction=0.67, end_age=95)
            rng = np.random.default_rng(7)
            z = rng.standard_normal((paths, 35))
            z = (z - z.mean()) / z.std()
            rets = np.expm1(np.log1p(0.0294) + vol * z)
            return simulate_household(hh, rets)

        def _js_cfg(death_age, pcls_spend=False, vol=0.15, paths=20_000):
            return dict(pot=400_000, retire=60, end=95, target=40_000,
                        sp=12_548, spAge=67, other=0, takePcls=True,
                        pclsSpend=pcls_spend, real=0.0294, vol=vol,
                        conv="geo", freeze=0, paths=paths, couple=True,
                        region="ruk", pot2=400_000, retire2=60, sp2=12_548,
                        spAge2=67, other2=0, deathAge=death_age or 0,
                        survFrac=0.67)

        for label, death_age in [("neither dies", None),
                                 ("partner dies at 80", 80),
                                 ("partner dead at the start", 60)]:
            jsr = await pg.evaluate("cfg => simulate(cfg).successRate",
                                    _js_cfg(death_age))
            pyr = _py_couple(death_age).success_rate
            chk(f"couple success, {label} (±1.5pp MC)",
                jsr * 100, pyr * 100, 1.5)

        # The Monte Carlo checks above WOULD have caught the bug, but by only
        # 0.15pp on the seed that was tried — a different seed might not have.
        # So pin it deterministically as well: zero volatility, and
        # pclsSpend=True so any lump leaves the household. The opening balance
        # then reads out directly whether a dead partner's lump was taken, and
        # a wrong answer shows up as a flat £100,000, not as noise.
        js_open = await pg.evaluate(
            "cfg => simulate(cfg).bal[0]",
            _js_cfg(60, pcls_spend=True, vol=0.0, paths=1))
        py_open = _py_couple(60, pcls_spent=True, vol=0.0,
                             paths=1).balances[0, 0]
        chk("opening balance, partner dead at start (deterministic)",
            js_open, py_open, 1.0)
        chk("...and it equals pot less ONE lump, not two",
            js_open, 800_000.0 - R.pcls(400_000), 1.0)

        print("\nG. PAGE HEALTH")
        print("=" * 86)
        for sel, label in [("#s_succ", "success rate"), ("#s_safe", "safe income"),
                           ("#s_dep", "depletion age")]:
            txt = await pg.evaluate(f"document.querySelector('{sel}').textContent")
            ok = txt.strip() not in ("", "—")
            if not ok:
                fails.append(label)
            print(f"  {'PASS' if ok else 'FAIL'}  {label:<50} rendered as {txt!r}")
        for sel in ["#fan svg", "#curve svg"]:
            n = await pg.evaluate(f"document.querySelectorAll('{sel}').length")
            ok = n == 1
            if not ok:
                fails.append(sel)
            print(f"  {'PASS' if ok else 'FAIL'}  {sel:<50} {n} rendered")
        real_errors = [e for e in errors if "favicon" not in e.lower()]
        if real_errors:
            fails.append("console errors")
            print(f"  FAIL  console/page errors: {real_errors[:3]}")
        else:
            print(f"  PASS  {'no console or page errors':<50}")

        await b.close()

    print("\n" + "=" * 86)
    if fails:
        print(f"FAILED {len(fails)}: " + "; ".join(fails))
        raise SystemExit(1)
    print("JS AND PYTHON ENGINES AGREE — ALL CHECKS PASSED")
    print("=" * 86)


asyncio.run(main())

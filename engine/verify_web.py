"""
Cross-verification: the JavaScript engine in tool/index.html must agree with
the Python engine that verify.py already validates.

Two independent implementations of the same rules is only useful if they are
actually checked against each other — otherwise it is two chances to be wrong.
"""
import asyncio, json, pathlib, re, dataclasses, inspect
from playwright.async_api import async_playwright

# Resolve index.html relative to this file so the check runs anywhere the
# repository is cloned, not just on the machine it was written on.
PAGE = (pathlib.Path(__file__).resolve().parent.parent / "public" / "index.html").as_uri()

import uk_rules as R
from decumulation import Plan, simulate
# 41a. The return convention is expressed ONCE, in returns.py, and used both
# by the shipped generator and by this harness — so this file checks the
# engine rather than checking a formula it wrote out for itself (10f).
from returns import lognormal_real, standard_normals, FCAPrescribed
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
            z = standard_normals(20_000, 35, 7)
            rets = lognormal_real(0.0294, 0.15, z, "geo")
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

        # The four cases above all sit below £100,000 of total income and all
        # pass uprate=1, so none of them reaches the personal-allowance taper.
        # That is the same blind spot section B of verify_household.py had, and
        # it is why THIS cross-check could not see the 22 Aug split bug: with a
        # fixed JS and a reverted Python the F3 grid above still agreed on every
        # case. Two engines only help on the inputs you actually compare — and a
        # band freeze scales the thresholds down, so the freeze is part of the
        # input space, not a setting.
        print()
        for region in ("ruk", "scotland"):
            for yrs in (0, 20, 35):
                up = 1.0 / (1.03 ** yrs)
                for need, oth in [(80_000, [0, 0]), (130_000, [0, 0]),
                                  (60_000, [95_000, 0]), (90_000, [110_000, 5_000])]:
                    js = await pg.evaluate(
                        "a => optimalSplit(a[0],a[1],a[2],a[3])",
                        [need, oth, region, up])
                    py = optimal_split(need, [float(x) for x in oth], region, up)
                    chk(f"{region} £{need:,} net, {yrs}yr freeze — A", js[0], py[0], 0.5)
                    chk(f"{region} £{need:,} net, {yrs}yr freeze — B", js[1], py[1], 0.5)
                    # and the split must actually deliver, in the JS too
                    delivered = sum(
                        R.net_income(float(o) + g, region, up)
                        - R.net_income(float(o), region, up)
                        for o, g in zip(oth, js))
                    chk(f"{region} £{need:,} net, {yrs}yr freeze — JS delivers",
                        delivered, float(need), 0.5)

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
            z = standard_normals(paths, 35, 7)
            rets = lognormal_real(0.0294, vol, z, "geo")
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

        print("\nF5. WHAT RETAINED TAX-FREE CASH DOES — JS vs PYTHON")
        print("=" * 86)
        # Added with the setting itself, 24 Aug 2026. Deterministic: zero
        # volatility, one path, so the closing balance reads out the growth of
        # the tax-free pot directly rather than through Monte Carlo noise.
        # The first case is the one that matters most — the DEFAULT must be
        # bit-for-bit the behaviour shipped before the setting existed.
        def _py_held(held, rate, ret=0.0294):
            hh = Household(
                people=[Person(pot=400_000, age=60, state_pension=12_548,
                               sp_age=67, take_pcls=True, pcls_spent=False)],
                target_net_income=13_000, end_age=95,
                pcls_held_as=held, pcls_cash_real=rate)
            return simulate_household(hh, np.full((1, 35), ret))

        def _js_held(held, rate, ret=0.0294):
            return dict(pot=400_000, retire=60, end=95, target=13_000,
                        sp=12_548, spAge=67, other=0, takePcls=True,
                        pclsSpend=False, real=ret, vol=0.0, conv="geo",
                        freeze=0, paths=1, couple=False, region="ruk",
                        pot2=0, retire2=0, sp2=0, spAge2=200, other2=0,
                        deathAge=0, survFrac=0.67,
                        pclsHeld=held, pclsCashReal=rate)

        _f5 = {}
        for label, held, rate in [("cash, 0% real (the default)", "cash", 0.0),
                                  ("cash, 1% real", "cash", 0.01),
                                  ("invested", "invested", 0.0)]:
            jsb = await pg.evaluate(
                "cfg => { const r = simulate(cfg); return r.bal[r.years]; }",
                _js_held(held, rate))
            pyb = float(_py_held(held, rate).balances[0, -1])
            chk(f"closing balance — {label}", jsb, pyb, 1.0)
            _f5[label] = (jsb, pyb)

        # AGREEMENT IS NOT ENOUGH. Delete the growth code from both engines and
        # every comparison above still passes — they agree on the same wrong
        # answer, which is exactly how the lifetime-tax bug survived (§15c) and
        # how F3 stayed blind to the split bug (§20h). So assert that the
        # setting CHANGES something, in each engine independently.
        _lo = _f5["cash, 0% real (the default)"]
        _mid = _f5["cash, 1% real"]
        _hi = _f5["invested"]
        for _eng, _i in (("JS", 0), ("Python", 1)):
            ok = _hi[_i] > _mid[_i] > _lo[_i]
            print(f"  {'PASS' if ok else 'FAIL'}  {_eng + ' — the setting actually changes the answer':<52}"
                  f"{_hi[_i]:>13,.0f} > {_mid[_i]:>11,.0f} > {_lo[_i]:>11,.0f}")
            if not ok:
                fails.append(f"{_eng}: pcls_held_as made no difference")

        # The setting must be INERT when no lump is retained. If it is not,
        # it has leaked into scenarios it has no business touching.
        for label, spend in [("PCLS spent elsewhere", True)]:
            cfg_a = _js_held("cash", 0.0);      cfg_a["pclsSpend"] = spend
            cfg_b = _js_held("invested", 0.03); cfg_b["pclsSpend"] = spend
            inert_a = await pg.evaluate("cfg => { const r=simulate(cfg); return r.bal[r.years]; }", cfg_a)
            inert_b = await pg.evaluate("cfg => { const r=simulate(cfg); return r.bal[r.years]; }", cfg_b)
            chk(f"setting is inert — {label}", inert_b, inert_a, 1.0)

        # And the control must actually exist on the page, wired to the engine.
        for sel in ("#pclsHeld", "#pclsCash"):
            n = await pg.evaluate(f"document.querySelectorAll('{sel}').length")
            print(f"  {'PASS' if n == 1 else 'FAIL'}  control {sel:<14} "
                  f"{'present' if n == 1 else 'MISSING'}")
            if n != 1:
                fails.append(f"control {sel} missing")

        # ==================================================================
        # F6. THE TWO POLICY ASSUMPTIONS — JS vs PYTHON
        #
        # Until 25 August 2026 the band-freeze inflation rate lived in the JS
        # as the literal 1.03 while Python carried it as a named parameter,
        # and State Pension real growth existed in NEITHER engine. Section 31
        # of the project notes calls that class of gap out: a constant only
        # one engine can express is a constant no cross-check is checking.
        #
        # Deterministic (zero volatility) so every number is exact and no
        # tolerance band can hide a discrepancy.
        # ==================================================================
        print("\nF6. BAND-FREEZE INFLATION AND STATE PENSION GROWTH — JS vs PYTHON")
        print("=" * 86)

        def _cfg6(freeze, infl, spg):
            return dict(pot=400_000, retire=60, end=95, target=20_000,
                        sp=12_548, spAge=67, other=0, takePcls=False,
                        pclsSpend=False, pclsHeld="cash", pclsCashReal=0.0,
                        real=0.0294, vol=0.0, conv="geo", freeze=freeze,
                        freezeInfl=infl, spGrowth=spg, paths=1, couple=False,
                        region="ruk", pot2=0, retire2=0, sp2=0, spAge2=200,
                        other2=0, deathAge=0, survFrac=0.67)

        def _py6(freeze, infl, spg):
            plan = Plan(pot=400_000, retire_age=60, end_age=95,
                        target_net_income=20_000, state_pension_age=67,
                        state_pension_annual=12_548, take_pcls=False,
                        band_freeze_years=freeze, assumed_inflation=infl,
                        sp_real_growth=spg)
            return float(simulate(plan, np.full((1, 35), 0.0294)).balances[0, -1])

        _cases = [("default — 3% infl, 0% SP growth", 20, 0.03, 0.0),
                  ("freeze inflation 2%",             20, 0.02, 0.0),
                  ("freeze inflation 6%",             20, 0.06, 0.0),
                  ("SP growth 0.75%",                  0, 0.03, 0.0075),
                  ("SP growth 1.5% under a freeze",   20, 0.03, 0.015)]
        _got = {}
        for _lab, _fz, _if, _sg in _cases:
            _js = await pg.evaluate(
                "cfg => { const r=simulate(cfg); return r.bal[r.years]; }",
                _cfg6(_fz, _if, _sg))
            _py = _py6(_fz, _if, _sg)
            _got[_lab] = (_js, _py)
            chk(f"closing balance — {_lab}", _js, _py, 1.0)

        # EFFECT ASSERTIONS. Agreement alone is not enough: if a parameter were
        # dropped on the floor by BOTH engines they would agree perfectly and
        # every comparison above would still pass. So assert the answer MOVES,
        # separately in each engine. (F5 learned this the hard way — stripping
        # the growth code from both engines left every comparison passing.)
        for _eng, _i in (("JS", 0), ("Python", 1)):
            _lo = _got["freeze inflation 6%"][_i]
            _mid = _got["default — 3% infl, 0% SP growth"][_i]
            _hi = _got["freeze inflation 2%"][_i]
            ok = _hi > _mid > _lo
            print(f"  {'PASS' if ok else 'FAIL'}  {_eng + ' — freeze inflation changes the answer':<52}"
                  f"{_hi:>13,.0f} > {_mid:>11,.0f} > {_lo:>11,.0f}")
            if not ok:
                fails.append(f"{_eng}: freezeInfl made no difference")

            _s0 = _got["default — 3% infl, 0% SP growth"][_i]
            _s15 = _got["SP growth 1.5% under a freeze"][_i]
            ok = _s15 > _s0
            print(f"  {'PASS' if ok else 'FAIL'}  {_eng + ' — SP growth changes the answer':<52}"
                  f"{_s15:>13,.0f} > {_s0:>11,.0f}")
            if not ok:
                fails.append(f"{_eng}: spGrowth made no difference")

        # An omitted field must fall back to the Python dataclass default, or
        # the two engines disagree about a config neither of them rejects.
        _bare = _cfg6(20, 0.03, 0.0)
        del _bare["freezeInfl"], _bare["spGrowth"]
        _js_bare = await pg.evaluate(
            "cfg => { const r=simulate(cfg); return r.bal[r.years]; }", _bare)
        chk("omitted fields fall back to the Python defaults",
            _js_bare, _py6(20, 0.03, 0.0), 1.0)

        # And both controls must exist on the page, wired to the engine.
        for sel in ("#freezeInfl", "#spGrowth"):
            n = await pg.evaluate(f"document.querySelectorAll('{sel}').length")
            print(f"  {'PASS' if n == 1 else 'FAIL'}  control {sel:<14} "
                  f"{'present' if n == 1 else 'MISSING'}")
            if n != 1:
                fails.append(f"control {sel} missing")

        # The disclosure is part of the fix, not decoration: section 31 found
        # the State Pension paragraph asserting "rising with inflation" with
        # none of the caveat the bands paragraph one block earlier carries.
        # SCOPED TO THE STATE PENSION PARAGRAPH, deliberately. Checking the
        # whole assumptions block for "not current policy" passes on the BANDS
        # paragraph alone — the removal test caught that, which is what removal
        # tests are for.
        _sp_para = await pg.evaluate("""() => {
            const ps = [...document.querySelectorAll('#assump p')];
            const p = ps.find(x => x.textContent.trim().startsWith('State Pension.'));
            return p ? p.textContent : ''; }""")
        for _phrase, _why in (("not current policy", "caveat in the SP paragraph"),
                              ("triple lock", "triple lock named"),
                              ("2.5%", "the 2.5% floor stated")):
            ok = _phrase in _sp_para
            print(f"  {'PASS' if ok else 'FAIL'}  disclosure: {_why:<38} "
                  f"{'present' if ok else 'MISSING'}")
            if not ok:
                fails.append(f"disclosure missing: {_why}")

        # ==================================================================
        # F7. STAGE D — AN ISA AS A STARTING ASSET, JS vs PYTHON
        #
        # Deterministic (zero volatility), so every figure is exact.
        # ==================================================================
        print("\nF7. AN ISA AS A STARTING ASSET — JS vs PYTHON")
        print("=" * 86)

        def _cfg7(isa, held="invested", isa_real=0.0, pcls_held="cash"):
            return dict(pot=400_000, retire=60, end=95, target=20_000,
                        sp=12_548, spAge=67, other=0, takePcls=True,
                        pclsSpend=False, pclsHeld=pcls_held, pclsCashReal=0.0,
                        isa=isa, isaHeld=held, isaReal=isa_real,
                        real=0.0294, vol=0.0, conv="geo", freeze=0,
                        freezeInfl=0.03, spGrowth=0.0, paths=1, couple=False,
                        region="ruk", pot2=0, retire2=0, sp2=0, spAge2=200,
                        other2=0, deathAge=0, survFrac=0.67)

        def _py7(isa, held="invested", isa_real=0.0, pcls_held="cash"):
            plan = Plan(pot=400_000, retire_age=60, end_age=95,
                        target_net_income=20_000, state_pension_age=67,
                        state_pension_annual=12_548, take_pcls=True,
                        isa=isa, isa_held_as=held, isa_real=isa_real,
                        pcls_held_as=pcls_held)
            return float(simulate(plan, np.full((1, 35), 0.0294)).balances[0, -1])

        _c7 = [("no ISA — the regression fixture", 0.0, "invested", 0.0, "cash"),
               ("ISA 100k, invested",          100_000.0, "invested", 0.0, "cash"),
               ("ISA 100k, cash at 0%",        100_000.0, "cash",     0.0, "cash"),
               ("ISA 100k, cash at 1%",        100_000.0, "cash",    0.01, "cash"),
               ("ISA 100k invested, PCLS invested",
                                               100_000.0, "invested", 0.0, "invested")]
        _g7 = {}
        for _lab, _isa, _held, _ir, _ph in _c7:
            _js = await pg.evaluate(
                "cfg => { const r=simulate(cfg); return r.bal[r.years]; }",
                _cfg7(_isa, _held, _ir, _ph))
            _py = _py7(_isa, _held, _ir, _ph)
            _g7[_lab] = (_js, _py)
            chk(f"closing balance — {_lab}", _js, _py, 1.0)

        # The opening balance is a direct read-out of whether the ISA arrived
        # whole and once — deterministic, and it cannot be floored.
        _open_js = await pg.evaluate("cfg => simulate(cfg).bal[0]", _cfg7(100_000.0))
        chk("opening balance = pot + ISA (arrived once)", _open_js, 500_000.0, 1.0)

        # EFFECT ASSERTIONS, separately in each engine. A field both engines
        # ignore identically agrees perfectly and means nothing (24c).
        for _eng, _i in (("JS", 0), ("Python", 1)):
            _n = _g7["no ISA — the regression fixture"][_i]
            _v = _g7["ISA 100k, invested"][_i]
            ok = _v > _n
            print(f"  {'PASS' if ok else 'FAIL'}  {_eng + ' — an ISA changes the answer':<52}"
                  f"{_v:>13,.0f} > {_n:>11,.0f}")
            if not ok:
                fails.append(f"{_eng}: isa made no difference")

            _lo = _g7["ISA 100k, cash at 0%"][_i]
            _mid = _g7["ISA 100k, cash at 1%"][_i]
            _hi = _g7["ISA 100k, invested"][_i]
            ok = _hi > _mid > _lo
            print(f"  {'PASS' if ok else 'FAIL'}  {_eng + ' — isaHeld changes the answer':<52}"
                  f"{_hi:>13,.0f} > {_mid:>11,.0f} > {_lo:>11,.0f}")
            if not ok:
                fails.append(f"{_eng}: isaHeld made no difference")

        # Omitted fields must fall back to the PYTHON dataclass defaults —
        # note isaHeld defaults to "invested" while pclsHeld defaults to
        # "cash", so a careless shared default would show up right here.
        _bare = _cfg7(100_000.0)
        del _bare["isaHeld"], _bare["isaReal"]
        _js_bare = await pg.evaluate(
            "cfg => { const r=simulate(cfg); return r.bal[r.years]; }", _bare)
        chk("omitted ISA fields default to invested, as Python does",
            _js_bare, _py7(100_000.0), 1.0)

        # The controls must exist and be wired.
        for sel in ("#isa", "#isaHeld", "#isaReal"):
            n = await pg.evaluate(f"document.querySelectorAll('{sel}').length")
            print(f"  {'PASS' if n == 1 else 'FAIL'}  control {sel:<14} "
                  f"{'present' if n == 1 else 'MISSING'}")
            if n != 1:
                fails.append(f"control {sel} missing")

        # The ordering disclosure is part of the fix. Shipping a knowingly
        # suboptimal hard-coded order without saying so would be the tool
        # doing the thing it criticises.
        _assump = await pg.evaluate("document.getElementById('assump').textContent")
        for _phrase, _why in (("order is fixed", "the order is declared fixed"),
                              ("not always the best", "and declared suboptimal")):
            ok = _phrase in _assump
            print(f"  {'PASS' if ok else 'FAIL'}  disclosure: {_why:<38} "
                  f"{'present' if ok else 'MISSING'}")
            if not ok:
                fails.append(f"disclosure missing: {_why}")

        # ==================================================================
        # F8. STAGE E — WITHDRAWAL ORDER, JS vs PYTHON
        #
        # Deterministic (zero volatility, one path), so every figure is exact
        # and nothing here is a sampling artefact. Single person only — the
        # engines both REFUSE ordering for a couple, and F8f checks that they
        # refuse rather than silently falling back.
        # ==================================================================
        print("\nF8. WITHDRAWAL ORDER — JS vs PYTHON")
        print("=" * 86)

        _ORDERS = ("tax_free_first", "fill_allowance",
                   "proportional", "pension_first")

        def _cfg8(order, pot=900_000, isa=0, pcls_held="invested"):
            return dict(pot=pot, retire=60, end=95, target=30_000,
                        sp=12_548, spAge=67, other=0, takePcls=True,
                        pclsSpend=False, pclsHeld=pcls_held, pclsCashReal=0.0,
                        isa=isa, isaHeld="invested", isaReal=0.0,
                        real=0.03, vol=0.0, conv="geo", freeze=0,
                        freezeInfl=0.03, spGrowth=0.0, paths=1, couple=False,
                        region="ruk", pot2=0, retire2=0, sp2=0, spAge2=200,
                        other2=0, deathAge=0, survFrac=0.67, order=order)

        def _py8(order, pot=900_000, isa=0, pcls_held="invested"):
            plan = Plan(pot=pot, retire_age=60, end_age=95,
                        target_net_income=30_000, state_pension_age=67,
                        state_pension_annual=12_548, take_pcls=True,
                        isa=isa, isa_held_as="invested",
                        pcls_held_as=pcls_held, withdrawal_order=order)
            return simulate(plan, np.full((1, 35), 0.03))

        # F8a. Closing balances agree, order by order, on a case that does NOT
        # deplete. Depletion would floor the balance at zero and make four
        # different strategies agree perfectly while doing nothing (10d).
        _g8 = {}
        for _o in _ORDERS:
            _js = await pg.evaluate(
                "cfg => { const r=simulate(cfg); return r.bal[r.years]; }",
                _cfg8(_o))
            _pyr = _py8(_o)
            if _pyr.depleted_age[0] > 0:
                fails.append(f"F8a censored: {_o} depleted")
            _g8[_o] = (_js, float(_pyr.balances[0, -1]))
            chk(f"closing balance — {_o}", _js, float(_pyr.balances[0, -1]), 1.0)

        # F8b. And with an ISA present, which is the case ordering exists for.
        for _o in _ORDERS:
            _js = await pg.evaluate(
                "cfg => { const r=simulate(cfg); return r.bal[r.years]; }",
                _cfg8(_o, pot=600_000, isa=300_000))
            _pyr = _py8(_o, pot=600_000, isa=300_000)
            if _pyr.depleted_age[0] > 0:
                fails.append(f"F8b censored: {_o} depleted")
            chk(f"closing balance, £300k ISA — {_o}", _js,
                float(_pyr.balances[0, -1]), 1.0)

        # F8c. EFFECT ASSERTIONS, separately in each engine. This is the check
        # that 24c and 35c row (b) exist to force: strip the feature from BOTH
        # engines and every comparison above still passes.
        for _eng, _i in (("JS", 0), ("Python", 1)):
            _vals = [_g8[_o][_i] for _o in _ORDERS]
            ok = max(_vals) - min(_vals) > 1_000.0
            print(f"  {'PASS' if ok else 'FAIL'}  "
                  f"{_eng + ' — the order changes the answer':<52}"
                  f"spread {max(_vals)-min(_vals):>12,.0f}")
            if not ok:
                fails.append(f"{_eng}: withdrawal order made no difference")

            # And the specific mechanism, not merely "something moved":
            # fill_allowance must beat the shipped order once the pools grow.
            ok = _g8["fill_allowance"][_i] > _g8["tax_free_first"][_i]
            print(f"  {'PASS' if ok else 'FAIL'}  "
                  f"{_eng + ' — fill_allowance beats tax_free_first':<52}"
                  f"{_g8['fill_allowance'][_i]:>12,.0f} > "
                  f"{_g8['tax_free_first'][_i]:>11,.0f}")
            if not ok:
                fails.append(f"{_eng}: fill_allowance did not beat the default")

        # F8d. With NO tax-free pool the four orders must COINCIDE — in the JS
        # as well as in Python. A strategy that had stopped respecting balances
        # would show up here and nowhere else.
        _nf = [await pg.evaluate(
            "cfg => { const r=simulate(cfg); return r.bal[r.years]; }",
            {**_cfg8(_o), "pclsSpend": True}) for _o in _ORDERS]
        ok = max(_nf) - min(_nf) < 1.0
        print(f"  {'PASS' if ok else 'FAIL'}  "
              f"{'JS — no tax-free pool => all orders coincide':<52}"
              f"spread {max(_nf)-min(_nf):>12,.6f}")
        if not ok:
            fails.append("JS: orders differ with no tax-free pool")

        # F8e. An omitted `order` must fall back to the Python default.
        _bare = _cfg8("tax_free_first")
        del _bare["order"]
        _js_bare = await pg.evaluate(
            "cfg => { const r=simulate(cfg); return r.bal[r.years]; }", _bare)
        chk("omitted order defaults to tax_free_first, as Python does",
            _js_bare, float(_py8("tax_free_first").balances[0, -1]), 1.0)

        # F8f. BOTH engines must REFUSE what they cannot do, rather than
        # silently doing something else. An unknown order, and ordering for a
        # couple — which is out of scope for this stage because it interacts
        # with the tax-optimal split.
        # These check the MESSAGE, not merely that something threw, and the
        # reason is worth recording. The first version asked only "did it
        # throw?" and stayed GREEN when the guard was deleted — because
        # without the guard the couple case runs on to a null tax curve and
        # crashes there instead. A downstream crash imitated the guard
        # perfectly. That is 10d's shape in a new place: the assertion was
        # true for a reason that had nothing to do with what it claimed.
        async def _refuses(label, cfg, want, failtag):
            msg = await pg.evaluate(
                "cfg => { try { simulate(cfg); return ''; } "
                "catch(e) { return String(e.message || e); } }", cfg)
            ok = want in msg
            print(f"  {'PASS' if ok else 'FAIL'}  {label:<52}"
                  f"{(msg[:40] or 'ACCEPTED') if not ok else 'refused explicitly'}")
            if not ok:
                fails.append(failtag)

        await _refuses("JS — an unknown order is refused",
                       {**_cfg8("tax_free_first"), "order": "cheapest"},
                       "unknown withdrawal order",
                       "JS: unknown order not explicitly refused")
        await _refuses("JS — ordering for a couple is refused, not faked",
                       {**_cfg8("fill_allowance"), "couple": True,
                        "pot2": 200_000, "retire2": 60, "sp2": 12_548,
                        "spAge2": 67},
                       "single-person only",
                       "JS: couple ordering not explicitly refused")

        # ==================================================================
        # F9. THE SOURCED POLICY ASSUMPTIONS (38) — ONS figures on the page
        #
        # No engine change here: this is presentation and disclosure. What
        # matters is that the numbers printed beside the sliders are the ones
        # verify.py section I recomputes from the ONS series, and that the
        # DEFAULTS did not move.
        # ==================================================================
        print("\nF9. THE SOURCED POLICY ASSUMPTIONS")
        print("=" * 86)

        import ons_data as _O
        _pub = pathlib.Path(__file__).resolve().parent.parent / "public"
        _idx = (_pub / "index.html").read_text(encoding="utf-8")
        _fnd = (_pub / "findings.html").read_text(encoding="utf-8")

        # F9a. The observed maximum must be REACHABLE on the slider. Asserting
        # the attribute equals 10 would pass for the wrong reason if the CPI
        # series were revised; assert against the data instead.
        _mx = await pg.evaluate(
            "() => parseFloat(document.getElementById('freezeInfl').max)")
        _obs = max(_O.CPI_ANNUAL_RATE[y] for y in range(1993, 2026))
        ok = _mx >= _obs
        print(f"  {'PASS' if ok else 'FAIL'}  "
              f"{'slider reaches the observed CPI maximum':<52}"
              f"max {_mx:g}% >= {_obs:g}% (2022)")
        if not ok:
            fails.append("freezeInfl slider cannot reach the observed CPI maximum")

        # F9b. THE DEFAULTS MUST NOT HAVE MOVED. This is what keeps the
        # published 35% standing, and it is the check that would catch someone
        # "helpfully" defaulting the State Pension to the measured 1.3%.
        _d = await pg.evaluate(
            "() => ({fi: document.getElementById('freezeInfl').value,"
            " sp: document.getElementById('spGrowth').value})")
        ok = _d["fi"] == "3" and _d["sp"] == "0"
        print(f"  {'PASS' if ok else 'FAIL'}  "
              f"{'defaults unmoved — freezeInfl 3%, spGrowth 0%':<52}"
              f"{_d['fi']}% / {_d['sp']}%")
        if not ok:
            fails.append(f"policy defaults moved: {_d}")

        # F9c. The figures quoted beside the sliders are the computed ones.
        for _needle, _what in (("9.1", "2022 CPI peak"),
                               ("2.5% a year", "1993-2025 CPI mean"),
                               ("D7G7", "the CPI series is named"),
                               ("1.3&ndash;1.4% a year", "the triple lock figure"),
                               ("median 1.6%", "and its median")):
            ok = _needle in _idx
            print(f"  {'PASS' if ok else 'FAIL'}  {'index.html quotes ' + _what:<52}"
                  f"{'present' if ok else 'MISSING'}")
            if not ok:
                fails.append(f"index.html missing {_what}")

        # F9d. 10f MECHANISED. The triple-lock figure appears on two pages. The
        # standing rule is that a claim stated twice should be stated once and
        # referenced — where that is not possible across two static files, a
        # test has to hold them together. 21e is four instances of exactly this
        # going wrong.
        ok = ("1.3&ndash;1.4% a year" in _idx
              and "1.3&ndash;1.4% a year in real terms" in _fnd)
        print(f"  {'PASS' if ok else 'FAIL'}  "
              f"{'the figure agrees across index and findings':<52}"
              f"{'both' if ok else 'DIVERGED'}")
        if not ok:
            fails.append("triple-lock figure differs between the two pages")

        # The href may or may not carry the .html extension — Cloudflare
        # Pages serves /findings and 308s /findings.html to it, so the
        # site declares the extensionless form. What must hold is that
        # index.html links to the findings page anchored at s10 and that
        # the anchor exists. Written against the URL SHAPE it was, this
        # row went red for a spelling change — 10h. 4 September 2026.
        ok = (re.search(r'href="/?findings(?:\.html)?#s10"', _idx) is not None
              and 'id="s10"' in _fnd)
        print(f"  {'PASS' if ok else 'FAIL'}  "
              f"{'and index.html links to the working':<52}"
              f"{'linked' if ok else 'BROKEN ANCHOR'}")
        if not ok:
            fails.append("index.html link to findings section 10 is broken")

        # F9e. The Open Government Licence attribution is a CONDITION of using
        # the data, not a nicety. It must be on the page that publishes it.
        ok = ("Open Government Licence" in _fnd and "D7G7" in _fnd
              and "KAB9" in _fnd)
        print(f"  {'PASS' if ok else 'FAIL'}  "
              f"{'findings.html carries the OGL attribution':<52}"
              f"{'present' if ok else 'MISSING'}")
        if not ok:
            fails.append("OGL attribution missing from findings.html")

        # F9f. A template placeholder left in STATIC html renders literally as
        # "${RULES.src...}" to the reader. Added because it happened while
        # writing this section: the hints live outside <script>, and the first
        # draft pasted a ${...} into one.
        _strays = await pg.evaluate("""() => {
            const out = [];
            document.querySelectorAll('p,li,span,td,caption,h1,h2,h3').forEach(el => {
              if (/\$\{/.test(el.textContent)) out.push(el.textContent.slice(0,60));
            });
            return out;
        }""")
        ok = not _strays
        print(f"  {'PASS' if ok else 'FAIL'}  "
              f"{'no unrendered ${...} placeholders on the page':<52}"
              f"{'clean' if ok else _strays[:2]}")
        if not ok:
            fails.append(f"unrendered template placeholder on the page: {_strays[:2]}")

        print("\nF10. THE RETURN CONVENTION — GEOMETRIC vs ARITHMETIC (41a)")
        print("=" * 86)
        # Until 1 September 2026 `conv` was a JS-ONLY parameter. The browser
        # carried both branches; the Python engine carried neither; and all
        # seven conv= call sites in this file passed "geo". So the ARITHMETIC
        # branch of the shipped calculator was cross-checked against nothing,
        # for as long as it has been live. 10b, and 10c in the direction 31's
        # literal audit never swept — a parameter the JS can express and the
        # Python cannot.
        #
        # THIS SECTION MUST NOT BE RUN AT vol=0. The two conventions are
        # identical by construction there, so a zero-volatility version of it
        # would pass with `conv` ignored entirely (10h). F10a states that
        # coincidence separately, and labels it, so it cannot be mistaken for
        # the test.
        _cv_cfg = dict(pot=500_000, retire=60, end=95, target=30_000,
                       sp=12_548, spAge=67, other=0, takePcls=True,
                       pclsSpend=False, real=0.0294, vol=0.15, freeze=0,
                       paths=20_000, couple=False, region="ruk", pot2=0,
                       retire2=0, sp2=0, spAge2=200, other2=0, deathAge=0,
                       survFrac=0.67)
        _cv_plan = Plan(pot=500_000, retire_age=60, end_age=95,
                        target_net_income=30_000, state_pension_age=67,
                        state_pension_annual=12_548, take_pcls=True)
        _cv_z = standard_normals(20_000, 35, 7)

        _js_s, _py_s = {}, {}
        for _c in ("geo", "ari"):
            _js_s[_c] = await pg.evaluate(
                "cfg => simulate(cfg).successRate", dict(_cv_cfg, conv=_c)) * 100
            _py_s[_c] = simulate(
                _cv_plan, lognormal_real(0.0294, 0.15, _cv_z, _c)).success_rate * 100
            chk(f"success rate at conv={_c!r} (±1.5pp MC)", _js_s[_c], _py_s[_c], 1.5)

        # F10a. THE DEGENERATE CASE, named so it cannot be mistaken for a test.
        # At vol=0 the conventions coincide. Checked on a CLOSING BALANCE with
        # a pot that cannot deplete, not on a success rate — at zero volatility
        # every path is the same path, so the success rate is 0% or 100% and a
        # comparison of two censored values is not a comparison (10d).
        _flat = dict(_cv_cfg, vol=0.0, pot=2_000_000, paths=200)
        _fb = {}
        for _c in ("geo", "ari"):
            _fb[_c] = await pg.evaluate(
                "cfg => { const r = simulate(cfg); return r.bal[(r.years+1)-1]; }",
                dict(_flat, conv=_c))
        _unc = _fb["geo"] > 1_000.0 and _fb["ari"] > 1_000.0
        if not _unc:
            fails.append("F10a ran on a depleted pot — result is censored")
        print(f"  {'PASS' if _unc else 'FAIL'}  "
              f"{'F10a case is uncensored (pot never depletes)':<50} "
              f"£{min(_fb.values()):>13,.0f}")
        chk("vol=0: conventions coincide (DEGENERATE, not a test)",
            _fb["geo"], _fb["ari"], 0.01)

        # F10b. EFFECT ASSERTIONS (10b). The rows above compare two engines;
        # they do NOT establish that either engine READS the parameter. An
        # engine that ignored `conv` would agree perfectly with another engine
        # that ignored `conv` — which is 20a exactly, two implementations of
        # one mistake reported as agreement. So assert the effect separately
        # in each engine.
        #
        # The measured gap is ~12.4pp (41a, five seeds, sd 0.08pp). The 8.0pp
        # threshold is deliberately far below it and far above zero: it fails
        # loudly if either engine stops reading `conv`, and does not tighten
        # into a flaky test as the Monte Carlo noise moves.
        for _eng, _d in (("JS", _js_s), ("Python", _py_s)):
            _eff = _d["geo"] - _d["ari"]
            ok = _eff > 8.0
            if not ok:
                fails.append(f"conv has no effect in the {_eng} engine")
            print(f"  {'PASS' if ok else 'FAIL'}  "
                  f"{'conv CHANGES the answer in ' + _eng:<50} "
                  f"{_eff:>10.2f} pp")
        chk("both engines agree on the SIZE of the effect",
            _js_s["geo"] - _js_s["ari"], _py_s["geo"] - _py_s["ari"], 1.5)

        # F10c. 37g: the uncensored check is built INTO the script rather than
        # remembered. 41's own first measurement compared 0.000% with 0.000%
        # and looked exactly like a pass.
        for _eng, _d in (("js", _js_s), ("py", _py_s)):
            for _c in ("geo", "ari"):
                ok = 0.5 < _d[_c] < 99.5
                if not ok:
                    fails.append(f"F10 {_eng} conv={_c} is at a bound ({_d[_c]:.2f}%)")
                print(f"  {'PASS' if ok else 'FAIL'}  "
                      f"{f'{_eng} conv={_c!r} is strictly inside (0,100)':<50} "
                      f"{_d[_c]:>10.2f} %")

        # F10d. A MISTYPED convention must raise, not quietly run geometric —
        # a silent fallback is an output the caller believes is one thing and
        # is another (10b). Asserted on the MESSAGE, not merely on the fact
        # that something was raised (10h).
        try:
            lognormal_real(0.0294, 0.15, _cv_z, "arithmetic")
            ok, _msg = False, "no exception"
        except ValueError as _e:
            _msg = str(_e)
            ok = "conv must be one of" in _msg
        if not ok:
            fails.append(f"unknown conv not refused properly: {_msg}")
        print(f"  {'PASS' if ok else 'FAIL'}  "
              f"{'an unknown convention is REFUSED':<50} {_msg[:28]!r}")

        print("\nF12. ANNUAL CHARGES (41b)")
        print("=" * 86)
        # The fee is applied to the DRIFT, not inside the withdrawal loop, so it
        # never touches the gross-up maths. It is charged on the return path,
        # which means the pension and any pool held as "invested" pay it and
        # pools held as cash do not.
        _fee_base = dict(pot=500_000, retire=60, end=95, target=30_000,
                         sp=12_548, spAge=67, other=0, takePcls=True,
                         pclsSpend=False, real=0.0294, vol=0.15, conv="geo",
                         freeze=0, paths=20_000, couple=False, region="ruk",
                         pot2=0, retire2=0, sp2=0, spAge2=200, other2=0,
                         deathAge=0, survFrac=0.67)
        _fee_plan = Plan(pot=500_000, retire_age=60, end_age=95,
                         target_net_income=30_000, state_pension_age=67,
                         state_pension_annual=12_548, take_pcls=True)

        # F12a. The DEFAULT must reproduce the shipped page exactly. Not
        # "closely" — a config with fee omitted and a config with fee=0 must
        # give the identical number, because the JS is deterministic on a fixed
        # seed. This is the check that protects the published 35% / 20,650 / 81.
        _omitted = await pg.evaluate("cfg => simulate(cfg).successRate", _fee_base)
        _zero = await pg.evaluate("cfg => simulate(cfg).successRate",
                                  dict(_fee_base, fee=0.0))
        ok = _omitted == _zero
        if not ok:
            fails.append("fee omitted differs from fee=0")
        print(f"  {'PASS' if ok else 'FAIL'}  "
              f"{'fee omitted == fee 0.0, exactly':<50} "
              f"{_omitted*100:>10.4f} %")

        # F12b. MULTIPLICATIVE, NOT ADDITIVE — the one modelling decision 41b
        # actually made, checked deterministically at vol=0 against a closed
        # form, on a pot that cannot deplete (10d). A `mu - fee` engine gives a
        # visibly different closing balance, so this assertion cannot be
        # satisfied by the model it excludes (10h).
        _det = dict(_fee_base, vol=0.0, paths=200, pot=1_000_000, end=90,
                    target=25_000, takePcls=False, sp=0, spAge=200, fee=0.015)
        _js_det = await pg.evaluate(
            "cfg => { const r = simulate(cfg); return r.bal[(r.years+1)-1]; }", _det)
        _gross = R.gross_for_net(25_000, 0.0)
        def _closed(growth):
            _p = 1_000_000.0
            for _ in range(30):
                _p = (_p - min(_p, _gross)) * growth
            return _p
        _mult = _closed((1 + 0.0294) * (1 - 0.015))     # log1p(-fee) form
        _addi = _closed(1 + 0.0294 - 0.015)             # the naive - fee form
        chk("charges are multiplicative (closed form)", _js_det, _mult, 1.0)

        # F12b-py. THE SAME CHECK ON THE PYTHON SIDE, and it is not optional.
        # Running the removal harness showed that making `lognormal_real`
        # additive left this whole suite GREEN: the closed form above tests the
        # JS only, and the stochastic rows below carry a 1.5pp Monte Carlo
        # tolerance while additive-vs-multiplicative is worth about 0.5pp at
        # these charge levels. So the Python fee FORM was checked by nothing —
        # 10a, in a test written the same afternoon as 10a's own automation,
        # and found by RUNNING the removal rather than by reading the test.
        #
        # Asserted on the return itself at vol=0, where lognormal_real is exact
        # and deterministic, so there is no tolerance to hide inside.
        _r = float(lognormal_real(0.0294, 0.0, np.zeros((1, 1)), "geo", 0.015)[0, 0])
        _r_mult = (1 + 0.0294) * (1 - 0.015) - 1
        _r_addi = 0.0294 - 0.015
        ok = abs(_r - _r_mult) < 1e-12 and abs(_r - _r_addi) > 1e-5
        if not ok:
            fails.append("the PYTHON fee is not multiplicative")
        print(f"  {'PASS' if ok else 'FAIL'}  "
              f"{'...in the PYTHON engine too, exactly':<50} "
              f"{_r:.10f} vs {_r_addi:.10f} additive")
        _sep = abs(_js_det - _addi)
        ok = _sep > 1_000.0 and _js_det > 1_000.0
        if not ok:
            fails.append("F12b cannot tell multiplicative from additive here")
        print(f"  {'PASS' if ok else 'FAIL'}  "
              f"{'...and NOT additive — the two are separable':<50} "
              f"£{_sep:>13,.0f} apart")

        # F12c/d. Cross-engine at two real charge levels, with an effect
        # assertion in each engine separately (10b).
        _z = standard_normals(20_000, 35, 7)
        _js_f, _py_f = {}, {}
        for _f in (0.0, 0.0075, 0.015):
            _js_f[_f] = await pg.evaluate("cfg => simulate(cfg).successRate",
                                          dict(_fee_base, fee=_f)) * 100
            _py_f[_f] = simulate(_fee_plan,
                                 lognormal_real(0.0294, 0.15, _z, "geo", _f)
                                 ).success_rate * 100
            chk(f"success rate at {_f*100:.2f}% charges (±1.5pp MC)",
                _js_f[_f], _py_f[_f], 1.5)
        for _eng, _d in (("JS", _js_f), ("Python", _py_f)):
            _eff = _d[0.0] - _d[0.015]
            ok = _eff > 3.0
            if not ok:
                fails.append(f"the fee has no effect in the {_eng} engine")
            print(f"  {'PASS' if ok else 'FAIL'}  "
                  f"{'charges CHANGE the answer in ' + _eng:<50} "
                  f"{_eff:>10.2f} pp")
        # Monotone: more charges cannot help.
        for _eng, _d in (("JS", _js_f), ("Python", _py_f)):
            ok = _d[0.0] >= _d[0.0075] >= _d[0.015]
            if not ok:
                fails.append(f"{_eng}: success rate not monotone in the fee")
            print(f"  {'PASS' if ok else 'FAIL'}  "
                  f"{_eng + ': success falls as charges rise':<50} "
                  f"{_d[0.0]:.2f} > {_d[0.0075]:.2f} > {_d[0.015]:.2f}")

        # F12e. 37g — uncensored, built into the script rather than remembered.
        for _eng, _d in (("js", _js_f), ("py", _py_f)):
            for _f in (0.0, 0.0075, 0.015):
                ok = 0.5 < _d[_f] < 99.5
                if not ok:
                    fails.append(f"F12 {_eng} fee={_f} is at a bound")
        print(f"  {'PASS' if all(0.5 < v < 99.5 for d in (_js_f, _py_f) for v in d.values()) else 'FAIL'}  "
              f"{'every F12 rate is strictly inside (0,100)':<50} "
              f"{min(list(_js_f.values()) + list(_py_f.values())):.2f}-"
              f"{max(list(_js_f.values()) + list(_py_f.values())):.2f} %")

        # F12f. An impossible charge must RAISE. fee=1.0 is log1p(-1) = -inf and
        # anything above it is NaN — both would propagate silently through every
        # path and produce a plausible-looking answer. Asserted on the message.
        try:
            lognormal_real(0.0294, 0.15, _z, "geo", 1.0)
            ok, _m = False, "no exception"
        except ValueError as _e:
            _m = str(_e)
            ok = "fee must be in" in _m
        if not ok:
            fails.append(f"an impossible fee was not refused: {_m}")
        print(f"  {'PASS' if ok else 'FAIL'}  "
              f"{'a fee of 100% is REFUSED':<50} {_m[:28]!r}")

        print("\nF13. THE CSV AUDIT EXPORT (41c)")
        print("=" * 86)
        _ax = dict(pot=500_000, retire=60, end=95, target=30_000, sp=12_548,
                   spAge=67, other=0, takePcls=True, pclsSpend=False,
                   real=0.0294, vol=0.0, conv="geo", fee=0.0, freeze=0,
                   paths=1, couple=False, region="ruk", pot2=0, retire2=0,
                   sp2=0, spAge2=200, other2=0, deathAge=0, survFrac=0.67)

        # F13a. NUMBER-NEUTRALITY. The trace writes variables the simulation
        # never reads — but "it only records" is precisely the reasoning that
        # let 41a sit unchecked for sixteen days, so it is asserted. Exact
        # equality on the whole balance array, not a tolerance.
        _neutral = await pg.evaluate("""cfg => {
            const a = simulate(Object.assign({}, cfg, {trace:false, paths:2000, vol:0.15}));
            const b = simulate(Object.assign({}, cfg, {trace:true,  paths:2000, vol:0.15}));
            let same = a.successRate === b.successRate && a.bal.length === b.bal.length;
            for (let i = 0; same && i < a.bal.length; i++) if (a.bal[i] !== b.bal[i]) same = false;
            return {same, n: a.bal.length, succ: a.successRate};
        }""", _ax)
        ok = _neutral["same"]
        if not ok:
            fails.append("the audit trace CHANGES the simulation")
        print(f"  {'PASS' if ok else 'FAIL'}  "
              f"{'trace:true is byte-identical to trace:false':<50} "
              f"{_neutral['n']:,} balances equal")

        # F13b. THE EXPORT MUST RECONCILE. An audit file that does not add up is
        # worse than none, and a single "opening balance" total cannot add up:
        # the three pools grow at different rates. Checked on every row.
        _rows = await pg.evaluate("""cfg => {
            document.querySelector('#pot').value = cfg.pot;
            return (function(){ return auditRows(); })();
        }""", _ax)
        _h = {k: i for i, k in enumerate(_rows[0])}
        _worst, _f = 0.0, lambda r, k: float(r[_h[k]])
        for _row in _rows[1:]:
            _pred = ((_f(_row, "opening_pension") - _f(_row, "gross_pension_withdrawal"))
                     * _f(_row, "pension_growth_factor")
                     + (_f(_row, "opening_tax_free_cash") - _f(_row, "from_tax_free_cash"))
                     * _f(_row, "cash_growth_factor")
                     + (_f(_row, "opening_isa") - _f(_row, "from_isa"))
                     * _f(_row, "isa_growth_factor"))
            _worst = max(_worst, abs(_pred - _f(_row, "closing_total")))
        ok = _worst < 0.02          # the file rounds to pence
        if not ok:
            fails.append(f"the audit export does not reconcile (£{_worst:.4f})")
        print(f"  {'PASS' if ok else 'FAIL'}  "
              f"{'every row reconciles to its own columns':<50} "
              f"worst £{_worst:.4f} over {len(_rows)-1} rows")

        # F13c. The tax column is the PYTHON engine's tax function, row by row.
        # The export's whole claim is that a reader can recompute it; this is
        # that recomputation, done by the implementation verify.py already
        # checks against published HMRC figures.
        _bad, _checked = [], 0
        for _row in _rows[1:]:
            _g, _o, _u = (_f(_row, "gross_pension_withdrawal"),
                          _f(_row, "other_taxable_income"), _f(_row, "band_uprate"))
            if _g <= 0:
                continue
            _want = R.income_tax(_o + _g, "ruk", _u) - R.income_tax(_o, "ruk", _u)
            _checked += 1
            if abs(_want - _f(_row, "income_tax")) > 0.02:
                _bad.append((_row[0], _want, _f(_row, "income_tax")))
        ok = not _bad and _checked > 5
        if not ok:
            fails.append(f"audit tax column disagrees with the Python tax function: {_bad[:2]}")
        print(f"  {'PASS' if ok else 'FAIL'}  "
              f"{'income_tax matches the Python tax function':<50} "
              f"{_checked} taxed years, {len(_bad)} disagreements")

        # F13d. The trace's last closing balance IS the engine's own final
        # balance — the export cannot quietly be a different run.
        #
        # ON A POT THAT DOES NOT DEPLETE. The first draft of this check ran at
        # the site defaults, where a zero-volatility path empties the pot: it
        # compared £0.00 with £0.00 and passed, and would have passed just as
        # happily if the trace had come from an entirely different run. That is
        # 10d, and 37g is the same mistake made minutes after writing about it.
        # So the uncensored condition is asserted here, in the script, rather
        # than remembered.
        _big = dict(_ax, pot=3_000_000)
        _end = await pg.evaluate(
            "cfg => { const r = simulate(Object.assign({}, cfg, {trace:true})); "
            "return {fromTrace: r.trace[r.trace.length-1].close, "
            "fromBal: r.bal[(r.years+1)-1]}; }", _big)
        ok = _end["fromBal"] > 1_000.0
        if not ok:
            fails.append("F13d ran on a depleted pot — the comparison is censored")
        print(f"  {'PASS' if ok else 'FAIL'}  "
              f"{'F13d case is uncensored (pot never empties)':<50} "
              f"£{_end['fromBal']:>13,.0f}")
        chk("the trace's last row IS the engine's final balance",
            _end["fromTrace"], _end["fromBal"], 0.01)

        # F13e. The couple case is REFUSED, by message, not merely by throwing
        # something somewhere (10h). A trace that silently returned nothing
        # would be an output the caller believes is one thing and is another.
        _msg = await pg.evaluate("""cfg => { try {
            simulate(Object.assign({}, cfg, {trace:true, couple:true, pot2:300000,
              retire2:60, sp2:12548, spAge2:67})); return "no exception";
          } catch(e) { return e.message; } }""", _ax)
        ok = "audit trace is single-person only" in _msg
        if not ok:
            fails.append(f"the couple audit trace was not refused: {_msg}")
        print(f"  {'PASS' if ok else 'FAIL'}  "
              f"{'a couple audit trace is REFUSED':<50} {_msg[:30]!r}")

        # F13f. CSV quoting. Nothing in this export contains a comma today, but
        # a writer that breaks on one is a bug waiting for the first person who
        # exports something else through it.
        _q = await pg.evaluate(
            """() => toCSV([["a","b,c"],['say "hi"', 1]])""")
        ok = _q == 'a,"b,c"\r\n"say ""hi""",1'
        if not ok:
            fails.append(f"CSV quoting is wrong: {_q!r}")
        print(f"  {'PASS' if ok else 'FAIL'}  "
              f"{'commas and quotes are escaped correctly':<50} {_q[:24]!r}")

        print("\nF11. THE 10c AUDIT — AUTOMATED, AND IN BOTH DIRECTIONS (41a)")
        print("=" * 86)
        # 31 ran this audit BY HAND, in ONE direction — "grep for literals in
        # the JS that exist as named parameters in the Python" — and recorded
        # the result as "bounded at one". 41a was in the other direction, so
        # that grep could not have found it however carefully it was run.
        #
        # 37g's lesson is that a check you have to remember to run is a check
        # that does not exist. So both directions are built into the suite
        # here, and a new parameter on either side fails until someone records
        # where its counterpart lives — or records that it deliberately has
        # none.
        JS_TO_PY = {
            "pot": "Plan.pot / Person.pot",
            "pot2": "Person.pot",
            "retire": "Plan.retire_age / Person.age",
            "retire2": "Person.age",
            "end": "Plan.end_age / Household.end_age",
            "target": "Plan.target_net_income / Household.target_net_income",
            "sp": "Plan.state_pension_annual / Person.state_pension",
            "sp2": "Person.state_pension",
            "spAge": "Plan.state_pension_age / Person.sp_age",
            "spAge2": "Person.sp_age",
            "spGrowth": "Plan.sp_real_growth / Household.sp_real_growth",
            "other": "Plan.other_taxable_income / Person.other_income",
            "other2": "Person.other_income",
            "couple": "module choice: decumulation.simulate vs household.simulate_household",
            "deathAge": "Person.dies_at_age",
            "survFrac": "Household.survivor_fraction",
            "region": "Plan.region / Household.region",
            "freeze": "Plan.band_freeze_years / Household.band_freeze_years",
            "freezeInfl": "Plan.assumed_inflation / Household.assumed_inflation",
            "takePcls": "Plan.take_pcls / Person.take_pcls",
            "pclsSpend": "Plan.pcls_spent_immediately / Person.pcls_spent",
            "pclsHeld": "Plan.pcls_held_as / Household.pcls_held_as",
            "pclsCashReal": "Plan.pcls_cash_real / Household.pcls_cash_real",
            "isa": "Plan.isa / Household.isa",
            "isaHeld": "Plan.isa_held_as / Household.isa_held_as",
            "isaReal": "Plan.isa_real / Household.isa_real",
            "order": "Plan.withdrawal_order",
            "real": "FCAPrescribed.real / lognormal_real(real=...)",
            "vol": "FCAPrescribed.vol / lognormal_real(vol=...)",
            "conv": "FCAPrescribed.conv / lognormal_real(conv=...)  <- 41a, the gap this audit missed",
            "fee": "FCAPrescribed.fee / lognormal_real(fee=...)  <- 41b, and F11 caught it unmapped on the first run",
            # 41c. `trace` is the one entry in this map that is NOT a modelling
            # parameter. It records what the engine did; it does not change it.
            # That claim is exactly the kind of "it's fine, it only..." that
            # 41a hid behind, so it is not taken on trust: F13a asserts that
            # trace:true and trace:false return byte-identical results.
            "trace": "PRESENTATION ONLY, one-sided by decision — records path 0 for the CSV audit export; number-neutrality asserted in F13a, not assumed",
            "scen": "FCAPrescribed.scenario (resolved into P.real before simulate reads it)",
            "paths": "the n_paths dimension of the returns array",
        }
        # Deliberate one-sided parameters, each with the section that decided it.
        PY_ONLY = {
            "exact_gross_up": "37a — the JS ships the linear `frac` form; ~0.1pp, documented choice",
            "inflation_scenario": "31 — the JS pins FCA.inflation to 2% on purpose, index.html:544",
        }

        _src = pathlib.Path(PAGE.replace("file://", "")).read_text()
        _js_fields = set(re.findall(r"P\.([A-Za-z0-9_]+)", _src))
        _unmapped = sorted(_js_fields - set(JS_TO_PY))
        ok = not _unmapped
        if not ok:
            fails.append(f"JS parameter(s) with no recorded Python home: {_unmapped}")
        print(f"  {'PASS' if ok else 'FAIL'}  "
              f"{'every JS engine parameter has a Python home':<50} "
              f"{len(_js_fields)} fields, {len(_unmapped)} unmapped")
        if _unmapped:
            print(f"        UNMAPPED: {_unmapped}")

        _py_fields = {f.name for f in dataclasses.fields(Plan)}
        _py_fields |= set(inspect.signature(FCAPrescribed.__init__).parameters) - {"self"}
        # A Python parameter counts as covered if its name appears anywhere in
        # the map's values — deliberately crude, because the map is the record
        # and the point is to notice a NEW name, not to parse the old ones.
        _blob = " ".join(JS_TO_PY.values())
        _py_unmapped = sorted(f for f in _py_fields
                              if f not in _blob and f not in PY_ONLY)
        ok = not _py_unmapped
        if not ok:
            fails.append(f"Python parameter(s) the JS cannot express, unrecorded: {_py_unmapped}")
        print(f"  {'PASS' if ok else 'FAIL'}  "
              f"{'every Python parameter is mirrored or recorded':<50} "
              f"{len(_py_fields)} fields, {len(_py_unmapped)} unrecorded")
        if _py_unmapped:
            print(f"        UNRECORDED: {_py_unmapped}")
        for _k, _why in PY_ONLY.items():
            print(f"        one-sided BY DECISION: {_k} — {_why}")

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

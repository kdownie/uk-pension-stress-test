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

        ok = "findings.html#s10" in _idx and 'id="s10"' in _fnd
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

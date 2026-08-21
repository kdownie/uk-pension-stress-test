"""
Regenerate public/og.png — the social preview card — from the real engine.

The card quotes a result. That result is produced here by the same Python
engine the repo ships and the same default scenario the page loads with, so
the number on the card is checkable rather than decorative. If the FCA
FCA projection rates change, or the tax figures in uk_rules.py are updated, run
this again and the card follows.

    cd engine
    python make_og_card.py

Requires numpy and playwright (both already in requirements.txt; playwright
is otherwise only needed by verify_web.py).

Design constraints, deliberately:
  - No evaluative language. The card states the inputs and reports what the
    runs did. "35 of 100 runs funded the full income", never "risky", never
    "safe". See docs/REGULATORY-POSITION.md and CONTRIBUTING.md.
  - Colours are the site's own CSS custom properties, copied below.
  - The headline scenario is the page's DEFAULT scenario, so a visitor who
    arrives from the card sees the same number on load.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

from decumulation import Plan, simulate
from returns import FCAPrescribed

OUT = Path(__file__).resolve().parent.parent / "public" / "og.png"
HTML = Path(__file__).resolve().parent / "_og_card.html"

# The page's defaults, read off public/index.html input values.
PLAN = Plan(
    pot=500_000, retire_age=60, end_age=95, target_net_income=30_000,
    state_pension_age=67, take_pcls=True, pcls_spent_immediately=False,
    band_freeze_years=0, region="ruk",
)
VOL = 0.15
N_PATHS = 20_000
SEED = 20260820

# Site palette (public/index.html :root, light theme)
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
SURFACE, GRID, AXIS = "#fcfcfb", "#e1e0d9", "#898781"
S450, S100, BAD = "#2a78d6", "#cde2fb", "#e34948"

W, H = 566, 380          # chart box


def run():
    eng = FCAPrescribed(scenario="centre", vol=VOL)
    res = simulate(PLAN, eng.sample(N_PATHS, PLAN.years, seed=SEED), eng.describe())
    d = res.depleted_age
    ages = list(range(PLAN.retire_age, PLAN.end_age + 1))
    surv = [float(((d < 0) | (d > a)).mean()) for a in ages]
    half = next(a for a, s in zip(ages, surv) if s <= 0.5)
    return res, ages, surv, half


def build_html(res, ages, surv, half) -> str:
    def pt(i, s):
        return (i / (len(ages) - 1) * W, H - s * H)

    pts = [pt(i, s) for i, s in enumerate(surv)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    below = f"0,{H} {line} {W},{H}"
    above = f"0,0 {line} {W},0"
    grid = "".join(
        f'<line x1="0" y1="{H-f*H:.1f}" x2="{W}" y2="{H-f*H:.1f}" '
        f'stroke="{GRID}" stroke-width="1"/>' for f in (0.25, 0.5, 0.75))
    hx, hy = pt(ages.index(half), surv[ages.index(half)])
    ex, ey = pts[-1]
    pct = round(res.success_rate * 100)

    svg = f'''<svg width="{W}" height="{H+1}" viewBox="0 0 {W} {H+1}" xmlns="http://www.w3.org/2000/svg">
  <polygon points="{above}" fill="{BAD}" fill-opacity="0.10"/>
  <polygon points="{below}" fill="{S100}"/>
  {grid}
  <line x1="{hx:.1f}" y1="{hy:.1f}" x2="{hx:.1f}" y2="{H}" stroke="{INK2}" stroke-width="1.2" stroke-dasharray="3 4"/>
  <polyline points="{line}" fill="none" stroke="{S450}" stroke-width="3.4" stroke-linejoin="round" stroke-linecap="round"/>
  <circle cx="{hx:.1f}" cy="{hy:.1f}" r="5.2" fill="{SURFACE}" stroke="{S450}" stroke-width="3"/>
  <circle cx="{ex:.1f}" cy="{ey:.1f}" r="5.2" fill="{SURFACE}" stroke="{S450}" stroke-width="3"/>
  <line x1="0" y1="{H}" x2="{W}" y2="{H}" stroke="{AXIS}" stroke-width="1.5"/>
</svg>'''

    return f'''<!DOCTYPE html><html><head><meta charset="utf-8"><style>
 *{{margin:0;padding:0;box-sizing:border-box}}
 body{{width:1200px;height:630px;background:{SURFACE};
      font-family:"Liberation Sans",Arial,Helvetica,sans-serif;color:{INK};display:flex;overflow:hidden}}
 .left{{width:512px;padding:56px 0 50px 64px;display:flex;flex-direction:column}}
 .kicker{{font-size:19px;font-weight:700}}
 .rule{{width:44px;height:3px;background:{INK};margin:15px 0 32px}}
 .lead{{font-size:23px;line-height:1.4;color:{INK2}}}
 .hero{{font-size:80px;line-height:1;font-weight:700;letter-spacing:-.025em;margin:12px 0 10px}}
 .hero .em{{color:{BAD}}}
 .sub{{font-size:23px;line-height:1.38}}
 .stat{{margin-top:26px;font-size:21px;font-weight:700}}
 .assump{{margin-top:10px;font-size:16px;line-height:1.55;color:{MUTED}}}
 .spacer{{flex:1}}
 .domain{{font-size:17px;color:{MUTED}}}
 .right{{flex:1;padding:56px 58px 50px 22px;display:flex;flex-direction:column}}
 .ctitle{{font-size:16.5px;font-weight:700}}
 .csub{{font-size:14.5px;color:{MUTED};margin:3px 0 18px}}
 .cw{{position:relative;width:{W}px;height:{H+1}px}}
 .lab{{position:absolute;font-size:15px;color:{INK2}}}
 .l-out{{top:14px;left:14px}}
 .l-in{{bottom:46px;left:14px}}
 .l-end{{position:absolute;top:{H-surv[-1]*H-30:.0f}px;right:2px;font-weight:700;font-size:18px;color:{INK}}}
 .sw{{display:inline-block;width:14px;height:14px;border-radius:3px;vertical-align:-2px;margin-right:7px}}
 .xw{{position:relative;height:20px;margin-top:9px;font-size:14px;color:{MUTED}}}
 .xw span{{position:absolute;top:0;white-space:nowrap}}
</style></head><body>
<div class="left">
  <div class="kicker">UK pension stress test</div>
  <div class="rule"></div>
  <div class="lead">A &pound;{PLAN.pot:,.0f} pot drawing<br>&pound;{PLAN.target_net_income:,.0f} a year after tax:</div>
  <div class="hero">{pct} <span class="em">of 100</span></div>
  <div class="sub">runs funded the full income<br>from age {PLAN.retire_age} to {PLAN.end_age}.</div>
  <div class="stat">Half were dry by age {half}.</div>
  <div class="assump">FCA projection rates &middot; 2.94% real, {VOL:.0%} volatility<br>{N_PATHS:,} simulations &middot; every assumption editable</div>
  <div class="spacer"></div>
  <div class="domain">pensionstresstest.co.uk</div>
</div>
<div class="right">
  <div class="ctitle">Runs still paying the full income</div>
  <div class="csub">share of {N_PATHS:,} simulations, by age</div>
  <div class="cw">
    {svg}
    <div class="lab l-out"><span class="sw" style="background:#f9eae9;border:1px solid rgba(227,73,72,.35)"></span>ran out</div>
    <div class="lab l-in"><span class="sw" style="background:{S100}"></span>still paying in full</div>
    <div class="l-end">{pct}%</div>
  </div>
  <div class="xw">
    <span style="left:0">age {PLAN.retire_age}</span>
    <span style="left:{hx:.0f}px;transform:translateX(-50%)">age {half}</span>
    <span style="right:0">age {PLAN.end_age}</span>
  </div>
</div>
</body></html>'''


def main():
    res, ages, surv, half = run()
    print(res.summary())
    print(f"\ncard says: {round(res.success_rate*100)} of 100 runs · half dry by {half}")

    HTML.write_text(build_html(res, ages, surv, half), encoding="utf-8")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("playwright not installed — pip install playwright && playwright install chromium")

    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1200, "height": 630}, device_scale_factor=1)
        pg.goto(HTML.as_uri())
        pg.wait_for_timeout(400)
        pg.screenshot(path=str(OUT))
        b.close()
    HTML.unlink(missing_ok=True)
    print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()

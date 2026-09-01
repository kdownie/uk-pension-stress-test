# UK pension stress test

A free, independent tool for stress-testing a UK pension in drawdown. Every
assumption is visible and editable, the method is documented, and the whole
thing runs in your browser — nothing you type is sent anywhere, stored, or
logged.

**Not advice.** This project is not authorised or regulated by the Financial
Conduct Authority, gives no regulated financial advice, and makes no
recommendations. It names no pension product, fund or provider, and never will.
See [docs/REGULATORY-POSITION.md](docs/REGULATORY-POSITION.md).

---

## Why this exists

The good pension stress-testing engines are licensed to financial advisers. The
free consumer calculators mostly hide their assumptions and act as lead
generation. There is a gap between "here is a number, now speak to an adviser"
and "here is the model, here is every assumption, go and break it yourself."

This is an attempt at the second thing.

## What it does

- Simulates a pension in drawdown year by year, in today's money
- Income tax for **England/Wales/NI** and **Scotland**, 2026/27
- **Couples**: two pots, two State Pensions, two personal allowances, with each
  year's withdrawal split between the pots to minimise the household's tax
- **The survivor cliff**: what happens on first death, when a State Pension and
  a personal allowance are lost but the bills don't halve
- Tax-free cash, including the lump sum allowance cap
- **Fiscal drag** — what a nominal freeze in tax bands costs in real terms
- Return assumptions taken from the **FCA's own projection rates** (COBS 13
  Annex 2) rather than a house view — note these are the Handbook's *maximum*
  permitted rates, not prescribed ones; see
  [docs/FINDINGS.md §4](docs/FINDINGS.md)
- **Whether your return figure is a geometric or an arithmetic mean** — most
  calculators never say, and at the default settings the choice is worth 12.3
  percentage points of the result
- **Annual charges**, deducted from the return on invested money. Defaults to
  **0%**, so every other figure here is a return before charges
- **An ISA as a starting asset**, held as cash or invested, alongside the pension
- **Withdrawal ordering** — which pool is spent first, across four orders
- **State Pension growth above inflation**, with the triple lock's own formula
  run over ONS data to show what it has actually been worth

## What it does not do

Defined benefit pensions and annuities · the money purchase annual allowance ·
inheritance tax · care costs · holdings outside a pension or an ISA · mortality
as a probability rather than a date you choose — and only a partner's death,
never your own · anything at all about your personal circumstances.

## How to run it

Open `public/index.html` in a browser. That's the whole thing — one self-contained
file, no server, no build step, no dependencies.

## How to check it

The point of this project is that you don't have to take its word for anything.

There are **two independent implementations** of the same rules: the JavaScript
that runs in your browser, and a Python reference engine in `engine/`. They are
checked against each other, and the Python one is checked against figures
computed from the legislated rates.

```bash
cd engine
pip install -r requirements.txt

python verify.py             # tax and simulator vs legislated rates & closed forms
python verify_household.py   # Scottish bands, couples, tax-optimal splitting
python verify_web.py         # the browser engine vs the Python engine
```

What those actually verify:

| Check | Against what |
|---|---|
| Income tax | Computed from the legislated rates, incl. £110,000 → £33,432 and £150,000 → £53,703 |
| Scottish tax | Hand-computed from the published band table |
| Gross-up | Must be an exact inverse of the tax function |
| Simulator | A closed-form annuity recursion at zero volatility |
| Tax-optimal splitting | Brute-force search over 400 split ratios, both regions |
| Browser vs Python | Same inputs must give the same answers |

If you find a case where they disagree, or where either disagrees with reality,
please open an issue. That is the most useful thing anyone can do here.

## The tax detail most calculators get wrong

GOV.UK presents income tax bands as income ranges (£12,571–£50,270 at 20%),
which silently assumes a full personal allowance. The real mechanics are that
the basic-rate band is £37,700 wide and sits on top of whatever allowance
survives the £100,000 taper — so above £100,000 the 40% band starts *lower*,
not at £50,270.

Building from the published table rather than the mechanics understates tax
across the taper region. The error is exactly 40% of the allowance lost, so it
reaches **£5,028** once the allowance is fully gone at £125,140 and stays there
for every income above that — a plateau, not a peak. That is exactly the range a
large pot in drawdown can reach. This engine gets it right and the test suite
proves it.

## Assumptions

Every figure taken from legislation lives in one block in
`engine/uk_rules.py`, with a source URL and the date it was checked. Nothing is
hard-coded anywhere else. Return assumptions come from
[FCA Handbook COBS 13 Annex 2](https://handbook.fca.org.uk/handbook/COBS/13/Annex2.html).

Tax rules change. If you're reading this well after the check dates in that
file, verify before relying on anything.

## Documents

| | |
|---|---|
| [Regulatory position](docs/REGULATORY-POSITION.md) | Where the advice/guidance boundary sits and the rules this project is built by |
| [Findings](docs/FINDINGS.md) | What the modelling actually showed, including results that contradicted the hypothesis |
| [Findings, for a general reader](https://pensionstresstest.co.uk/findings.html) | The same material written for someone who is not a developer |
| [Data sourcing](docs/DATA-SOURCING.md) | Why there is no historical dataset, and the licensing behind that |

## Known limitations

The historical-bootstrap engine in `engine/returns.py` currently runs on a
**synthetic** market series, not real market data — free, redistributable
long-run UK *return* data is a licensing problem, not a coding one. (Real ONS
data *is* bundled, in `engine/ons_data.py`, but it sources the inflation and
State Pension assumptions — it is not a return series.) This is documented at
length in [docs/DATA-SOURCING.md](docs/DATA-SOURCING.md) and flagged loudly in
the code. The browser tool does not use it; it uses the FCA projection rates.

## Privacy

No accounts, no cookies, no analytics, no server, no logs. The page is a single
file and the maths runs on your own machine. Close the tab and it's gone.

## Contributing

Corrections to the tax rules, the sources, or the maths are very welcome —
especially with a failing test case. Please don't send pull requests that add
product names, provider comparisons, affiliate links, or anything that reads as
a recommendation; those would breach the design rules in the regulatory
position document.

## Credits

**Built by Kevin Downie with Claude (Anthropic).** Responsibility for what's
published here is Kevin's — if something is wrong, please open an issue.

The stochastic path work draws on [neural-sde](https://pypi.org/project/neural-sde/),
also built by Kevin with Claude.

## Licence

MIT — see [LICENSE](LICENSE). That covers the **code**.

The only third-party data in this repository is in `engine/ons_data.py`: three
Office for National Statistics series used to source the inflation and State
Pension assumptions. **Contains public sector information licensed under the
[Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/)**,
which permits commercial use, redistribution and adaptation with attribution —
so it sits alongside MIT without conflict.

**No Bank of England or Jordà-Schularick-Taylor data is bundled, and none should
be.** Both are non-commercial, which MIT cannot sublicense. See
[docs/DATA-SOURCING.md](docs/DATA-SOURCING.md) §I.

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
- Return assumptions taken from the **FCA's own prescribed projection rates**
  rather than a house view

## What it does not do

Defined benefit pensions and annuities · the money purchase annual allowance ·
inheritance tax · investment charges · care costs · ISAs and unwrapped holdings
· mortality as a probability rather than a date you choose — and only a partner's death, never your own · anything at all
about your personal circumstances.

## How to run it

Open `index.html` in a browser. That's the whole thing — one self-contained
file, no server, no build step, no dependencies.

## How to check it

The point of this project is that you don't have to take its word for anything.

There are **two independent implementations** of the same rules: the JavaScript
that runs in your browser, and a Python reference engine in `engine/`. They are
checked against each other, and the Python one is checked against published
figures.

```bash
cd engine
pip install -r requirements.txt

python verify.py             # tax and simulator vs published figures & closed forms
python verify_household.py   # Scottish bands, couples, tax-optimal splitting
python verify_web.py         # the browser engine vs the Python engine
```

What those actually verify:

| Check | Against what |
|---|---|
| Income tax | Published figures, incl. £110,000 → £33,432 and £150,000 → £53,703 |
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

Building from the published table rather than the mechanics understates tax on
a £110,000 income by about £5,000. That is exactly the range a large pot in
drawdown can reach. This engine gets it right and the test suite proves it.

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
| [Data sourcing](docs/DATA-SOURCING.md) | Why there is no historical dataset, and the licensing behind that |

## Known limitations

The historical-bootstrap engine in `engine/returns.py` currently runs on a
**synthetic** market series, not real data — free, redistributable long-run UK
return data is a licensing problem, not a coding one. This is documented at
length in [docs/DATA-SOURCING.md](docs/DATA-SOURCING.md) and flagged loudly in
the code. The browser tool does not use it; it uses the FCA prescribed rates.

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

MIT — see [LICENSE](LICENSE).

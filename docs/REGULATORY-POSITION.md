# Regulatory position — the advice/guidance boundary

**15 August 2026.** What the FCA's own guidance says, where this tool sits, and
the specific changes needed before it goes public.

> **I am not a lawyer and this is not legal advice.** It is a careful reading of
> primary sources, with everything quoted and linked so it can be checked. Before
> launch, get a compliance professional to read this document and the site. The
> reading below is deliberately cautious; a specialist may well tell you there is
> more room than I've allowed.

---

## 1. The finding that inverts the usual intuition

Most people assume that being unregulated means the advice rules don't apply to
them. **The opposite is true.** A *narrower* test applies to authorised firms; the
*wider* one applies to everyone else.

PERG 8.24.1B(3): an appropriately authorised firm "may give non-personalised
advice without the need to have advising on investments in its permission" —
for it, non-personalised advice "will be an unregulated activity".

PERG 8.24.1D, on unauthorised persons: "All the material in this chapter about
advising on investments is relevant, except for PERG 8.30B (Personal
recommendations)… **It is not relevant to such a person whether or not the advice
is a personal recommendation.**"

So the familiar defence — "it's not a personal recommendation, it's generic" —
is **not available to you**. An unauthorised person is caught by the wider
Article 53 test: advice to an investor on the merits of buying, selling or
holding *a particular investment*.

That is the single most important thing on this page, and it changes how the site
should be built.

## 2. What actually protects you

Not the disclaimer. The **"particular investment"** requirement.

PERG 8.24.2(2): the investment "must be a particular investment."

Your tool never names one. No fund, no provider, no product, no annuity quote,
no "drawdown versus annuity". It models an abstract pot with a user-set return.
There is no particular investment for advice to attach to, so the Article 53
activity is not engaged — regardless of how personalised the inputs are.

**This is the load-bearing wall. Design rule: the site never names, ranks,
compares or implies a specific product or provider.** Everything else in this
document is secondary to that one rule.

## 3. Where information becomes advice

If the site ever does touch a particular investment, these are the tests:

- **PERG 8.28.2(3)** — regulated advice includes any communication that "in the
  particular context in which it is given, goes beyond the mere provision of
  information and is objectively likely to influence the customer's decision
  whether or not to buy or sell."
- **PERG 8.28.2(4)** — information becomes advice when "accompanied by comment or
  value judgment on the relevance of that information to the customer's investment
  decision", or when it is "itself the product of a process of selection involving
  a value judgment so that the information will tend to influence the decision."
- **PERG 8.28.6** — "Any significant element of evaluation, value judgment or
  persuasion is likely to mean that advice is being given."
- **PERG 8.28.5** — the impartial observer test: would a reasonable observer
  conclude the customer could have understood it as advice?

Note how low the bar in 8.28.6 is. **Persuasion counts.** Not just recommending —
nudging.

## 4. The FCA's own worked examples for tools

FG15/1 is the guidance that deals directly with calculators and filtering.

**Not regulated advice:**

- *Example A* — a site giving generic investment information without interactivity
  or bias toward specific investments: "simply giving information without making
  any comment or value judgement on its relevance to decisions which an investor
  may make does not involve advising on investments."
- *Example D(1)* — filtering on objective factors, because the site "displays
  parts of an existing list based on what the customer wants to see."
- *Example F* — educational material and risk-profiling tools that help customers
  decide for themselves, where information is presented neutrally.

**Becomes regulated advice:**

- *Example D(2–6)* — filtering that applies the firm's own judgment about risk or
  ranking, because it applies "skill and judgement to arrive at the ranking".
- *Example E(1)* — filtering on personal facts (age, resources, retirement plans)
  where "the filtering is not based solely on what the investor wants but also on
  **what is good for them**."
- *Paragraph 3.10* — a decision tree is a personal recommendation if it makes any
  "judgement or assessment that would result in a single product or list of
  products being identified as suitable."
- *Paragraph 3.24* — implicit recommendations count, e.g. "people like you buy
  this product."

Your tool takes personal facts, but it doesn't filter *products* by them. It
computes an outcome and hands it back. That's Example A/F territory, not E(1).

## 5. Audit of the current wording

Three things to change. Everything else reads as neutral.

| Current | Problem | Suggested |
|---|---|---|
| "income **sustainable** in 9 runs out of 10" | "Sustainable" is our evaluative label, and 90% is our chosen threshold presented as the answer. Closest thing on the page to a recommendation. | "income that lasted in 9 runs out of 10" — describe what happened, don't label it safe |
| "The second box is the single most powerful control on this page. **Try it.**" | Direct instruction. PERG 8.28.6 catches persuasion, not just recommendation. | State the finding neutrally and let them find it |
| "Switch it and watch." | Same, milder. | "The two conventions give different answers." |

Also **missing** and worth adding:

- An explicit statement that you are **not authorised or regulated by the FCA**,
  and that nothing on the site is regulated advice.
- A statement that outputs are **illustrations of a model, not predictions**.
- The existing MoneyHelper and Pension Wise signposting is good and should stay —
  pointing to free impartial guidance is itself evidence you are not positioning
  yourself as its substitute.

## 6. The second perimeter: financial promotions

Section 21 FSMA restricts communicating an invitation or inducement to engage in
investment activity, in the course of business. A free, non-commercial tool that
promotes no product is very unlikely to be caught, but note the two things that
would change that:

- **Affiliate links or product referrals.** These would be an inducement, and
  they'd also breach the CC BY-NC-SA terms if you ever use JST data. One decision
  breaks two things at once.
- **Naming providers**, even neutrally, alongside anything that reads as
  endorsement.

This is the perimeter I've researched least. Flag it to whoever reviews this.

## 7. What changed in April 2026

The FCA's **targeted support** regime went live on 6 April 2026 (PS25/22), letting
authorised firms give suggestions to groups of consumers with common
characteristics without it being full advice. Firms could apply for the permission
from 2 March 2026.

It doesn't help you — it requires specific permission. But it matters for
positioning: the "helpful but not advice" space is now formally occupied by
regulated firms operating under a defined regime. That makes staying visibly and
clearly outside the perimeter more valuable, not less. Your differentiator is
transparency of method, not proximity to advice.

## 8. Rules to build by

1. **Never name a particular investment, product or provider.** The wall.
2. **Never rank, score or select options for the user.** Compute what they ask.
3. **Never say what someone should do**, including softly — no "try", "consider",
   "you may want to".
4. **Describe outputs, don't label them.** "Lasted in 9 of 10 runs", not "safe".
5. **Every threshold is theirs.** 90% confidence, 67% survivor fraction, 15%
   volatility — all adjustable, all disclosed. You already do this.
6. **Signpost to MoneyHelper and Pension Wise** on any page dealing with an
   irreversible decision.
7. **No affiliate links, referrals or sponsorship.** Ever.
8. **Keep the assumptions register dated and sourced.** It's your evidence of
   neutral information rather than judgment.

## 9. Before launch

- [ ] Make the three wording changes in section 5
- [ ] Add the not-authorised statement and the not-a-prediction statement
- [ ] Have a compliance professional review this document and the live site
- [ ] Decide and record the position on financial promotions
- [ ] Consider whether to publish this document itself — a site that shows its
      own regulatory reasoning is doing the same thing with the law that it
      already does with its assumptions

## Sources

- [PERG 8.24 — Advising on investments](https://www.handbook.fca.org.uk/handbook/PERG/8/24.html)
- [PERG 8.28 — Advice or information](https://handbook.fca.org.uk/handbook/PERG/8/28.html)
- [FG15/1 — Retail investment advice: clarifying the boundaries](https://www.fca.org.uk/publication/finalised-guidance/fg15-01.pdf)
- [PS25/22 — Rules for targeted support](https://www.fca.org.uk/publications/policy-statements/ps25-22-consumer-pensions-investment-decisions-rules-targeted-support)
- [FCA — Advice Guidance Boundary Review](https://www.fca.org.uk/firms/advice-guidance-boundary-review)
- [MoneyHelper](https://www.moneyhelper.org.uk/)

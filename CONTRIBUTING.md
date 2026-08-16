# Contributing

The most valuable contribution is a **failing test case**. If you think a
number is wrong, add a case to `engine/verify.py` or
`engine/verify_household.py` that fails, and the fix becomes obvious.

## Ground rules

These come from [docs/REGULATORY-POSITION.md](docs/REGULATORY-POSITION.md) and
are not negotiable, because the project's position outside the FCA perimeter
depends on them:

1. **Never name a particular investment, product or provider.** This is what
   keeps the tool outside the regulated activity of advising on investments.
2. **Never rank, score or select options for the user.** Compute what they ask.
3. **Never say what someone should do**, including softly — no "try",
   "consider", "you may want to".
4. **Describe outputs, don't label them.** "Lasted in 9 of 10 runs", not "safe".
5. **Every threshold belongs to the user** and must be adjustable and disclosed.
6. **No affiliate links, referrals or sponsorship.**

## Adding or changing a legislated figure

Every such figure lives in the `ASSUMPTIONS` or `REGIONS` block in
`engine/uk_rules.py`, and is mirrored in `index.html`. Each needs a source URL
and the date you checked it. Then run `engine/verify_web.py`, which will fail
if the two implementations disagree.

## Before opening a pull request

```bash
cd engine
python verify.py && python verify_household.py && python verify_web.py
```

All three must pass.

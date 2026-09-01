# Licence query — Bank of England

**CLOSED 31 August 2026. The permission was granted and has gone unused.** The
dataset could not do either job it was fetched for — equity total returns (§6d)
or the two policy assumption ranges (§7) — and the project sources those from
ONS instead. See `DATA-SOURCING.md` §I. Nothing here is blocking anything.

*Originally, and left for the record:* the licence position for *A Millennium of
Macroeconomic Data for the UK* is what blocks the historical-return engine.
Nothing shipped depends on it: the live engine uses FCA projection rates and
needs no dataset, and `returns.py` isolates the whole dependency behind
`load_history()`.

This file is the correspondence record.

| Date | Event |
|---|---|
| 15 Aug 2026 | Query sent to `DSD_EDITOR@bankofengland.co.uk`. |
| 17 Aug 2026 | Holding reply from **BEEDS portal administration** — "forwarded your query to the relevant business area". |
| 20 Aug 2026 | No substantive reply. Query identified as mis-routed; follow-up sent to the dataset's named contact. |
| **25 Aug 2026** | **Substantive reply from Ryland Thomas, one of the dataset's two authors, copying Sally Srinivasan who administers the Bank's research datasets. Permission granted — see §6. Thread closed with a short acknowledgement the same evening.** |
| **31 Aug 2026** | **Reported back that the permission has gone unused, with both reasons — see §7.** Also disclosed that this file quotes his reply publicly, and offered to summarise or remove it. |

---

## 1. The query as sent, 15 August 2026

**To:** `DSD_EDITOR@bankofengland.co.uk`
**Subject:** Licensing terms for "A Millennium of Macroeconomic Data for the UK" (Thomas & Dimsdale, v3.1)

Dear Bank of England,

I am building a free, non-commercial public information website about UK pensions
and retirement planning, and I would like to use the historical series in
*A Millennium of Macroeconomic Data for the UK* (Thomas, R. and Dimsdale, N., 2017,
version 3.1) as the basis for historical return modelling.

Third-party mirrors of the dataset state that it is published under the Open
Government Licence v3.0, but I cannot find a licence statement on the Bank's own
research datasets page. Could you confirm:

1. Under what licence or terms the dataset is published.
2. Whether those terms permit **redistribution** of the data, or of series derived
   from it, as part of a publicly accessible website.
3. Whether they permit **adaptation** — specifically, constructing total-return
   series from the published price and yield data.
4. Whether any distinction applies between non-commercial and commercial use,
   should the site later need to cover its hosting costs.
5. The attribution wording you would like used.

I am happy to display whatever acknowledgement you require.

Many thanks,

Kevin Downie

---

## 2. It went to the wrong team

The 17 August acknowledgement came from **BEEDS portal administration**. BEEDS is
the Bank of England Electronic Data Submission portal — the system regulated
firms use to file statutory statistical returns. Its administrators handle portal
access and reporting deadlines, and have no connection to research dataset
licensing. That is why the reply was a routing acknowledgement rather than an
answer.

**The contact for this dataset is published on the page the query was about.**
[bankofengland.co.uk/statistics/research-datasets](https://www.bankofengland.co.uk/statistics/research-datasets)
names `ryland.thomas@bankofengland.co.uk` for *A millennium of macroeconomic
data*. Ryland Thomas is one of the dataset's two authors.

---

## 3. What the Bank's published terms already establish

Read from [bankofengland.co.uk/legal](https://www.bankofengland.co.uk/legal) on
20 August 2026. All four points support the caution taken in
[DATA-SOURCING.md](DATA-SOURCING.md):

1. **Bank material is not Crown copyright.** Copyright is owned by "the Governor
   and Company of the Bank of England" — a distinct legal person, not a
   government department. The Open Government Licence therefore does **not**
   apply by default the way it does to a ministry.
2. **The OGL statement is scoped to the "Bank of England Database"** — the
   interactive statistical database — not to everything the Bank publishes. The
   Millennium dataset sits under *Research datasets*, and that page carries no
   licence statement at all.
3. **The default permission does not cover this use.** The Bank grants download,
   display or print "for personal use or internal use within an individual
   organisation for non-commercial purposes". Publishing derived series on a
   public website is neither. Beyond that requires authorisation from the **Head
   of Communications Division**. The Bank does note it "typically grants
   permission for non-commercial re-use... particularly in an academic or
   education context" — but that is permission, not a licence.
4. **There is precedent for carve-outs.** Some exchange-rate series are
   explicitly excluded from the Bank's OGL because they are "reproduced by the
   Bank under licence from third parties". The Millennium dataset is a
   compilation drawn from many academic sources, so a similar exclusion is
   plausible — which is exactly what question 2 of the follow-up asks.

**The third-party OGL claims are unsourced.** The datahub.io mirror labels the
dataset OGL v3.0 but links only to the National Archives licence text; it cites
no Bank statement asserting that licence. Given point 1, the mirrors are not
evidence of the Bank's position and should not be relied on.

---

## 4. Follow-up as sent, 20 August 2026

**To:** `ryland.thomas@bankofengland.co.uk`
**Subject:** "A Millennium of Macroeconomic Data for the UK" (v3.1) — licensing, following a query of 15 August

Dear Ryland Thomas,

I sent this query to DSD_EDITOR on 15 August. It was acknowledged on 17 August by
the BEEDS portal team, who forwarded it onward — I suspect to the wrong area,
BEEDS being the reporting portal. I am writing to you directly as the contact
given for this dataset on the Bank's research datasets page. My apologies if it
has already reached you by another route.

I maintain a free, open-source tool that models UK pension drawdown:

- https://pensionstresstest.co.uk
- https://github.com/kdownie/uk-pension-stress-test

It takes no payment, carries no advertising or affiliate links, collects no data,
names no financial product or provider, and gives no advice or recommendation —
it is not regulated by the FCA and does not need to be. The simulation engine,
the legislated tax figures with their sources, and three verification scripts are
all public, so the modelling can be checked rather than taken on trust. There is
a methodology and findings write-up at https://pensionstresstest.co.uk/findings.html
which cites the underlying literature, if it helps in judging the character of
the site.

At present it uses the FCA's projection rates rather than historical data,
precisely because I could not establish the licence position for your dataset. I
would like to use *A Millennium of Macroeconomic Data for the UK* (v3.1) to build
historical return series instead.

I have read the terms at bankofengland.co.uk/legal, and I take it that copyright
is held by the Governor and Company rather than being Crown copyright, so the
Open Government Licence does not apply automatically; that the OGL statement is
scoped to the Bank of England Database rather than to the research datasets; and
that the default permission — personal or internal non-commercial use — would not
extend to publishing derived series on a website. Several third-party mirrors
label the dataset OGL v3.0, but I can find no Bank statement to that effect, so I
would rather ask than assume.

My questions, narrowest first:

1. Would you be content for me to publish a *derived* annual total-return series
   constructed from the dataset's price and yield data — not the workbook itself
   — with attribution and a link to the Bank's page?
2. If so, is any part of the dataset excluded, in the way some exchange-rate
   series are excluded from the Bank's OGL because they are held under
   third-party licence?
3. If a fuller permission is needed, is the Head of Communications Division the
   right route, and would you be willing to point me there?
4. What attribution wording would you like used?

One point of honesty: the site is free and I intend it to stay that way, but it
may at some point need to cover its own hosting costs. I would not treat that as
commercial use without asking you first.

If the answer is no, that is a perfectly good answer and I will carry on with the
FCA rates. Either way, thank you for putting the dataset together — it is a
remarkable piece of work.

With thanks,

Kevin Downie

**Why it is shaped that way.** The questions run narrowest first, so question 1
alone unblocks the build without needing redistribution of the workbook. Saying
no is made cheap, and question 3 lets the recipient redirect in one line rather
than three exchanges. The site is not *claimed* to be academic or educational —
the Bank's phrase describes when it grants permission, not a category anyone can
qualify for — so the characteristics are listed and linked, and the conclusion is
left to the reader.

---

## 5. What each answer means for the build

| Answer | Consequence |
|---|---|
| OGL v3.0 confirmed | Best case. Use it, attribute it, all future options stay open. |
| Bespoke terms, redistribution allowed | Usable. Read the attribution and any no-endorsement clause carefully. |
| Non-commercial only | Same position as JST — usable now, forecloses monetisation later. |
| No redistribution | Ship derived statistics only (fitted moments, bootstrap blocks), not the series. Check whether even that is permitted. |
| No reply | No change. The FCA-rates engine is what shipped, so the fallback is already the live position. |

If a second no-reply follows, the next escalation is the Head of Communications
Division (§3 point 3) rather than another email to the same address. There is no
deadline pressure: `load_history()` in `engine/returns.py` is the single function
that would change, and it is documented as such.

---

## 6. The answer, 25 August 2026 — RESOLVED

Reply from **Ryland Thomas**, Senior Research Advisor, Monetary Policy Strategy
Division, copying **Sally Srinivasan** (research datasets). The four questions
of §4 were answered by number.

| Q | Asked | Answered |
|---|---|---|
| **1** | Publish a **derived** total-return series, with attribution? | **"Yes that is absolutely fine, if you are constructing/deriving your own return series from the data."** |
| **2** | Any series excluded under third-party licence? | None named. *"It is usually fine to reproduce any series in the spreadsheet provided it is for non-commercial purposes and that you acknowledge the source of any raw data we have published using the references provided alongside citing the spreadsheet as well."* The Bank holds permissions from the original authors *"as far as possible"*, on a non-commercial full-citation basis. Doubts → ask. |
| **3** | Is the Head of Communications Division the right route? | Not needed. Handled directly, with Sally Srinivasan copied in to advise on attribution. |
| **4** | Attribution wording? | The **Thomas and Dimsdale** reference in the **citation section of the workbook's front page**, *plus* the original references for any underlying raw series used, *plus* a citation of the spreadsheet itself. |

**Broader than the ask.** Question 1 sought permission for a *derived* series;
answer 2 permits reproducing **the series themselves**.

**Forward-looking:** *"I am preparing the next version of the Millennium dataset
which I am hoping we can put under an explicit open licence, pending checking
permissions and copyright on the new series we are adding."* The non-commercial
constraint may therefore be temporary.

**Commercial use is not foreclosed, only deferred:** *"if you do proceed to
reproduce anything on a commercial basis please do get back in touch and we can
discuss."*

### 6a. Which row of §5 this is

**"Non-commercial only."** §5 predicted the consequence: *"same position as JST
— usable now, forecloses monetisation later."* Correct, and it costs this
project nothing, because design rule 6 already bans affiliate links, referrals
and sponsorship permanently.

**The one live edge case** is hosting costs. Raised honestly in the 20 August
email and not ruled out — Ryland asked to discuss it. **Ask Sally before acting,
not after.** Deliberately left out of the acknowledgement, there being nothing
concrete to decide.

### 6b. What §3 got right in advance

Every point in §3, worked out from the Bank's published terms **before any
reply**, was confirmed: not Crown copyright, the OGL statement scoped to the
Bank of England Database rather than to research datasets, and the default
permission not extending to publishing on a website. **The datahub.io OGL label
is wrong**, and §3's refusal to rely on it was correct.

### 6c. Why the email worked, for next time

Worth recording, because the reply was more generous than the question.

- **Questions narrowest first.** Question 1 alone unblocked the build, and it
  could be answered in nine words without consulting anyone. It was.
- **Saying no was made cheap** — *"If the answer is no, that is a perfectly good
  answer and I will carry on with the FCA rates."*
- **One line let him redirect** (question 3) instead of a three-email chain.
- **The site's character was shown, not claimed** — free, no advertising, no
  affiliate links, no data collected, no product named, source public — and the
  conclusion left to the reader. §4 notes the site was deliberately *not*
  described as "academic or educational".
- **A limitation was volunteered** (possible hosting costs) rather than hidden.

### 6d. And then the data turned out not to fit

**The permission is real and the equity plan died anyway.** The Millennium
dataset's only equity series is a price index running 1962–2017, with no
dividend yield, so total returns cannot be constructed and the worst British
starting year (1900) sits outside the span entirely.

**Full analysis in `DATA-SOURCING.md` §H.** The permission still matters — it
covers long-run UK inflation, rates and wages, which is where the project now
intends to use it.

> **WRONG, 31 August 2026 — the inflation plan died too.** The dataset **ends in
> 2016**, and the assumption it was meant to bound depends most on 2022, when
> CPI reached 9.1%. Sourced from this workbook the range would have topped out
> at 4.5%. ONS series were used instead. `DATA-SOURCING.md` §I, and the reason
> is asserted in `verify.py` section I5 so it cannot be quietly reversed.

**The lesson, recorded because it cost ten days:** the field list was the
cheaper question and it was asked second. **Check that the data can do the job
before chasing the rights to it.**

---

## 7. Reported back, 31 August 2026 — the permission goes unused

**To:** `ryland.thomas@bankofengland.co.uk`
**Cc:** Sally Srinivasan
**Subject:** "A Millennium of Macroeconomic Data for the UK" — thank you, and what happened next

> **Recorded from the draft as prepared.** If the sent version differs, this
> entry should be corrected to match what actually went — the point of this file
> is that it is the record, not the intention.

Dear Ryland,

Thank you for your answer of 25 August, and for dealing with it directly rather
than sending me round the Communications route. It was a good deal more generous
than my question.

I said I would report back. The honest report is that I have not used the
dataset, and the two reasons may be worth knowing while you are preparing the
next version.

**Equity total returns.** The only equity price index in v3.1 begins in April
1962 and carries no dividend yield, so total returns cannot be constructed from
the workbook alone. The start date turned out to matter more than the missing
dividends: the UK result I wanted to test rests on a 1900 start year, sixty-two
years before the series begins. A withdrawal test run on 1962–2017 would come
back more optimistic than the truth, and look authoritative while doing it.

Your signature pointed me at the ESCoE historical data collection, which I had
not found on my own. The Actuaries Investment Share Index 1923–1962 does carry
both prices and yields, and with Campbell, Grossman and Turner before it, a UK
total-return series back to the 1920s is clearly constructible. I decided
against building it — three sources, three splice points and three sets of
citations, for an improvement my own testing puts at about two percentage
points on a figure already uncertain by twelve. That is a judgement about scope
in a project I maintain alone, not a criticism of the data.

**Long-run inflation.** This was the use I actually expected to make of the
dataset, and it foundered on something simpler: v3.1 ends in 2016. The
assumption I was trying to bound is what inflation does while tax thresholds
are frozen, and the observation that matters most is 2022, when CPI reached
9.1%. Sourced from the Millennium data the range would have topped out at 4.5%.
I have used ONS series instead — CPI and average weekly earnings, 1989 and 2000
to date, under the Open Government Licence.

So the permission has gone unused. I would rather tell you that than leave it
looking as though it had quietly been taken up.

One thing I should mention: I keep the project's working notes public, and that
includes the correspondence on this licence question, with your reply quoted.
If you would prefer it summarised rather than quoted, or removed, say the word
and I will change it — it did not occur to me to ask first, and it should have.

I would be glad to hear when the openly-licensed version lands, particularly if
it extends past 2016.

With thanks,

Kevin Downie
https://pensionstresstest.co.uk

---

### 7a. Why this was sent at all

The permission was granted generously and then not used. Saying nothing would
have left a courteous correspondent to assume his answer had been taken up, and
would have wasted the one genuinely useful thing this episode produced: **two
specific, checkable reasons why a dataset did not fit two jobs, delivered to the
person preparing its next version.** No dividend yield, and it stops in 2016.
Both are things a maintainer can act on.

### 7b. The disclosure that should have come first

This file quotes Ryland's reply verbatim and the repository is public. **He was
never asked.** It is a professional reply about licensing rather than anything
personal, and the risk is low — but low risk is not the same as permission, and
the right moment to raise it was before publishing, not six days after.

Raised in the email, with an offer to summarise or remove. **If he asks for
either, do it the same day and note it here.**

**The general rule this leaves:** when correspondence is going into a public
record, tell the correspondent while you are still writing to them anyway. It
costs one sentence in an email that was being sent regardless.

### 7c. What remains open with the Bank

- **Hosting costs.** §6a: Ryland did not rule out a donation or hosting link and
  asked to discuss it. Still unresolved, and still nothing concrete to decide.
  **Ask Sally before acting, not after.** Deliberately kept out of the 31 August
  email for that reason.
- **The openly-licensed version.** Asked to be told when it lands. If it extends
  past 2016 the inflation question is worth reopening — though ONS covers it
  perfectly well under a licence that raises no MIT conflict, so it would be a
  matter of preference rather than need.


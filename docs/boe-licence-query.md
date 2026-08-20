# Licence query — Bank of England

The licence position for *A Millennium of Macroeconomic Data for the UK* is what
blocks the historical-return engine. Nothing shipped depends on it: the live
engine uses FCA projection rates and needs no dataset, and `returns.py` isolates
the whole dependency behind `load_history()`.

This file is the correspondence record.

| Date | Event |
|---|---|
| 15 Aug 2026 | Query sent to `DSD_EDITOR@bankofengland.co.uk`. |
| 17 Aug 2026 | Holding reply from **BEEDS portal administration** — "forwarded your query to the relevant business area". |
| 20 Aug 2026 | No substantive reply. Query identified as mis-routed; follow-up sent to the dataset's named contact. |

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

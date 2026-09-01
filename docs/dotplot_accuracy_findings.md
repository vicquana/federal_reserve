# How accurate is the SEP dot plot? A direct measurement

**Date:** 2026-09-01
**Sample:** 42 SEP releases, 2015-09-17 through 2026-06-17 (the era
with a machine-readable Median + Federal Funds Rate row in the
same-day release PDF; see "Scope and data gaps" below).
**Reproduce:**

```bash
uv run --with-requirements requirements.txt python3 src/download_sep.py --dates-file data/raw/sep_dates.txt --out data/raw/sep
uv run --with-requirements requirements.txt python3 src/download_fed_funds_rate.py data/raw/fedfunds_monthly.csv
uv run --with-requirements requirements.txt python3 src/parse_sep_dotplot.py data/raw/sep data/interim/sep_dotplot.csv
uv run --with-requirements requirements.txt python3 src/estimate_dotplot_accuracy.py data/interim/sep_dotplot.csv data/raw/fedfunds_monthly.csv docs/dotplot_accuracy_results.csv
```

## Method

For each SEP release, the median "dot" for the federal funds rate at
each future year-end (current year, +1, +2, +3) is compared to the
*realized* effective federal funds rate in December of that year (or
the latest available month, for years not yet finished). Longer-run
projections are excluded (no fixed comparison date -- "longer run"
means "5-6 years out, in the absence of further shocks").

## Result: accuracy degrades sharply with horizon, and the direction of error flips

| Horizon | Mean absolute error (pp) | Mean signed error (pp) | n |
|---|---|---|---|
| Current year | 0.25 | +0.06 | 42 |
| 1 year ahead | 1.02 | -0.10 | 39 |
| 2 years ahead | 1.85 | -0.29 | 35 |
| 3 years ahead | 2.16 | -0.30 | 18 |

- **Current-year projections are quite good** (median error a quarter
  of a percentage point, no systematic bias) -- unsurprising, since
  by the time of a given SEP release most of that year's meetings
  (and hence rate decisions) have already happened or are imminent.
- **Accuracy degrades roughly linearly with horizon**, from 0.25pp at
  0 years out to over 2pp at 3 years out.
- **Longer-horizon projections are systematically biased toward
  underestimating the eventual rate** (negative mean error = dot too
  low vs. what actually happened), not just noisier.

## The 10 worst individual forecasts, and what they have in common

All ten are 2020-2021 SEP releases projecting near-zero rates (0.1-1.0%)
for 2022/2023, which actually landed at 4.1-5.33% -- errors of
**4 to 5.2 percentage points**. This is the FOMC's own real-time
projection of the pandemic-era "lower for longer" stance, made just
as inflation was beginning to surge; it matches the qualitative
account in outside research (e.g. the Chicago Fed's retrospective on
2020-24 forecast errors -- see `docs/REFERENCES.md`-adjacent notes
from this conversation) but this is this project's own independent
measurement of the same episode, computed directly from the primary
source documents rather than cited secondhand.

## Robustness: the pattern isn't *only* the pandemic episode

Excluding every SEP released in 2020-2021 (i.e. dropping the acute
mis-forecasting period entirely):

| Horizon | Mean absolute error (pp), ex-2020/2021 |
|---|---|
| Current year | 0.30 |
| 1 year ahead | 0.77 |
| 2 years ahead | 1.24 |
| 3 years ahead | 1.67 |

Errors shrink substantially (2-year error drops from 1.85pp to
1.24pp) but the same qualitative pattern holds -- accuracy still
degrades steadily with horizon. **The pandemic period made the
longer-horizon errors much larger, but didn't single-handedly create
the "farther out = less reliable" pattern**, which is present in
ordinary years too.

## Scope and data gaps

- **2012 - mid-2015 SEP releases are out of scope for now.** Their
  same-day "advance release" PDF used an older table format with only
  Central Tendency and Range columns -- no Median row and no Federal
  Funds Rate row at all (confirmed directly: `fomcprojtabl20150318.pdf`
  and `fomcprojtabl20150617.pdf` both lack "Federal funds rate" as
  text entirely). The transition to the modern format happened
  between June and September 2015. Recovering the earlier dot-plot
  medians, if wanted, would likely require pulling the fuller SEP
  document that gets released alongside the minutes 3 weeks later,
  which was not attempted here.
- **2020-03-15 has no SEP at all** -- confirmed via a 404 on the
  expected URL, not a download bug. The Fed did not publish a SEP
  that quarter given the extreme, fast-moving pandemic uncertainty at
  the time; the calendar resumed with the June 2020 release.
- **2017-06-14 could not be parsed.** Unlike every other release in
  the sample, this file's Table 1 page appears to contain no
  extractable text at all (get_text() returns only whitespace, and
  there are no embedded raster images either) -- the table on this
  particular release was apparently rendered as vector line/box
  drawings rather than as text or a picture. Not pursued further for
  one data point out of 43.

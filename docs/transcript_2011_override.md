# 2011 transcripts: Acosta's own section coding is broken for this year

**Date:** 2026-08-24

## Discovery

While inspecting semantic-similarity examples across different eras
(`src/inspect_semantic_matches.py`), 2011 turned out to have zero
paired POLICY meetings in `data/interim/analysis_units.csv` -- every
other year from 1995-2019 has 6-8 of 8 meetings paired.

## Root cause: this is Acosta's data, not this project's parser

2011 falls entirely within Acosta's own coverage range (1976-2019), so
`transcripts_master.csv` used his xlsx directly for this year with no
involvement from `src/parse_transcripts.py` at all. Checking his raw
data directly:

| Year | ECSIT | MPS | NaN |
|---|---|---|---|
| 2009 | 589 | 1,038 | 1,682 |
| 2010 | 528 | 865 | 878 |
| **2011** | **2,226** | **0** | 1,101 |
| 2012 | 1,120 | 1,844 | 901 |
| 2013 | 1,224 | 1,236 | 456 |

Total row count for 2011 (3,327) is normal for the era -- this isn't
missing/truncated data. But `MPS` is exactly 0 for the entire year,
while `ECSIT` is 2-4x every neighboring year's count. This isn't
under-labeling (which would show up as more `NaN`); it looks like
Acosta's own section classifier mislabeled the entire year's MPS
content as ECSIT.

## Fix: reparse 2011 from the primary source with this project's own calibrated parser

Since 2011 is fully in the past (not a true "gap year" the way 2020
is), the raw PDFs were re-downloaded from federalreserve.gov and run
through `src/parse_transcripts.py` directly, bypassing Acosta's broken
year entirely:

```bash
uv run --with-requirements requirements.txt python3 src/download_fed_transcripts.py \
    --stems FOMC20110126meeting FOMC20110315meeting FOMC20110427meeting FOMC20110622meeting \
            FOMC20110809meeting FOMC20110921meeting FOMC20111102meeting FOMC20111213meeting \
    --out data/raw/transcripts_2011
uv run --with-requirements requirements.txt python3 src/parse_transcripts.py \
    data/raw/transcripts_2011 data/interim/transcripts_2011_reparsed.csv
```

This surfaced two more anchor-phrasing variants not seen in the
2015-2018 calibration sample or the 2020 gap-fill, both now handled
generally in `src/parse_transcripts.py` (not special-cased to 2011):

1. **A third connector phrase**: `"...referring to the single exhibit
   behind the cover **that says** 'Staff Report on the Domestic
   Economic Situation'"` -- added `that says` alongside the existing
   `titled`/`labeled`/`with the cover page` connectors.
2. **The quarterly SEP-projections briefing uses different title
   words**: `"Material for Briefing on FOMC Participants' Economic
   Projections"` / `"Forecast Summary"` instead of the usual
   `outlook`/`situation` wording -- added `economic projections` and
   `forecast summary` to the ECSIT keyword list. This required also
   adding `enhancements?` to the exclude list, because a *different*,
   special-topic memo that year ("Potential Enhancements to the
   Summary of Economic Projections") shares the words "economic
   projections" with the real briefing but is not it -- confirmed by
   re-running the full 32-meeting calibration set after each change
   (see below).

## Result

| | Before (Acosta) | After (reparsed) |
|---|---|---|
| Meetings with MPS content | 0 / 8 | **8 / 8** |
| Meetings with ECSIT content | 8 / 8 (but likely mislabeled) | 5 / 8 |

3 of 8 meetings (2011-03-15, 2011-09-21, 2011-12-13) still have no
ECSIT anchor found. Spot-checked directly: 2011-03-15's presenter
(Stockton) launches straight into content without ever stating the
handout title in speech -- the same "no recoverable anchor phrase"
failure mode already documented for 2015-06-17 in
`docs/transcript_calibration_report.md`. The other two were not fully
run to ground given diminishing returns per meeting investigated; they
fail safe (0 ECSIT rows, not mislabeled rows).

## Validation: the calibration set does not regress

Both new rules were tested against unintended side effects by
re-running the full 32-meeting calibration
(`src/validate_transcripts_calibration.py`) after each change. The
`enhancements?` exclude keyword exists specifically because the first
version of the "economic projections" keyword *did* regress
2015-07-29 (wrongly classified a special-topic memo as ECSIT); after
adding the exclusion, the calibration set is back to its prior 30/32
both-anchors-match rate with no regressions.

## Downstream impact

`src/build_master_transcripts.py` was generalized to accept multiple
`--gapfill` sources and treat any date present in one as an
intentional override of Acosta's row for that date (see its
docstring). Rebuilding the full analysis pipeline
(`build_analysis_units.py` -> `build_vocabulary.py` ->
`build_count_matrix.py` -> the three `estimate_*.py` scripts) with the
2011 override in place changed the headline numbers negligibly (8 of
~400 meetings):

| Metric | Before | After |
|---|---|---|
| ECON content survival rate | 8.87% | 8.97% |
| POLICY content survival rate | 3.27% | 3.27% |
| ECON semantic recall | 46.43% | 46.59% |
| POLICY semantic recall | 36.06% | 36.02% |

The finding (POLICY compressed far more than ECON) is unchanged and
was not being driven by the 2011 gap.

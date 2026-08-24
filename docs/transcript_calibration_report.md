# Transcript parser calibration report

**Date:** 2026-08-24
**Script under test:** `src/parse_transcripts.py`
**Ground truth:** `data/external/acosta_transcripts.xlsx` (Acosta's cleaned FOMC transcript database)
**Calibration sample:** the same 32 meetings used for the minutes parser, 2015-01-28
through 2018-12-19 (raw PDFs in `data/raw/transcripts_calib/`)
**Reproduce with:**

```bash
python3 src/parse_transcripts.py data/raw/transcripts_calib data/interim/transcripts_calib_parsed.csv
python3 src/validate_transcripts_calibration.py data/interim/transcripts_calib_parsed.csv data/external/acosta_transcripts.xlsx docs/transcript_calibration_results.csv
```

Full per-meeting numbers are in `docs/transcript_calibration_results.csv`.

## Summary

| Metric | Value |
|---|---|
| Meetings compared | 32 |
| Mean turn-count ratio (parsed / Acosta) | 0.911 (range 0.775-1.024) |
| Meetings where the ECSIT start speaker matches Acosta exactly | 21 / 32 |
| Meetings where the MPS start speaker matches Acosta exactly | 23 / 32 |
| Meetings where **both** anchors match | 18 / 32 |
| Meetings where **at least one** anchor matches | 26 / 32 |

**This is meaningfully less reliable than the minutes parser** (0.980 mean
section agreement, 20/32 exact matches). Turn segmentation itself is in
reasonable shape; section-boundary detection (which turn starts the
ECSIT staff briefing, which starts the MPS staff briefing) is the weak
point and is documented below with its specific, understood failure
modes rather than treated as solved.

## Method

1. **Text extraction**: PyMuPDF page-by-page text, with the repeated
   page footer (`"<date range>\n<n> of <m>"`, which PDF extraction
   otherwise splices into the middle of sentences at page breaks)
   stripped via regex.
2. **Speaker-turn segmentation**: split on lines opening with an
   ALL-CAPS speaker label (`CHAIRMAN POWELL.  `, `MR. WILCOX.3  `
   -- note the footnote-marker digit sometimes glued directly onto
   the label's period with no space, handled explicitly).
3. **Section boundary (ECSIT/MPS) detection**: FOMC transcripts have
   no headings the way minutes do. Both staff briefings are cued by
   the presenter's own turn containing a phrase of the form
   *"[I will/I'll] be referring to \[the/a] \[materials/handout/packet]
   \[titled/labeled] '\<title>'"* -- but the exact wording (titled vs.
   labeled vs. "with the cover page", "materials" vs. "handout" vs.
   "packet") varies by year and by presenter, so this is matched
   loosely and then the captured `<title>`-adjacent text is
   keyword-classified:
   - contains "monetary policy" (and no exclude keyword) -> candidate MPS anchor
   - contains "\<something> outlook" or "economic (and financial) situation"
     or "financial situation" (and no exclude keyword) -> candidate ECSIT anchor
   - exclude keywords (`options`, `framework`, `strategy`,
     `communications`, `revisions`, `authorization`, `tools`,
     `proposed`, `update`, `gross domestic product`) rule out
     one-off special-topic staff memos that happen to also mention
     "monetary policy" or "domestic" in passing (see Known failure
     modes).
   - the **first** ECSIT-classified turn found is the ECSIT boundary;
     the **first** MPS-classified turn found *after* it is the MPS
     boundary. Everything from ECSIT-start to just before MPS-start
     is labeled ECSIT; everything from MPS-start onward is labeled
     MPS (matching Acosta's observed pattern on this sample: no
     unlabeled rows after MPS begins).

## Known failure modes (why this is weaker than the minutes parser)

1. **ECSIT has two-plus staff sub-briefings, only one of which is the
   "real" first one.** A typical meeting has a domestic-outlook
   briefing (usually Wilcox in this sample) *and* a
   foreign/international-outlook briefing (usually Kamin), each of
   which independently triggers a "referring to ... outlook" match.
   Acosta's ECSIT section includes both, but its first row is always
   the domestic one. When domestic and international are swapped in
   speaking order (as the transcripts themselves note happens --
   "David and I will be switching positions in the order" -- 2015-03-18)
   the parser is actually right to follow whoever spoke first; when
   the *keyword match* fires on the international presenter's turn
   before the domestic presenter's turn for wording reasons (rather
   than speaking-order reasons), it is wrong. This is the dominant
   ECSIT failure mode (e.g. 2015-04-29, 2017-03-15, 2017-07-26).
2. **Some meetings' briefing intro sentences don't match the anchor
   regex at all** (0 turns found for either section: 2015-06-17,
   2015-12-16, 2016-06-15, 2016-12-14, 2018-12-19). Spot-checking
   shows still-different phrasing this pass didn't anticipate --
   e.g. a presenter referring back to "your handout" without
   re-stating "titled"/"labeled" nearby. Each of these needs a
   one-off look rather than a general fix.
3. **Turn-count shortfall (~9% fewer turns than Acosta on average)**
   is not yet root-caused per-meeting; it is consistent enough
   (std 0.084) that it's more likely a handful of recurring
   formatting variants (further footnote-marker styles, a speaker
   label format not yet covered) than random noise, but this parser
   run did not chase down each one individually.

## Assessment against the project's stated bar

The user's instruction for this pipeline was to get "close to Acosta's
cleanliness" rather than bit-for-bit reproduce his file. Turn-level
extraction (who spoke, in what order, how many times) is solid enough
to use as-is. Section coding (ECSIT vs. MPS) is right about
two-thirds of the time at the exact-boundary level, and even where the
boundary is off it is usually off by absorbing/missing one extra
staff sub-briefing turn rather than being in a wildly wrong location --
but it does not yet clear the same bar the minutes parser cleared, and
should be treated as provisional until either refined further or
manually spot-checked before being used for any section-conditional
analysis (e.g. "how compressed is ECSIT vs. MPS disclosure").

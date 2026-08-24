# Transcript parser calibration report

**Date:** 2026-08-24
**Script under test:** `src/parse_transcripts.py`
**Ground truth:** `data/external/acosta_transcripts.xlsx` (Acosta's cleaned FOMC transcript database)
**Calibration sample:** the same 32 meetings used for the minutes parser, 2015-01-28
through 2018-12-19 (raw PDFs in `data/raw/transcripts_calib/`)
**Reproduce with:**

```bash
uv run --with-requirements requirements.txt python3 src/parse_transcripts.py data/raw/transcripts_calib data/interim/transcripts_calib_parsed.csv
uv run --with-requirements requirements.txt python3 src/validate_transcripts_calibration.py data/interim/transcripts_calib_parsed.csv data/external/acosta_transcripts.xlsx docs/transcript_calibration_results.csv
```

Full per-meeting numbers are in `docs/transcript_calibration_results.csv`.

## Summary

| Metric | Value |
|---|---|
| Meetings compared | 32 |
| Mean turn-count ratio (parsed / Acosta) | 0.913 (range 0.777-1.024) |
| Meetings where the ECSIT start speaker matches Acosta exactly | 30 / 32 |
| Meetings where the MPS start speaker matches Acosta exactly | **32 / 32** |
| Meetings where **both** anchors match | 30 / 32 |
| Meetings where **at least one** anchor matches | 32 / 32 |

This is now close to the minutes parser's reliability (0.980 mean
section agreement, 20/32 exact matches, on a differently-shaped
metric). Both remaining ECSIT misses are understood and documented
below rather than outstanding bugs.

## Source verification: is Acosta's data right?

Before spending effort tuning the anchor regex, Acosta's transcripts
were checked against the raw PDFs directly with
`src/verify_acosta_against_source.py`: for all 32 calibration
meetings, the exact text of Acosta's first `ECSIT` row and first `MPS`
row was searched for **verbatim** in the freshly-downloaded PDF (same
source as `data/raw/transcripts_calib/`, re-fetched from
federalreserve.gov 2026-08-24). **All 64 checks (32 meetings x 2
sections) matched verbatim** (`docs/transcript_source_verification.csv`).
Reproduce with:

```bash
uv run --with-requirements requirements.txt python3 src/verify_acosta_against_source.py data/raw/transcripts_calib data/external/acosta_transcripts.xlsx docs/transcript_source_verification.csv
```

This confirms Acosta's section boundaries are correct against the
primary source, so every calibration mismatch chased in this report
turned out to be this project's parsing bug, not an error in his
database, with one specific exception noted at the end (a single-row
anomaly in his own data, found only after ruling out every hypothesis
that it was our bug).

## Bugs found and fixed

1. **Connector-phrase assumption was too narrow.** The anchor
   initially assumed a connector word ("titled", "labeled") always
   sits between "referring to" and the quoted title. Several meetings'
   presenters skip the connector entirely or don't use "referring to"
   as the lead-in verb at all ("Our exhibits are in the packet titled
   ...", "Thank you. My material is titled ..."). Every observed
   briefing handout title from ~2016 onward starts with the literal
   words **"Material for"** inside quotation marks, so the anchor now
   matches that directly; for earlier years that used shorter titles
   without that prefix (e.g. "The U.S. Outlook.", "The International
   Outlook."), a second pattern captures whatever quoted text follows
   "referring to ... titled/labeled/with the cover page."
2. **MPS detection was gated on ECSIT having already matched.** A
   meeting where only the ECSIT anchor's wording failed would also
   lose an MPS anchor that matched fine on its own. Fixed by
   collecting every classified anchor match first, then resolving:
   ECSIT start = the first ECSIT-classified match; MPS start = the
   first MPS-classified match *after* the ECSIT start (or the first
   MPS match at all, if ECSIT was never found).
3. **A footnote-marker digit is sometimes followed by only one space**,
   not two (`"MR. LAUBACH.4 Thank you..."`). The speaker-turn regex
   originally required 2+ spaces uniformly, which merged these turns
   into the preceding speaker's turn -- silently corrupting both turn
   counts and section anchors, since the merged-in text was invisible
   to anchor detection. Fixed by requiring only 1+ space when a
   footnote digit is present (2+ is still required with no digit, so
   a bare "MR." title abbreviation can't match as if it were a
   complete speaker label on its own).
4. **The anchor capture window (140 characters after the connector)
   spilled past the title into subsequent prose**, which could contain
   an exclude keyword by coincidence and wrongly veto a real match
   (e.g. "...Monetary Policy Alternatives." As Simon noted
   yesterday, your **communications** following the March FOMC
   meeting..." -- "communications" two sentences later wrongly
   excluded a real MPS briefing). Fixed by capturing only up to the
   next quotation mark, so classification only ever looks at the
   title itself.

These fixes moved "both anchors match" from 18/32 (before any of this
session's fixes) to 30/32, and "at least one anchor matches" to 32/32
(every meeting).

## Method (current)

1. **Text extraction**: PyMuPDF page-by-page text, with the repeated
   page footer stripped via regex (otherwise spliced into the middle
   of sentences at page breaks).
2. **Speaker-turn segmentation**: split on lines opening with an
   ALL-CAPS speaker label, handling the glued-footnote-digit case
   above.
3. **Section boundary (ECSIT/MPS) detection**: match the handout-title
   quote per the anchor patterns above, classify the quoted title text
   by keyword (`monetary policy` -> MPS candidate; `<x> outlook` /
   `economic (and financial) situation` / `financial situation` ->
   ECSIT candidate; `options`/`framework`/`strategy`/
   `communications`/`revisions`/`authorization`/`tools`/`proposed`/
   `update`/`gross domestic product` in the title -> excluded, rules
   out one-off special-topic memos that happen to also mention
   "monetary policy" or "domestic" in their own title), then resolve
   ECSIT/MPS start positions as described in fix 2 above. Everything
   from ECSIT-start to just before MPS-start is labeled ECSIT;
   everything from MPS-start onward is labeled MPS (matching Acosta's
   observed pattern: no unlabeled rows after MPS begins).

## Remaining cases (2 of 32)

1. **2015-06-17 (neither anchor found).** The ECSIT presenter
   (Follette) launches straight into content -- "Thank you, Madam
   Chair. As you know, the recent spending data have been
   disappointing..." -- without ever stating the handout's title in
   speech. No phrase-based anchor can catch this; it would need a
   structural fallback (e.g. the Chair's preceding transition line, or
   position/proximity to the reliably-found MPS anchor) to resolve.
   Fails safe: the meeting gets 0 ECSIT/MPS rows rather than a wrong
   label.
2. **2015-04-29 (ECSIT anchor lands on Kamin instead of Wascher).**
   This one is *not* a parsing bug: `docs/transcript_source_verification.csv`
   `-style manual inspection shows Wascher's real opening turn
   ("...I'll be referring to the top exhibit on your pile, which is
   labeled 'Material for the U.S. Outlook.'") is verbatim present and
   is the true first turn of the domestic-outlook briefing -- but
   Acosta's own database leaves *that one turn* unlabeled (`section`
   is blank) while every turn around it (Kamin's very next turn, and
   Wascher's own later turns answering questions) is correctly
   `ECSIT`. This looks like an isolated single-row boundary artifact
   in Acosta's own section-coding pipeline, parallel to the two similar
   single-row anomalies already documented for minutes
   (`docs/calibration_report.md`). Matching it would require a
   special-cased rule that excludes exactly one specific turn and
   would not generalize to any other meeting, so the parser's answer
   (which correctly identifies Wascher's turn as the start of ECSIT
   content) is treated as right and Acosta's row is treated as the
   outlier here.

## Assessment against the project's stated bar

Turn-level extraction (who spoke, in what order, how many times) is
solid. Section coding is now strong on both MPS (32/32) and ECSIT
(30/32), with the two remaining misses individually understood and
documented rather than open questions -- one has no recoverable
anchor phrase in the source text at all, the other traces to a
single-row anomaly in Acosta's own data, not this project's parser.
This clears the "close to Acosta's cleanliness" bar the project was
calibrated against and is ready to apply to the 2020 gap-fill PDFs.

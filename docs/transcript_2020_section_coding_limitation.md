# 2020 transcripts: section coding is not reliable, and can't yet be validated

**Date:** 2026-08-24

Running `src/parse_transcripts.py` on the 2020 gap-fill PDFs
(`data/raw/transcripts/`) gives solid turn-level extraction (speaker,
sequence, text) but almost no ECSIT/MPS section coding:

| date | ECSIT rows | MPS rows |
|---|---|---|
| 2020-01-29 | 91 | 60 |
| 2020-03-02 (conf call) | 0 | 0 |
| 2020-03-15 (conf call) | 0 | 0 |
| 2020-04-29 | 0 | 0 |
| 2020-06-10 | 0 | 0 |
| 2020-07-29 | 0 | 0 |
| 2020-09-16 | 0 | 0 |
| 2020-11-05 | 0 | 0 |
| 2020-12-16 | 0 | 0 |

Only 2020-01-29 (the last pre-pandemic meeting) gets section-coded, on
the same anchor patterns calibrated against 2015-2018. The two March
conference calls plausibly have no full ECSIT/MPS structure at all
(emergency meetings). The other five, however, are regular scheduled
meetings that should have both staff briefings, and the anchor simply
isn't finding them.

## Why: the handout-title convention changed for the pandemic-era (virtual) meetings

Checked directly against 2020-07-29's raw PDF text: the presenters say
things like *"I'll be referring to the exhibits on the U.S. Outlook,
beginning on page 28 of the packet"* and *"I will be referring to the
exhibits that start on page 62 of your briefing material packet"* --
no quoted "Material for ..." title, no "titled"/"labeled" connector at
all. The Chair's transition line sometimes explicitly names the
upcoming agenda item in quotes (*"Moving along to our next agenda
item: 'Economic and Financial Situation.'"*), which could serve as an
alternate anchor -- but checking the other 2020 meetings shows this
phrasing is **not consistent even within 2020**: 2020-06-10 and
2020-04-29 have no "agenda item" announcement at all, and the count of
"referring to the exhibits..." occurrences per meeting varies (2 in
July, 0 in September, 1 in December) rather than reliably appearing
twice (once per briefing) the way the 2015-2018 anchor phrase did.

This looks like a genuine, meeting-by-meeting inconsistent shift in
phrasing during the virtual/remote-meeting era, not a single stable
new convention that a general regex could target the way the
"Material for" prefix or "Current (Economic) Conditions" heading fixes
did for other years.

## Why this wasn't chased further this session

Unlike every other gap in this project, **there is no ground truth to
calibrate or validate a 2020-specific anchor against** -- Acosta's
database stops at 2019-12-11, so 2020 is exactly the data this
pipeline exists to produce, not to check. Committing to a hand-tuned
regex here would mean shipping unvalidated section labels with no way
to measure their error rate, which runs against the standard the rest
of this pipeline was held to (calibrate first, verify against source
second, only then trust the output).

## Current state and options

- Turn-level data for all 9 meetings (`data/interim/transcripts_gapfill_parsed.csv`)
  is solid and usable regardless of section coding.
- Section labels for 2020 should be treated as **absent, not wrong**:
  the parser fails safe (NaN) rather than guessing, so downstream code
  should simply have less 2020 ECSIT/MPS data available, not corrupted
  data.
- To close this gap, the most defensible path is manual annotation of
  a handful of 2020 meetings (reading the transcript directly to mark
  the true ECSIT/MPS boundaries) to create a small ground-truth set,
  the same role Acosta's data played for 2015-2018 -- then calibrate
  a 2020-specific anchor against that, the same way the rest of this
  project's parsers were built.

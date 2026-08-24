# Data provenance

## 1. External baseline: Acosta cleaned FOMC minutes/transcript database

- `data/external/acosta_minutes.xlsx`, `data/external/acosta_transcripts.xlsx`
- Source: Miguel Acosta's public FOMC communications database.
- Coverage as loaded: minutes 1976-01-20 to 2018-12-19 (360 meetings);
  transcripts 1976-03-29 to 2019-12-11 (366 meetings).
- SHA-256 checksums: `docs/CHECKSUMS_external.sha256`.
- Schema: minutes = `date, sequence, doctype (ROPA/MINUTES), section, text`;
  transcripts = `date, sequence, name, n_utterance, section, text`.
  `section` coding (`STAFF_ECSIT`, `STAFF_FINSIT`, `STAFF_OUTLOOK`,
  `FOMC_ECON`, `FOMC_POLICY`, `OTHER_MINUTES`, `POLICY_MISC` for
  minutes; `ECSIT`, `MPS`, `AGGREGATES` for transcripts) is present
  only from 1995 onward.

## 2. Gap-fill downloads from federalreserve.gov

Downloaded 2026-08-24 to extend past Acosta's coverage window and
prepare 2019+ data in the same target schema.

### Minutes, 2019-01-30 through 2026-07-29 (61 meetings)

- URL pattern: `https://www.federalreserve.gov/monetarypolicy/fomcminutes{YYYYMMDD}.htm`
- Date list: `data/raw/minutes_gapfill_dates.txt`
- Output: `data/raw/minutes/*.htm`
- Reproduce:
  ```bash
  python3 src/download_fed_minutes.py --dates-file data/raw/minutes_gapfill_dates.txt --out data/raw/minutes
  ```

### Transcripts, 2020 (9 meetings, including the 2020-03-02 unscheduled conference call)

- URL pattern: `https://www.federalreserve.gov/monetarypolicy/files/{stem}.pdf`
- Stem list: `data/raw/transcripts_2020_stems.txt`
- Output: `data/raw/transcripts/*.pdf`
- Reproduce:
  ```bash
  python3 src/download_fed_transcripts.py --stems $(cat data/raw/transcripts_2020_stems.txt) --out data/raw/transcripts
  ```
- Note: transcripts are released on a ~5-year lag. 2021 was probed
  (`FOMC20210127meeting.pdf`) and returns HTTP 404 as of 2026-08-24 —
  not yet public. Re-check after January 2027.

### Minutes, 2015-01-28 through 2018-12-19 (32 meetings) — calibration sample only

- Same URL pattern as above; downloaded specifically because Acosta's
  xlsx already has ground-truth section labels for these dates, so
  the parser in `src/parse_minutes.py` could be validated against it
  before being applied to the true gap years above.
- Date list: `data/raw/minutes_calib_dates.txt`
- Output: `data/raw/minutes_calib/*.htm`
- See `docs/calibration_report.md` for the validation methodology and results.

### Transcripts, 2015-01-28 through 2018-12-19 (32 meetings) — calibration sample only

- Same URL pattern as the 2020 transcripts above.
- Date list: `data/raw/transcripts_calib_dates.txt`
- Output: `data/raw/transcripts_calib/*.pdf`
- Downloaded to validate `src/parse_transcripts.py` (PDF text extraction,
  speaker-turn segmentation, ECSIT/MPS section-boundary detection)
  against Acosta's ground truth before applying it to 2020. See
  `docs/transcript_calibration_report.md` -- section-boundary detection
  is markedly less reliable here than the minutes parser (see that
  report for specifics) and should be treated as provisional.

All downloads used `curl`/`urllib` with a standard browser User-Agent
header; no authentication was required (all source documents are
public Federal Reserve materials). Per-file SHA-256 checksums are in
`docs/CHECKSUMS_raw.sha256`.

## 3. Derived / processed outputs

- `data/interim/minutes_calib_parsed.csv` — output of
  `src/parse_minutes.py` on the 2015-2018 calibration HTML, used only
  for validation (see `docs/calibration_report.md`).
- `data/interim/minutes_gapfill_parsed.csv` — output of
  `src/parse_minutes.py` on the 2019-2026 gap-fill HTML. This is the
  new data, in Acosta's schema, not covered by his xlsx. Treat as
  provisional pending the spot-check noted in
  `docs/calibration_report.md` ("Known limitations").

Regenerate both with:
```bash
python3 src/parse_minutes.py data/raw/minutes_calib data/interim/minutes_calib_parsed.csv
python3 src/parse_minutes.py data/raw/minutes data/interim/minutes_gapfill_parsed.csv
```

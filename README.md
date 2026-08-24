# FOMC transcripts vs. minutes: disclosure-gap text analysis

Research pipeline for a Gentzkow-Shapiro-Taddy-style ("What Drives
Media Slant?" / "Measuring Group Differences in High-Dimensional
Choices") group-difference analysis comparing FOMC **transcripts**
(what was said) against **minutes** (what was disclosed), by meeting
and by discussion section (economic situation vs. monetary-policy
deliberation).

## Data pipeline

```
Acosta xlsx (1976-2018 minutes, 1976-2019 transcripts, section-coded)
        │
        ├── used as ground truth to calibrate a from-scratch parser ──┐
        │                                                              │
        ▼                                                              ▼
raw Fed HTML/PDF (data/raw/)  ──[src/parse_minutes.py]──►  data/interim/*.csv
        │                                                   (same schema as
        │                                                    Acosta's xlsx)
   2019-2026 gap years (no Acosta ground truth)
```

See `docs/data_provenance.md` for exact sources, URLs, and download
dates, and `docs/calibration_report.md` for how the parser was
validated (2015-2018 overlap sample: 0.980 mean section-label
agreement against Acosta, 20/32 meetings exactly matching — see that
doc for the 3 known meetings where Acosta's own labels are internally
inconsistent). Full citations for all data sources and methodology
this project builds on are in `docs/REFERENCES.md`.

## Repository layout

```
data/
  external/     Acosta's cleaned xlsx databases (baseline ground truth)
  raw/          Raw HTML/PDF downloaded from federalreserve.gov
  interim/      Parser output, same schema as Acosta's xlsx
src/            Download and parsing scripts
docs/           Provenance, calibration methodology and results
```

## Reproducing

```bash
pip install -r requirements.txt   # or: uv run --with <pkg>==<ver> python3 ...

# 1. Download raw materials (already done; re-run only to refresh/verify)
python3 src/download_fed_minutes.py --dates-file data/raw/minutes_gapfill_dates.txt --out data/raw/minutes
python3 src/download_fed_minutes.py --dates-file data/raw/minutes_calib_dates.txt --out data/raw/minutes_calib
python3 src/download_fed_transcripts.py --stems $(cat data/raw/transcripts_2020_stems.txt) --out data/raw/transcripts

# 2. Parse minutes HTML into Acosta's target schema
python3 src/parse_minutes.py data/raw/minutes_calib data/interim/minutes_calib_parsed.csv
python3 src/parse_minutes.py data/raw/minutes data/interim/minutes_gapfill_parsed.csv

# 3. Validate the parser against Acosta's ground truth (2015-2018 overlap)
python3 src/validate_minutes_calibration.py data/interim/minutes_calib_parsed.csv data/external/acosta_minutes.xlsx docs/calibration_results.csv
```

## Status / next steps

- [x] Acquire Acosta's cleaned minutes/transcripts xlsx as baseline (1976-2018/2019)
- [x] Download raw Fed minutes HTML for gap years 2019-2026 and calibration years 2015-2018
- [x] Download raw Fed transcript PDFs for 2020 (2021+ not yet released; ~5-year publication lag)
- [x] Build and calibrate `src/parse_minutes.py` against Acosta's 2015-2018 section labels
- [ ] Spot-check `data/interim/minutes_gapfill_parsed.csv` (2019-2026, no ground truth available)
- [ ] Build a transcript PDF parser (speaker-turn segmentation + ECSIT/MPS/AGGREGATES section
      coding), calibrated the same way against Acosta's transcript section labels
- [ ] Merge into a single `meeting_id / date / doctype / section / speaker / sequence / text`
      master table spanning both the Acosta baseline and the gap-year extension
- [ ] Vocabulary selection (frequency + breadth thresholds, procedural-phrase exclusion list)
- [ ] Meeting x section x doctype phrase count matrices
- [ ] Leave-out / out-of-sample distinctiveness estimator (Gentzkow-Shapiro-Taddy 2019) comparing
      transcript vs. minutes phrase usage, by section

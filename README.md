# FOMC transcripts vs. minutes: disclosure-gap text analysis

Research pipeline for a Gentzkow-Shapiro-Taddy-style ("What Drives
Media Slant?" / "Measuring Group Differences in High-Dimensional
Choices") group-difference analysis comparing FOMC **transcripts**
(what was said) against **minutes** (what was disclosed), by meeting
and by discussion section (economic situation vs. monetary-policy
deliberation).

**Headline result so far** (`docs/findings_summary.md`): pooling
1995-2020, the substantive vocabulary spoken during monetary-policy
deliberation survives into the official minutes at less than half the
rate of economic-outlook discussion (3.3% vs. 8.9% exact bigram
survival; 36.1% vs. 46.4% paraphrase-tolerant semantic recall),
corroborated independently by raw word-count compression (24.9x vs.
6.5x). Three unrelated measurements agree: **monetary-policy
deliberation is disclosed far more sparingly than economic-outlook
discussion.** See that doc for caveats before treating this as
publication-ready.

## Data pipeline

```text
Acosta xlsx (1976-2018 minutes, 1976-2019 transcripts, section-coded)
        │
        ├── used as ground truth to calibrate from-scratch parsers ───┐
        │                                                              │
        ▼                                                              ▼
raw Fed HTML/PDF (data/raw/) ──[parse_minutes.py /            data/interim/*_parsed.csv
                                 parse_transcripts.py]──►      (Acosta's schema)
        │
   gap years: minutes 2019-2026, transcripts 2020 only (~5yr publication lag)

data/interim/{minutes,transcripts}_master.csv   (Acosta + gap-fill, joined & checked)
        │
        ▼  [build_analysis_units.py]  (ECON/POLICY section-group text, per meeting x doctype)
data/interim/analysis_units.csv ──[estimate_semantic_similarity.py]──► docs/semantic_similarity_results.csv
        │                                                                (SBERT paraphrase-tolerant recall)
        ▼  [build_vocabulary.py]  (bigrams, frequency+breadth filtered, register/procedural excluded)
data/interim/vocabulary.csv ──[estimate_content_survival.py]──────────► docs/content_survival_results.csv
        │                                                                (exact bigram survival rate)
        ▼  [build_count_matrix.py]  (sparse meeting x section x doctype phrase-count matrix)
data/interim/counts.mtx ──[estimate_distinctiveness.py]────────────────► docs/distinctiveness_results.csv
                                                                           (leave-out classifier)
```

See `docs/data_provenance.md` for exact sources/URLs/download dates,
`docs/calibration_report.md` and `docs/transcript_calibration_report.md`
for how each parser was validated against Acosta and against the raw
PDFs directly, `docs/transcript_2020_section_coding_limitation.md` for
the one still-open data-quality gap, and `docs/REFERENCES.md` for full
citations.

## Repository layout

```text
data/
  external/     Acosta's cleaned xlsx databases (baseline ground truth; gitignored, re-downloadable)
  raw/          Raw HTML/PDF downloaded from federalreserve.gov (gitignored, re-downloadable)
  interim/      Parser/pipeline output (tracked, except two large fully-regeneratable files -- see .gitignore)
src/            Download, parsing, and analysis scripts (each documents its own reproduction command)
docs/           Provenance, calibration methodology/results, findings, references
```

## Reproducing

Uses [uv](https://docs.astral.sh/uv/) to run every script in an
ephemeral environment built from the pinned `requirements.txt`, so
nothing needs to be installed into the ambient Python first:

```bash
alias run='uv run --with-requirements requirements.txt python3'

# 1. Download raw materials (already done; re-run only to refresh/verify)
run src/download_fed_minutes.py --dates-file data/raw/minutes_gapfill_dates.txt --out data/raw/minutes
run src/download_fed_minutes.py --dates-file data/raw/minutes_calib_dates.txt --out data/raw/minutes_calib
run src/download_fed_transcripts.py --stems $(cat data/raw/transcripts_2020_stems.txt) --out data/raw/transcripts

# 2. Parse raw HTML/PDF into Acosta's target schema
run src/parse_minutes.py data/raw/minutes_calib data/interim/minutes_calib_parsed.csv
run src/parse_minutes.py data/raw/minutes data/interim/minutes_gapfill_parsed.csv
run src/parse_transcripts.py data/raw/transcripts_calib data/interim/transcripts_calib_parsed.csv
run src/parse_transcripts.py data/raw/transcripts data/interim/transcripts_gapfill_parsed.csv

# 3. Validate parsers against Acosta's ground truth, and Acosta against the primary source
run src/validate_minutes_calibration.py data/interim/minutes_calib_parsed.csv data/external/acosta_minutes.xlsx docs/calibration_results.csv
run src/validate_transcripts_calibration.py data/interim/transcripts_calib_parsed.csv data/external/acosta_transcripts.xlsx docs/transcript_calibration_results.csv
run src/verify_acosta_against_source.py data/raw/transcripts_calib data/external/acosta_transcripts.xlsx docs/transcript_source_verification.csv

# 4. Join Acosta + gap-fill into continuous master tables
run src/build_master_minutes.py data/external/acosta_minutes.xlsx data/interim/minutes_gapfill_parsed.csv data/interim/minutes_master.csv
run src/build_master_transcripts.py data/external/acosta_transcripts.xlsx data/interim/transcripts_gapfill_parsed.csv data/interim/transcripts_master.csv

# 5. Build the analysis dataset: units -> vocabulary -> count matrix
run src/build_analysis_units.py data/interim/minutes_master.csv data/interim/transcripts_master.csv data/interim/analysis_units.csv
run src/build_vocabulary.py data/interim/analysis_units.csv data/interim/vocabulary.csv --min-freq 10 --min-units 5
run src/build_count_matrix.py data/interim/analysis_units.csv data/interim/vocabulary.csv data/interim/counts

# 6. Estimate the disclosure gap
run src/estimate_distinctiveness.py data/interim/counts.mtx data/interim/counts_units.csv data/interim/counts_vocab.csv docs/distinctiveness_results.csv --folds 5
run src/estimate_content_survival.py data/interim/analysis_units.csv data/interim/vocabulary.csv docs/content_survival_results.csv
run src/estimate_semantic_similarity.py data/interim/analysis_units.csv docs/semantic_similarity_results.csv --model all-MiniLM-L6-v2 --min-words 4
```

(Each `run src/foo.py ...` line above is exactly equivalent to `uv run
--with-requirements requirements.txt python3 src/foo.py ...`; the
`alias` just keeps the block readable. Without `uv`, `pip install -r
requirements.txt` into a virtualenv and calling `python3 src/foo.py
...` directly works identically.)

## Status / next steps

Full pipeline (download -> parse -> calibrate/verify -> join -> vocab
-> count matrix -> estimate, including an SBERT semantic-similarity
robustness check that rules out "it's just different word choices" as
the explanation) is built and produces a first result -- see
`docs/findings_summary.md`. Remaining known gaps and natural next
steps:

- [ ] **2020 transcript section coding is unreliable** (pandemic-era
      handout-title phrasing drifted from the calibrated pattern, and
      there's no Acosta ground truth for 2020 to calibrate against) --
      see `docs/transcript_2020_section_coding_limitation.md`. Closing
      this needs manual annotation of a few 2020 meetings as a new
      ground-truth set.
- [ ] Results are pooled across 1995-2020; not yet time-resolved by
      chair era or communication-policy milestones (1993 transparency,
      2011 press conferences, 2020 framework review) -- the original
      research motivation is specifically about how disclosure changed
      *over time*.
- [ ] The simple two-sample comparison in `estimate_content_survival.py`
      treats meetings as independent; a defensible standard error should
      cluster/block by year or chair era instead.
- [ ] Section-group mapping (`build_analysis_units.py`) and vocabulary
      thresholds (`build_vocabulary.py`) were chosen as reasonable
      defaults, not sensitivity-tested -- worth checking how much the
      8.9%/3.3% survival-rate numbers move under alternative choices.
- [ ] `estimate_distinctiveness.py`'s leave-out classifier saturates at
      100% accuracy for both section groups (register alone is fully
      separable) -- it's kept as a documented negative result and a
      methodological note (see `docs/findings_summary.md`), not as a
      comparison metric; a topic-content-only vocabulary (e.g. a curated
      economic/policy lexicon) might avoid the ceiling if that
      comparison is still wanted.

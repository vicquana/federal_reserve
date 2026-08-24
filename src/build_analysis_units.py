"""Collapse minutes_master.csv and transcripts_master.csv into a
single table of analysis units: one row per (meeting, doctype,
section_group), with all matching paragraphs/turns concatenated into
one text blob.

section_group groups the finer Acosta/parser section codes into the
two buckets the disclosure-gap analysis compares:
  - ECON:   minutes STAFF_ECSIT + STAFF_FINSIT + STAFF_OUTLOOK +
            FOMC_ECON (staff review of conditions/outlook, and
            participants' views on conditions/outlook)
            transcripts ECSIT (the domestic+international staff
            briefing and the participant go-round on it)
  - POLICY: minutes FOMC_POLICY; transcripts MPS

Rows with no section_group (procedural/administrative content, and
everything from years without section coding at all) are dropped --
they're not part of either side of the ECON-vs-POLICY comparison.

Usage:
    python3 src/build_analysis_units.py \
        data/interim/minutes_master.csv data/interim/transcripts_master.csv \
        data/interim/analysis_units.csv
"""
import argparse

import pandas as pd

MINUTES_ECON = {"STAFF_ECSIT", "STAFF_FINSIT", "STAFF_OUTLOOK", "FOMC_ECON"}
MINUTES_POLICY = {"FOMC_POLICY"}
TRANSCRIPT_ECON = {"ECSIT"}
TRANSCRIPT_POLICY = {"MPS"}


def section_group(section, minutes: bool) -> str | None:
    if minutes:
        if section in MINUTES_ECON:
            return "ECON"
        if section in MINUTES_POLICY:
            return "POLICY"
    else:
        if section in TRANSCRIPT_ECON:
            return "ECON"
        if section in TRANSCRIPT_POLICY:
            return "POLICY"
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("minutes_master_csv")
    ap.add_argument("transcripts_master_csv")
    ap.add_argument("out_csv")
    args = ap.parse_args()

    m = pd.read_csv(args.minutes_master_csv)
    t = pd.read_csv(args.transcripts_master_csv)

    m["section_group"] = m["section"].apply(lambda s: section_group(s, minutes=True))
    t["section_group"] = t["section"].apply(lambda s: section_group(s, minutes=False))

    m = m.dropna(subset=["section_group"]).copy()
    t = t.dropna(subset=["section_group"]).copy()
    m["doctype"] = "minutes"
    t["doctype"] = "transcript"

    both = pd.concat(
        [m[["date", "doctype", "section_group", "text"]], t[["date", "doctype", "section_group", "text"]]],
        ignore_index=True,
    )

    units = (
        both.groupby(["date", "doctype", "section_group"])["text"]
        .apply(lambda s: " ".join(str(x) for x in s))
        .reset_index()
        .rename(columns={"text": "text"})
    )
    units["n_words"] = units["text"].str.split().str.len()
    units = units.sort_values(["date", "doctype", "section_group"]).reset_index(drop=True)
    units.to_csv(args.out_csv, index=False)

    print(f"{len(units)} analysis units -> {args.out_csv}")
    print(units.groupby(["doctype", "section_group"]).agg(
        n_units=("date", "nunique"), mean_words=("n_words", "mean")
    ).round(0))


if __name__ == "__main__":
    main()

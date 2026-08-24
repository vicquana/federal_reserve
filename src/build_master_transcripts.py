"""Concatenate Acosta's cleaned transcripts (1976-2019) with the
gap-fill parser output (2020) into one continuous master table, and
run sanity checks that the join is clean: no date overlap/duplication,
no unexpected section codes, no meeting-cadence gaps.

Usage:
    uv run --with-requirements requirements.txt python3 src/build_master_transcripts.py \
        data/external/acosta_transcripts.xlsx \
        data/interim/transcripts_gapfill_parsed.csv \
        data/interim/transcripts_master.csv
"""
import argparse
import sys
from datetime import date as _date

import pandas as pd

COLUMNS = ["date", "sequence", "name", "n_utterance", "section", "text"]


def to_date(yyyymmdd: int) -> _date:
    s = str(yyyymmdd)
    return _date(int(s[:4]), int(s[4:6]), int(s[6:8]))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("acosta_xlsx")
    ap.add_argument("gapfill_csv")
    ap.add_argument("out_csv")
    args = ap.parse_args()

    old = pd.read_excel(args.acosta_xlsx)[COLUMNS].copy()
    old["source"] = "acosta"
    new = pd.read_csv(args.gapfill_csv)[COLUMNS].copy()
    new["source"] = "gapfill_parser"

    problems = []

    for df, name in [(old, "acosta"), (new, "gapfill")]:
        missing = set(COLUMNS) - set(df.columns)
        if missing:
            problems.append(f"{name} missing columns: {missing}")

    old_dates = set(old["date"].unique())
    new_dates = set(new["date"].unique())
    overlap = old_dates & new_dates
    if overlap:
        problems.append(f"{len(overlap)} overlapping meeting dates: {sorted(overlap)}")

    old_max = max(old_dates)
    new_min = min(new_dates)
    gap_days = (to_date(new_min) - to_date(old_max)).days
    if gap_days > 130:
        problems.append(
            f"gap of {gap_days} days between acosta's last meeting ({old_max}) "
            f"and gapfill's first meeting ({new_min}) -- looks too long for a normal "
            f"FOMC meeting cadence, check for a missing meeting"
        )

    old_sections = set(old["section"].dropna().unique())
    new_sections = set(new["section"].dropna().unique())
    unknown_sections = new_sections - old_sections
    if unknown_sections:
        problems.append(f"gapfill has section codes not seen in acosta: {unknown_sections}")

    combined = pd.concat([old, new], ignore_index=True)
    dupe_keys = combined.duplicated(subset=["date", "sequence"]).sum()
    if dupe_keys:
        problems.append(f"{dupe_keys} duplicate (date, sequence) rows in combined table")

    combined = combined.sort_values(["date", "sequence"]).reset_index(drop=True)
    combined.to_csv(args.out_csv, index=False)

    print(f"acosta:  {len(old_dates):>4} meetings, {len(old):>6} rows, "
          f"{min(old_dates)}-{max(old_dates)}")
    print(f"gapfill: {len(new_dates):>4} meetings, {len(new):>6} rows, "
          f"{min(new_dates)}-{max(new_dates)}")
    print(f"master:  {len(old_dates | new_dates):>4} meetings, {len(combined):>6} rows, "
          f"{min(old_dates | new_dates)}-{max(old_dates | new_dates)}")

    gapfill_section_coverage = new["section"].notna().mean()
    print(f"gapfill section-coding coverage: {gapfill_section_coverage:.1%} of rows "
          f"(low is expected/documented for 2020 -- see "
          f"docs/transcript_2020_section_coding_limitation.md)")
    print(f"-> {args.out_csv}")
    print()

    if problems:
        print("PROBLEMS FOUND:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    else:
        print("All join checks passed: no date overlap, no gap, no unknown "
              "section codes, no duplicate keys.")


if __name__ == "__main__":
    main()

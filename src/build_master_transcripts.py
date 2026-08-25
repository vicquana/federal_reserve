"""Concatenate Acosta's cleaned transcripts (1976-2019) with one or
more gap-fill parser outputs into one continuous master table, and
run sanity checks that the join is clean: no accidental date overlap
outside of an intended override, no unexpected section codes, no
meeting-cadence gaps anywhere in the merged timeline, and no
duplicate keys.

Any meeting date present in a --gapfill file is treated as an
intentional override of Acosta's row for that date (dropped from the
Acosta side before merging) rather than a duplicate-overlap error --
this is how known-bad years in Acosta's own section coding (e.g. 2011,
see docs/transcript_2011_override.md) get replaced by this project's
own calibrated parser output, alongside true gap-fill years Acosta
never covered at all (2020).

Usage:
    uv run --with-requirements requirements.txt python3 src/build_master_transcripts.py \
        data/external/acosta_transcripts.xlsx \
        data/interim/transcripts_master.csv \
        --gapfill data/interim/transcripts_gapfill_parsed.csv data/interim/transcripts_2011_reparsed.csv
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
    ap.add_argument("out_csv")
    ap.add_argument("--gapfill", nargs="+", required=True, help="one or more gap-fill/override parsed CSVs")
    args = ap.parse_args()

    old = pd.read_excel(args.acosta_xlsx)[COLUMNS].copy()

    new_parts = []
    for path in args.gapfill:
        df = pd.read_csv(path)[COLUMNS].copy()
        df["source"] = path
        new_parts.append(df)
    new = pd.concat(new_parts, ignore_index=True)

    problems = []

    for df, name in [(old, "acosta")] + [(p, path) for p, path in zip(new_parts, args.gapfill)]:
        missing = set(COLUMNS) - set(df.columns)
        if missing:
            problems.append(f"{name} missing columns: {missing}")

    # a gapfill date is either a true gap (Acosta never covered it) or
    # an intentional override (Acosta covered it, but with known-bad
    # section coding) -- either way, the gapfill version wins and the
    # Acosta row for that date is dropped rather than flagged as a
    # duplicate-overlap error.
    new_dates = set(new["date"].unique())
    overridden = set(old["date"].unique()) & new_dates
    if overridden:
        print(f"Overriding {len(overridden)} Acosta date(s) with gap-fill/override parser output: "
              f"{sorted(overridden)}")
    old = old[~old["date"].isin(new_dates)].copy()
    old["source"] = "acosta"

    combined = pd.concat([old, new], ignore_index=True)

    # duplicate (date, sequence) keys within the combined table
    dupe_keys = combined.duplicated(subset=["date", "sequence"]).sum()
    if dupe_keys:
        problems.append(f"{dupe_keys} duplicate (date, sequence) rows in combined table")

    # section codes anywhere in the combined table should be a subset
    # of Acosta's own vocabulary (else a parser invented a code)
    acosta_sections = set(pd.read_excel(args.acosta_xlsx)["section"].dropna().unique())
    combined_sections = set(combined["section"].dropna().unique())
    unknown_sections = combined_sections - acosta_sections
    if unknown_sections:
        problems.append(f"combined table has section codes not seen in acosta: {unknown_sections}")

    # meeting-cadence gap check across the FULL merged timeline (not
    # just at one junction point), since an override can sit in the
    # middle of Acosta's date range rather than only at the end
    all_dates = sorted(combined["date"].unique())
    for prev, cur in zip(all_dates, all_dates[1:]):
        gap_days = (to_date(cur) - to_date(prev)).days
        if gap_days > 130:
            problems.append(
                f"gap of {gap_days} days between meetings {prev} and {cur} -- looks too long for a "
                f"normal FOMC meeting cadence, check for a missing meeting"
            )

    combined_out = combined[COLUMNS + ["source"]].sort_values(["date", "sequence"]).reset_index(drop=True)
    combined_out.to_csv(args.out_csv, index=False)

    print(f"acosta (after overrides): {old['date'].nunique():>4} meetings, {len(old):>6} rows")
    print(f"gapfill/override:         {new['date'].nunique():>4} meetings, {len(new):>6} rows")
    print(f"master:                   {len(all_dates):>4} meetings, {len(combined_out):>6} rows, "
          f"{min(all_dates)}-{max(all_dates)}")
    print(f"-> {args.out_csv}")
    print()

    if problems:
        print("PROBLEMS FOUND:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    else:
        print("All join checks passed: no unexpected overlap, no cadence gap, no unknown "
              "section codes, no duplicate keys.")


if __name__ == "__main__":
    main()

"""Extract the median "dot plot" federal funds rate path from a
Summary of Economic Projections (SEP) PDF.

Table 1 in every SEP PDF lists, for each variable (GDP growth,
unemployment rate, PCE inflation, core PCE inflation, federal funds
rate), three number-groups in a fixed order -- Median, Central
Tendency, Range -- each covering the same five horizons (current year,
+1, +2, +3, longer run). The horizon year labels are printed once near
the top of the table and apply to every variable's row-groups. This
parser locates the "Federal funds rate" heading and takes the first 5
numeric tokens after it (before "Central Tendency"/range dashes start
mattering) as the median dot values, paired with the year labels
extracted from the table header.

Usage:
    uv run --with-requirements requirements.txt python3 src/parse_sep_dotplot.py \
        data/raw/sep data/interim/sep_dotplot.csv
"""
import argparse
import glob
import os
import re

import fitz
import pandas as pd

NUM_RE = re.compile(r"-?\d+\.\d+")
YEAR_RE = re.compile(r"\b(20\d\d)\b")


def find_table_text(doc) -> str:
    # The "Table 1." label prefix was only added to the heading in
    # later years (~2020+); older releases (2015-2019) head straight
    # into "Economic projections of Federal Reserve..." with no
    # "Table 1." text at all, so "Federal funds rate" is the only
    # reliable universal anchor.
    for page in doc:
        text = page.get_text()
        if "Federal funds rate" in text and "Median" in text:
            return text
    raise ValueError("SEP median table not found in this PDF")


def extract_horizon_years(text: str) -> list[int]:
    """The year header ('2023 2024 2025 2026 Longer run') appears
    right after 'Median1', before 'Change in real GDP'."""
    idx = text.find("Median1")
    end = text.find("Change in real GDP")
    header = text[idx:end] if idx != -1 and end != -1 else text[:400]
    years = [int(y) for y in YEAR_RE.findall(header)]
    # dedupe while preserving order, keep the first 4 distinct years
    # (current + 3 years ahead) -- "Longer run" has no year number
    seen = []
    for y in years:
        if y not in seen:
            seen.append(y)
        if len(seen) == 4:
            break
    return seen


def extract_median_fed_funds(text: str) -> list[float]:
    idx = text.find("Federal funds rate")
    if idx == -1:
        raise ValueError("'Federal funds rate' row not found")
    window = text[idx : idx + 400]
    nums = NUM_RE.findall(window)
    if len(nums) < 5:
        raise ValueError(f"expected >=5 numbers after 'Federal funds rate', found {len(nums)}: {nums}")
    return [float(n) for n in nums[:5]]


def parse_one(path: str) -> list[dict]:
    release_date = int(re.search(r"(\d{8})", os.path.basename(path)).group(1))
    doc = fitz.open(path)
    text = find_table_text(doc)
    horizon_years = extract_horizon_years(text)  # [current, +1, +2, +3]
    medians = extract_median_fed_funds(text)  # [current, +1, +2, +3, longer_run]

    rows = []
    for i, year in enumerate(horizon_years):
        rows.append(
            {
                "release_date": release_date,
                "target_year": year,
                "horizon": ["current_year", "1y_ahead", "2y_ahead", "3y_ahead"][i],
                "median_fed_funds_projection": medians[i],
            }
        )
    rows.append(
        {
            "release_date": release_date,
            "target_year": None,
            "horizon": "longer_run",
            "median_fed_funds_projection": medians[4],
        }
    )
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("in_dir", help="directory of raw fomcprojtabl*.pdf files")
    ap.add_argument("out_csv")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.in_dir, "*.pdf")))
    if not files:
        raise SystemExit(f"no .pdf files found in {args.in_dir}")

    all_rows = []
    failed = []
    for f in files:
        try:
            all_rows.extend(parse_one(f))
        except Exception as exc:  # noqa: BLE001
            failed.append((f, str(exc)))

    df = pd.DataFrame(all_rows)
    df.to_csv(args.out_csv, index=False)
    print(f"parsed {len(files) - len(failed)}/{len(files)} files -> {len(df)} rows -> {args.out_csv}")
    if failed:
        print("FAILED:")
        for f, err in failed:
            print(f"  {f}: {err}")


if __name__ == "__main__":
    main()

"""Validate src/parse_minutes.py output against Acosta's cleaned minutes.xlsx
on the overlap years used for calibration (2015-2018).

For each meeting date, compares:
  - row (paragraph) count: parsed vs. Acosta
  - section-label agreement over the shared prefix of rows

Writes a per-meeting CSV report and prints a summary.

Usage:
    uv run --with-requirements requirements.txt python3 src/validate_minutes_calibration.py \
        data/interim/minutes_calib_parsed.csv \
        data/external/acosta_minutes.xlsx \
        docs/calibration_results.csv
"""
import argparse

import pandas as pd


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("parsed_csv")
    ap.add_argument("acosta_xlsx")
    ap.add_argument("out_csv")
    args = ap.parse_args()

    parsed = pd.read_csv(args.parsed_csv)
    acosta = pd.read_excel(args.acosta_xlsx)
    acosta = acosta[acosta["date"].isin(parsed["date"].unique())]

    results = []
    for d in sorted(parsed["date"].unique()):
        p = parsed[parsed["date"] == d].sort_values("sequence").reset_index(drop=True)
        a = acosta[acosta["date"] == d].sort_values("sequence").reset_index(drop=True)
        n_p, n_a = len(p), len(a)
        minlen = min(n_p, n_a)
        sec_match = (
            (p["section"][:minlen].values == a["section"][:minlen].values).mean()
            if minlen > 0
            else 0.0
        )
        first_mismatch_idx = None
        for i in range(minlen):
            if p.loc[i, "section"] != a.loc[i, "section"]:
                first_mismatch_idx = i
                break
        results.append(
            {
                "date": d,
                "parsed_rows": n_p,
                "acosta_rows": n_a,
                "row_count_diff": n_p - n_a,
                "section_agreement": round(sec_match, 4),
                "first_mismatch_row": first_mismatch_idx,
            }
        )

    df = pd.DataFrame(results)
    df.to_csv(args.out_csv, index=False)

    print(df.to_string(index=False))
    print()
    print(f"meetings: {len(df)}")
    print(f"mean section agreement: {df['section_agreement'].mean():.4f}")
    print(f"meetings with 100% section agreement: {(df['section_agreement'] == 1.0).sum()}/{len(df)}")
    print(f"mean |row_count_diff|: {df['row_count_diff'].abs().mean():.2f}")


if __name__ == "__main__":
    main()

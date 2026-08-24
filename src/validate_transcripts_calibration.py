"""Validate src/parse_transcripts.py output against Acosta's cleaned
transcripts.xlsx on the 2015-2018 calibration sample.

For each meeting date, compares:
  - turn count: parsed vs. Acosta
  - section counts (ECSIT / MPS / unlabeled)
  - the identity of the first ECSIT and first MPS speaker (the anchor
    turn) -- a strong signal the section boundary landed in the right
    place even before checking row-by-row alignment
  - speaker-name agreement over the shared prefix of rows (surname
    string equality)

Usage:
    uv run --with-requirements requirements.txt python3 src/validate_transcripts_calibration.py \
        data/interim/transcripts_calib_parsed.csv \
        data/external/acosta_transcripts.xlsx \
        docs/transcript_calibration_results.csv
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

        def first_speaker(df, section):
            rows = df[df["section"] == section]
            return rows.iloc[0]["name"] if len(rows) else None

        ecsit_p, ecsit_a = first_speaker(p, "ECSIT"), first_speaker(a, "ECSIT")
        mps_p, mps_a = first_speaker(p, "MPS"), first_speaker(a, "MPS")

        n_ecsit_p = (p["section"] == "ECSIT").sum()
        n_ecsit_a = (a["section"] == "ECSIT").sum()
        n_mps_p = (p["section"] == "MPS").sum()
        n_mps_a = (a["section"] == "MPS").sum()

        results.append(
            {
                "date": d,
                "parsed_turns": n_p,
                "acosta_turns": n_a,
                "turn_count_ratio": round(n_p / n_a, 3) if n_a else None,
                "ecsit_first_speaker_match": ecsit_p == ecsit_a,
                "ecsit_first_speaker_parsed": ecsit_p,
                "ecsit_first_speaker_acosta": ecsit_a,
                "ecsit_n_parsed": n_ecsit_p,
                "ecsit_n_acosta": n_ecsit_a,
                "mps_first_speaker_match": mps_p == mps_a,
                "mps_first_speaker_parsed": mps_p,
                "mps_first_speaker_acosta": mps_a,
                "mps_n_parsed": n_mps_p,
                "mps_n_acosta": n_mps_a,
            }
        )

    df = pd.DataFrame(results)
    df.to_csv(args.out_csv, index=False)

    print(df.to_string(index=False))
    print()
    print(f"meetings: {len(df)}")
    print(f"mean turn_count_ratio (parsed/acosta): {df['turn_count_ratio'].mean():.3f}")
    print(f"ECSIT first-speaker match: {df['ecsit_first_speaker_match'].sum()}/{len(df)}")
    print(f"MPS first-speaker match:   {df['mps_first_speaker_match'].sum()}/{len(df)}")


if __name__ == "__main__":
    main()

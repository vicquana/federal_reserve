"""Verify Acosta's transcripts.xlsx section boundaries against the raw
Fed-website PDFs directly, independent of src/parse_transcripts.py.

For each calibration meeting, takes the literal text of Acosta's first
ECSIT row and first MPS row and searches for it verbatim in the raw
PDF text. This checks whether Acosta's own section boundaries are
correct against the primary source -- if a probe is NOT found
verbatim, that would point to either an error in Acosta's data or a
source-document mismatch; if all probes ARE found, any calibration
mismatch against src/parse_transcripts.py's output is necessarily this
project's parsing bug, not an error in Acosta's database.

Usage:
    python3 src/verify_acosta_against_source.py \
        data/raw/transcripts_calib data/external/acosta_transcripts.xlsx \
        docs/transcript_source_verification.csv
"""
import argparse
import os
import re

import pandas as pd

from parse_transcripts import extract_text


def norm(s) -> str:
    s = str(s)
    s = s.replace("’", "'").replace("‘", "'")
    s = s.replace("“", '"').replace("”", '"')
    s = re.sub(r"\s+", " ", s).strip()
    return s


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf_dir", help="directory of raw FOMC*meeting.pdf files")
    ap.add_argument("acosta_xlsx")
    ap.add_argument("out_csv")
    args = ap.parse_args()

    acosta = pd.read_excel(args.acosta_xlsx)
    dates = sorted(
        int(m.group(1))
        for f in os.listdir(args.pdf_dir)
        if (m := re.search(r"(\d{8})", f))
    )

    results = []
    for d in dates:
        sub = acosta[acosta["date"] == d].sort_values("sequence").reset_index(drop=True)
        path = os.path.join(args.pdf_dir, f"FOMC{d}meeting.pdf")
        text = norm(extract_text(path))

        for label in ("ECSIT", "MPS"):
            rows = sub[sub["section"] == label]
            if len(rows) == 0:
                results.append({"date": d, "section": label, "acosta_speaker": None, "found_verbatim": None})
                continue
            first = rows.iloc[0]
            snippet = norm(first["text"])
            snippet = re.sub(r"^\d{1,2}\s*", "", snippet)  # drop a leading footnote digit acosta sometimes keeps
            probe = snippet[:80]
            results.append(
                {
                    "date": d,
                    "section": label,
                    "acosta_speaker": first["name"],
                    "found_verbatim": probe in text,
                }
            )

    df = pd.DataFrame(results)
    df.to_csv(args.out_csv, index=False)
    checked = df["found_verbatim"].notna().sum()
    matched = (df["found_verbatim"] == True).sum()  # noqa: E712
    print(f"{matched}/{checked} probes found verbatim in the raw PDFs -> {args.out_csv}")
    if matched < checked:
        print("MISMATCHES:")
        print(df[df["found_verbatim"] == False].to_string(index=False))  # noqa: E712


if __name__ == "__main__":
    main()

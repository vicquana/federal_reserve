"""Content-survival rate: of the vocabulary bigrams used in a
meeting's TRANSCRIPT excerpt, what fraction also appear in that same
meeting's MINUTES excerpt, for ECON vs. POLICY sections?

Why this metric exists: src/estimate_distinctiveness.py's doctype
classifier hit 100% out-of-sample accuracy on BOTH section groups
(docs/distinctiveness_results.csv) -- minutes' institutional
third-person summary prose and transcripts' first-person spoken
dialogue are so stylistically distinct that a bigram-count classifier
saturates regardless of topic, exactly the "MR. KOHN -> transcript"
failure mode the project's own early design notes warned about. That
makes classification accuracy uninformative for comparing ECON vs.
POLICY -- both hit the ceiling.

Content survival is a direct, complementary operationalization of the
project's actual question ("how much of what was said survives into
what was disclosed?") that isn't saturated the same way: even though
*style* trivially reveals doctype, the *substantive vocabulary*
overlap between a meeting's spoken discussion and its official
minutes is a real, continuously-varying quantity, and is the more
literal reading of "disclosure compression" in the first place.

Usage:
    uv run --with-requirements requirements.txt python3 src/estimate_content_survival.py \
        data/interim/analysis_units.csv data/interim/vocabulary.csv \
        docs/content_survival_results.csv
"""
import argparse
import re

import numpy as np
import pandas as pd

TOKEN_RE = re.compile(r"[a-z]+")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def bigram_set(text: str, vocab: set[str]) -> set[str]:
    toks = tokenize(text)
    bgs = {f"{a} {b}" for a, b in zip(toks, toks[1:])}
    return bgs & vocab


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("units_csv")
    ap.add_argument("vocab_csv")
    ap.add_argument("out_csv")
    args = ap.parse_args()

    units = pd.read_csv(args.units_csv)
    vocab = set(pd.read_csv(args.vocab_csv)["bigram"])

    rows = []
    for section_group in ["ECON", "POLICY"]:
        sub = units[units["section_group"] == section_group]
        wide = sub.pivot(index="date", columns="doctype", values="text")
        wide = wide.dropna(subset=["minutes", "transcript"])  # paired meetings only

        for date, r in wide.iterrows():
            t_bigrams = bigram_set(str(r["transcript"]), vocab)
            m_bigrams = bigram_set(str(r["minutes"]), vocab)
            if not t_bigrams:
                continue
            survived = t_bigrams & m_bigrams
            rows.append(
                {
                    "date": date,
                    "section_group": section_group,
                    "n_transcript_bigrams": len(t_bigrams),
                    "n_minutes_bigrams": len(m_bigrams),
                    "n_survived": len(survived),
                    "survival_rate": len(survived) / len(t_bigrams),
                }
            )

    out = pd.DataFrame(rows)
    out.to_csv(args.out_csv, index=False)

    summary = out.groupby("section_group")["survival_rate"].agg(["mean", "std", "count"])
    print(summary.round(4))

    econ = out.loc[out["section_group"] == "ECON", "survival_rate"]
    policy = out.loc[out["section_group"] == "POLICY", "survival_rate"]
    diff = econ.mean() - policy.mean()
    pooled_se = np.sqrt(econ.var(ddof=1) / len(econ) + policy.var(ddof=1) / len(policy))
    print()
    print(f"ECON mean survival rate:   {econ.mean():.4f}")
    print(f"POLICY mean survival rate: {policy.mean():.4f}")
    print(f"difference (ECON - POLICY): {diff:+.4f}  (approx t-stat: {diff / pooled_se:.2f})")
    print(f"-> {args.out_csv}")


if __name__ == "__main__":
    main()

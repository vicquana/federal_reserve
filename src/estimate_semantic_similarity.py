"""Semantic-similarity robustness check for src/estimate_content_survival.py's
exact-bigram-overlap "survival rate": does a meeting's TRANSCRIPT
content still show up in its MINUTES if paraphrases count, not just
identical wording?

Method: split each (date, doctype, section_group) unit into sentences,
embed them with a sentence-transformers model, and for every
transcript sentence find its single most similar minutes sentence
(cosine similarity) from the same meeting/section. Averaging that
best-match similarity across a meeting's transcript sentences gives a
"semantic recall" score -- directly analogous to content_survival_rate,
but using paraphrase-tolerant embeddings instead of exact bigram
matches. This is the same "for each candidate token/sentence, find its
best match in the reference and average" idea BERTScore uses for
summarization evaluation, applied at the sentence level with SBERT
(sentence-transformers) rather than token-level contextual embeddings
-- there is direct 2025 precedent for exactly this kind of
FOMC-statement-vs-minutes SBERT comparison (see docs/REFERENCES.md).

Usage:
    uv run --with-requirements requirements.txt python3 src/estimate_semantic_similarity.py \
        data/interim/analysis_units.csv docs/semantic_similarity_results.csv \
        --model all-MiniLM-L6-v2 --min-words 4
"""
import argparse
import re

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def split_sentences(text: str, min_words: int) -> list[str]:
    sents = SENT_SPLIT_RE.split(str(text).strip())
    return [s.strip() for s in sents if len(s.split()) >= min_words]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("units_csv")
    ap.add_argument("out_csv")
    ap.add_argument("--model", default="all-MiniLM-L6-v2")
    ap.add_argument("--min-words", type=int, default=4, help="drop sentence fragments shorter than this")
    ap.add_argument("--batch-size", type=int, default=256)
    args = ap.parse_args()

    units = pd.read_csv(args.units_csv)
    model = SentenceTransformer(args.model)

    # flatten to one row per sentence, tagged with its (date,
    # section_group, doctype) so embeddings can be regrouped after
    # one big batched encode() call (much faster than encoding
    # per-meeting)
    flat = []
    for _, r in units.iterrows():
        for sent in split_sentences(r["text"], args.min_words):
            flat.append((r["date"], r["section_group"], r["doctype"], sent))
    flat_df = pd.DataFrame(flat, columns=["date", "section_group", "doctype", "sentence"])
    print(f"{len(flat_df)} sentences across {len(units)} units; encoding with {args.model}...")

    embeddings = model.encode(
        flat_df["sentence"].tolist(), batch_size=args.batch_size, show_progress_bar=True,
        normalize_embeddings=True,  # so cosine similarity = dot product
    )

    results = []
    for section_group in ["ECON", "POLICY"]:
        sub = flat_df[flat_df["section_group"] == section_group]
        sub_emb = embeddings[sub.index.to_numpy()]
        sub = sub.reset_index(drop=True)

        dates_by_doctype = sub.groupby("doctype")["date"].apply(set)
        paired_dates = set.intersection(*dates_by_doctype.values) if len(dates_by_doctype) == 2 else set()

        for date in sorted(paired_dates):
            t_mask = (sub["date"] == date) & (sub["doctype"] == "transcript")
            m_mask = (sub["date"] == date) & (sub["doctype"] == "minutes")
            t_emb = sub_emb[t_mask.to_numpy()]
            m_emb = sub_emb[m_mask.to_numpy()]
            if len(t_emb) == 0 or len(m_emb) == 0:
                continue
            sim = t_emb @ m_emb.T  # cosine similarity, since embeddings are normalized
            recall = sim.max(axis=1).mean()  # best-match minutes sentence, per transcript sentence
            precision = sim.max(axis=0).mean()  # best-match transcript sentence, per minutes sentence
            results.append(
                {
                    "date": date,
                    "section_group": section_group,
                    "n_transcript_sentences": len(t_emb),
                    "n_minutes_sentences": len(m_emb),
                    "semantic_recall": recall,
                    "semantic_precision": precision,
                }
            )
        print(f"{section_group}: {sum(1 for r in results if r['section_group'] == section_group)} paired meetings scored")

    out = pd.DataFrame(results)
    out.to_csv(args.out_csv, index=False)

    summary = out.groupby("section_group")[["semantic_recall", "semantic_precision"]].agg(["mean", "std", "count"])
    print(summary.round(4))

    econ = out.loc[out["section_group"] == "ECON", "semantic_recall"]
    policy = out.loc[out["section_group"] == "POLICY", "semantic_recall"]
    diff = econ.mean() - policy.mean()
    pooled_se = np.sqrt(econ.var(ddof=1) / len(econ) + policy.var(ddof=1) / len(policy))
    print()
    print(f"ECON mean semantic recall:   {econ.mean():.4f}")
    print(f"POLICY mean semantic recall: {policy.mean():.4f}")
    print(f"difference (ECON - POLICY): {diff:+.4f}  (approx t-stat: {diff / pooled_se:.2f})")
    print(f"-> {args.out_csv}")


if __name__ == "__main__":
    main()

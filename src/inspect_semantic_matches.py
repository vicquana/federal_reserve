"""Qualitative spot-check for estimate_semantic_similarity.py: dump
the actual sentence pairs behind the similarity numbers, so the
quantitative recall/precision scores can be sanity-checked against
real examples rather than trusted blindly.

For one meeting (or a few), shows:
  - the highest-similarity transcript -> minutes sentence pairs
    (what "survived" most clearly)
  - the lowest-similarity transcript sentences and their best (still
    weak) minutes match (what got compressed away)

Usage:
    uv run --with-requirements requirements.txt python3 src/inspect_semantic_matches.py \
        data/interim/analysis_units.csv --date 20180801 --section ECON \
        --model all-MiniLM-L6-v2 --top-n 10
"""
import argparse
import re
from difflib import SequenceMatcher

import pandas as pd
from sentence_transformers import SentenceTransformer

SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")

# Markers that a transcript sentence is reading/referencing a
# pre-drafted document (the Bluebook/Tealbook, a numbered statement
# alternative, the policy directive) rather than giving an
# independent, in-the-moment view -- a high similarity score on one
# of these usually means "the same script was echoed," not "genuine
# deliberation survived."
SCRIPT_MARKERS_RE = re.compile(
    r"\breading from\b|\bpage \d+\b|\bbluebook\b|\btealbook\b|\bgreenbook\b|"
    r"\balternative [a-c]\b|\bthe directive\b|\bpostmeeting statement\b|"
    r"\bparagraph \d+\b|\bdraft statement\b|\bcall the roll\b",
    re.IGNORECASE,
)


def split_sentences(text: str, min_words: int) -> list[str]:
    sents = SENT_SPLIT_RE.split(str(text).strip())
    return [s.strip() for s in sents if len(s.split()) >= min_words]


def literal_overlap(a: str, b: str) -> float:
    """Character-level literal similarity (0-1), independent of the
    semantic embedding score -- high semantic + high literal =
    near-verbatim quoting; high semantic + low literal = genuine
    independent paraphrase."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def match_type(transcript_sent: str, literal_score: float) -> str:
    if SCRIPT_MARKERS_RE.search(transcript_sent):
        return "SCRIPTED (references a drafted document)"
    if literal_score >= 0.55:
        return "NEAR-VERBATIM (same words, likely quoted/echoed)"
    return "PARAPHRASE (independent wording, same meaning)"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("units_csv")
    ap.add_argument("--date", type=int, required=True, help="meeting date, YYYYMMDD")
    ap.add_argument("--section", choices=["ECON", "POLICY"], required=True)
    ap.add_argument("--model", default="all-MiniLM-L6-v2")
    ap.add_argument("--min-words", type=int, default=4)
    ap.add_argument("--top-n", type=int, default=10)
    args = ap.parse_args()

    units = pd.read_csv(args.units_csv)
    row = units[
        (units["date"] == args.date) & (units["section_group"] == args.section) & (units["doctype"] == "transcript")
    ]
    mrow = units[
        (units["date"] == args.date) & (units["section_group"] == args.section) & (units["doctype"] == "minutes")
    ]
    if row.empty or mrow.empty:
        raise SystemExit(f"no paired (transcript, minutes) unit for {args.date} / {args.section}")

    t_sents = split_sentences(row.iloc[0]["text"], args.min_words)
    m_sents = split_sentences(mrow.iloc[0]["text"], args.min_words)
    print(f"{args.date} {args.section}: {len(t_sents)} transcript sentences, {len(m_sents)} minutes sentences")

    model = SentenceTransformer(args.model)
    t_emb = model.encode(t_sents, normalize_embeddings=True, show_progress_bar=False)
    m_emb = model.encode(m_sents, normalize_embeddings=True, show_progress_bar=False)
    sim = t_emb @ m_emb.T  # rows = transcript sentences, cols = minutes sentences

    best_j = sim.argmax(axis=1)
    best_score = sim.max(axis=1)
    order = best_score.argsort()

    print(f"\n=== TOP {args.top_n} highest-similarity pairs (what clearly survived) ===")
    for i in order[::-1][: args.top_n]:
        j = best_j[i]
        lit = literal_overlap(t_sents[i], m_sents[j])
        kind = match_type(t_sents[i], lit)
        print(f"\n[semantic={best_score[i]:.3f}  literal={lit:.3f}]  {kind}")
        print(f"  TRANSCRIPT: {t_sents[i]}")
        print(f"  MINUTES:    {m_sents[j]}")

    print(f"\n=== BOTTOM {args.top_n} lowest-similarity transcript sentences (what got compressed away) ===")
    for i in order[: args.top_n]:
        j = best_j[i]
        lit = literal_overlap(t_sents[i], m_sents[j])
        print(f"\n[semantic={best_score[i]:.3f}  literal={lit:.3f}] (closest minutes sentence shown, still weak)")
        print(f"  TRANSCRIPT: {t_sents[i]}")
        print(f"  MINUTES:    {m_sents[j]}")


if __name__ == "__main__":
    main()

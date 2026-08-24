"""Select the bigram vocabulary for the phrase-count matrices, in the
spirit of the Gentzkow/Shapiro/Taddy congress_text pipeline: tokenize,
form bigrams, then keep only bigrams that clear a frequency and a
breadth threshold, after dropping a short procedural-phrase stoplist.

Deliberately does NOT stem or apply Acosta's own LDA-oriented
preprocessing (dropping words <3 or >15 characters, Lancaster
stemming, Loughran-McDonald stoplists) -- this project's bigram
selection cares about exact phrases like "not concerned" or "could
persist" that stemming/aggressive filtering would blur.

Usage:
    uv run --with-requirements requirements.txt python3 src/build_vocabulary.py data/interim/analysis_units.csv data/interim/vocabulary.csv \
        --min-freq 10 --min-units 5
"""
import argparse
import re
from collections import Counter

import pandas as pd

TOKEN_RE = re.compile(r"[a-z]+")

# Pure meeting-procedure / speech-act boilerplate that survives even
# after restricting to the ECON/POLICY substantive sections (this is
# conversational filler in transcripts -- minutes have no equivalent
# clutter since they're already third-person prose). Bigrams built
# from these words are dropped outright rather than trying to strip
# the words pre-bigram, so that a real phrase like "not concerned"
# isn't affected by removing "not" as a stopword elsewhere.
PROCEDURAL_BIGRAMS = {
    "thank you", "you very", "very much", "mr chairman", "madam chair",
    "chair yellen", "chair powell", "chairman bernanke", "chairman greenspan",
    "president bullard", "vice chairman", "governor brainard",
    "i think", "i guess", "i mean", "you know", "let me", "let us",
    "we should", "i would", "i think that", "going to", "want to",
    "yes sir", "no sir", "okay so", "so i", "and i", "but i",
}

# A bigram made of two pure function words ("in the", "of the", "to
# be") is syntactic glue: it will occur at similar rates in almost any
# English prose regardless of who wrote it or what it's about, so it
# only adds noise and computational cost to a group-difference
# analysis. Dropping bigrams where BOTH tokens are stopwords (one
# content word is enough to keep a bigram -- e.g. "the economy" stays)
# is standard practice in this literature (Gentzkow & Shapiro 2010).
STOPWORDS = {
    "a", "an", "the", "of", "to", "in", "on", "at", "by", "for", "with",
    "and", "or", "but", "so", "if", "as", "that", "this", "these", "those",
    "is", "are", "was", "were", "be", "been", "being", "am",
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her",
    "us", "them", "my", "your", "his", "its", "our", "their",
    "do", "does", "did", "have", "has", "had", "will", "would", "can",
    "could", "should", "may", "might", "must", "shall",
    "not", "no", "yes", "s", "t", "don", "re", "ve", "ll", "m", "d",
    "there", "here", "what", "which", "who", "whom", "when", "where",
    "why", "how", "all", "any", "some", "one", "than", "then", "just",
    "very", "over", "up", "down", "out", "about", "into", "from",
    # Address terms and first-person reporting verbs: these mark
    # *register* (spoken first-person transcript vs. reported
    # third-person minutes), not economic content, and made the
    # doctype classifier a trivial "is this a form of direct address /
    # a reporting verb" detector rather than a content-distinctiveness
    # measure (see docs/distinctiveness_results.csv discussion in
    # docs/calibration_report.md-adjacent notes -- a bigram like "you
    # mr" or "think we" is pure spoken-text artifact, not substance).
    "mr", "ms", "mrs", "dr", "president", "chairman", "chair",
    "governor", "madam", "vice",
    "think", "believe", "guess", "mean", "know", "going", "want",
    "thanks", "okay", "sir", "ok",
}


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def bigrams(tokens: list[str]) -> list[str]:
    return [f"{a} {b}" for a, b in zip(tokens, tokens[1:])]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("units_csv")
    ap.add_argument("out_csv")
    ap.add_argument("--min-freq", type=int, default=10, help="min total corpus occurrences")
    ap.add_argument("--min-units", type=int, default=5, help="min number of distinct analysis units containing the bigram")
    args = ap.parse_args()

    units = pd.read_csv(args.units_csv)

    total_counts = Counter()
    unit_counts = Counter()  # number of distinct units each bigram appears in
    for text in units["text"]:
        toks = tokenize(str(text))
        bgs = [
            b for b in bigrams(toks)
            if b not in PROCEDURAL_BIGRAMS
            and not all(w in STOPWORDS for w in b.split())
        ]
        total_counts.update(bgs)
        unit_counts.update(set(bgs))

    rows = [
        {"bigram": bg, "total_count": total_counts[bg], "n_units": unit_counts[bg]}
        for bg in total_counts
        if total_counts[bg] >= args.min_freq and unit_counts[bg] >= args.min_units
    ]
    vocab = pd.DataFrame(rows).sort_values("total_count", ascending=False).reset_index(drop=True)
    vocab.to_csv(args.out_csv, index=False)

    print(f"{len(total_counts)} distinct bigrams observed")
    print(f"{len(vocab)} bigrams pass min_freq>={args.min_freq}, min_units>={args.min_units} -> {args.out_csv}")
    print(vocab.head(20).to_string(index=False))


if __name__ == "__main__":
    main()

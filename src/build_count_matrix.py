"""Build the meeting x section x doctype phrase-count matrix: rows are
analysis units (from build_analysis_units.py), columns are the
selected vocabulary (from build_vocabulary.py), values are bigram
counts. Saved as a sparse Matrix Market (.mtx) file plus separate
row-index and column-index (vocab) CSVs, mirroring the congress_text
dataset's own file layout (docs/REFERENCES.md).

Usage:
    uv run --with-requirements requirements.txt python3 src/build_count_matrix.py \
        data/interim/analysis_units.csv data/interim/vocabulary.csv \
        data/interim/counts
    # writes data/interim/counts.mtx, data/interim/counts_units.csv,
    # data/interim/counts_vocab.csv
"""
import argparse
import re
from collections import Counter

import pandas as pd
from scipy import sparse
from scipy.io import mmwrite

TOKEN_RE = re.compile(r"[a-z]+")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def bigrams(tokens: list[str]) -> list[str]:
    return [f"{a} {b}" for a, b in zip(tokens, tokens[1:])]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("units_csv")
    ap.add_argument("vocab_csv")
    ap.add_argument("out_stem", help="output path stem, e.g. data/interim/counts")
    args = ap.parse_args()

    units = pd.read_csv(args.units_csv).reset_index(drop=True)
    vocab = pd.read_csv(args.vocab_csv).reset_index(drop=True)
    vocab_index = {bg: i for i, bg in enumerate(vocab["bigram"])}

    rows, cols, vals = [], [], []
    for unit_i, text in enumerate(units["text"]):
        toks = tokenize(str(text))
        counts = Counter(bigrams(toks))
        for bg, c in counts.items():
            j = vocab_index.get(bg)
            if j is not None:
                rows.append(unit_i)
                cols.append(j)
                vals.append(c)

    mat = sparse.coo_matrix((vals, (rows, cols)), shape=(len(units), len(vocab)))
    mmwrite(f"{args.out_stem}.mtx", mat)
    units[["date", "doctype", "section_group", "n_words"]].to_csv(f"{args.out_stem}_units.csv", index=False)
    vocab.to_csv(f"{args.out_stem}_vocab.csv", index=False)

    print(f"matrix: {mat.shape[0]} units x {mat.shape[1]} bigrams, {mat.nnz} nonzero entries "
          f"({mat.nnz / (mat.shape[0] * mat.shape[1]):.4%} density)")
    print(f"-> {args.out_stem}.mtx, {args.out_stem}_units.csv, {args.out_stem}_vocab.csv")


if __name__ == "__main__":
    main()

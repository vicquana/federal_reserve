"""Leave-out (cross-validated) distinctiveness estimator: how well can
bigram usage alone predict whether a given analysis unit is a
*transcript* excerpt or the corresponding *minutes* excerpt, for the
ECON section-group vs. the POLICY section-group?

This is a practical implementation in the spirit of the leave-out /
out-of-sample correction in Gentzkow, Shapiro & Taddy (2019,
Econometrica, "Measuring Group Differences in High-Dimensional
Choices") -- see docs/REFERENCES.md. It is NOT a literal
reimplementation of their specific bias-corrected mutual-information
estimator; it is a k-fold cross-validated multinomial classifier,
which addresses the same core problem GST's leave-out correction
targets (naive in-sample distinctiveness measures are severely
upward-biased when the number of candidate phrases is large relative
to the number of documents -- here, ~88k bigrams vs. a few hundred
units per group). Evaluating on held-out folds is what keeps the
reported accuracy honest.

Method: for each section_group (ECON, POLICY), restrict to meetings
where both a minutes and a transcript unit exist (the paired,
apples-to-apples sample), fit a multinomial naive Bayes classifier
predicting doctype (minutes vs. transcript) from bigram counts via
stratified k-fold cross-validation, and report the mean out-of-sample
accuracy. A classifier that can't beat 50% (chance, since the two
classes are balanced by construction) means transcript and minutes
phrase usage for that section is statistically indistinguishable at
the bigram level; higher accuracy means the two document types use
detectably different language -- the paper's operational definition
of a "disclosure gap."

Usage:
    python3 src/estimate_distinctiveness.py data/interim/counts.mtx \
        data/interim/counts_units.csv data/interim/counts_vocab.csv \
        docs/distinctiveness_results.csv --folds 5
"""
import argparse

import numpy as np
import pandas as pd
from scipy.io import mmread
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.naive_bayes import MultinomialNB


def run_section(X, units: pd.DataFrame, section_group: str, folds: int, seed: int) -> dict:
    mask = units["section_group"] == section_group
    # restrict to meetings with both doctypes present, for a paired
    # apples-to-apples comparison rather than letting one doctype's
    # unmatched years dominate
    dates_by_doctype = units[mask].groupby("doctype")["date"].apply(set)
    paired_dates = set.intersection(*dates_by_doctype.values) if len(dates_by_doctype) == 2 else set()
    mask = mask & units["date"].isin(paired_dates)

    sub_units = units[mask].reset_index(drop=True)
    sub_X = X[mask.values]
    y = (sub_units["doctype"] == "transcript").astype(int).values

    skf = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    clf = MultinomialNB()
    scores = cross_val_score(clf, sub_X, y, cv=skf, scoring="accuracy")

    return {
        "section_group": section_group,
        "n_meetings_paired": len(paired_dates),
        "n_units": len(sub_units),
        "n_minutes": int((y == 0).sum()),
        "n_transcripts": int((y == 1).sum()),
        "cv_folds": folds,
        "mean_accuracy": scores.mean(),
        "std_accuracy": scores.std(),
        "fold_accuracies": list(np.round(scores, 4)),
    }


def top_distinctive_bigrams(X, units: pd.DataFrame, vocab: pd.DataFrame, section_group: str, n: int = 15):
    """Descriptive only (fit on all data, not leave-out): the bigrams
    a full-sample naive Bayes model finds most indicative of each
    doctype, for illustration alongside the honest cross-validated
    accuracy number above."""
    mask = (units["section_group"] == section_group).values
    sub_X = X[mask]
    y = (units.loc[mask, "doctype"] == "transcript").astype(int).values
    clf = MultinomialNB().fit(sub_X, y)
    log_ratio = clf.feature_log_prob_[1] - clf.feature_log_prob_[0]  # + = more transcript-like
    order = np.argsort(log_ratio)
    minutes_top = vocab["bigram"].values[order[:n]]
    transcript_top = vocab["bigram"].values[order[::-1][:n]]
    return minutes_top, transcript_top


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("counts_mtx")
    ap.add_argument("units_csv")
    ap.add_argument("vocab_csv")
    ap.add_argument("out_csv")
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    X = mmread(args.counts_mtx).tocsr()
    units = pd.read_csv(args.units_csv)
    vocab = pd.read_csv(args.vocab_csv)

    results = []
    for section_group in ["ECON", "POLICY"]:
        r = run_section(X, units, section_group, args.folds, args.seed)
        results.append(r)
        print(f"=== {section_group} ===")
        print(f"  {r['n_meetings_paired']} paired meetings, {r['n_units']} units "
              f"({r['n_minutes']} minutes, {r['n_transcripts']} transcript)")
        print(f"  out-of-sample accuracy: {r['mean_accuracy']:.3f} +/- {r['std_accuracy']:.3f} "
              f"(folds: {r['fold_accuracies']})")

        minutes_top, transcript_top = top_distinctive_bigrams(X, units, vocab, section_group)
        print(f"  most minutes-like bigrams (descriptive, in-sample): {list(minutes_top)}")
        print(f"  most transcript-like bigrams (descriptive, in-sample): {list(transcript_top)}")
        print()

    out = pd.DataFrame(results)
    out.to_csv(args.out_csv, index=False)
    print(f"-> {args.out_csv}")


if __name__ == "__main__":
    main()

"""Compare SEP dot-plot median federal funds rate projections
(src/parse_sep_dotplot.py) against the realized effective federal
funds rate (src/download_fed_funds_rate.py) to measure forecast
accuracy by horizon and over time.

For each SEP release's projection of the federal funds rate at the
end of a given target year, "realized" is the effective fed funds
rate in December of that year (or the most recent available month, if
the target year isn't over yet).

Usage:
    uv run --with-requirements requirements.txt python3 src/estimate_dotplot_accuracy.py \
        data/interim/sep_dotplot.csv data/raw/fedfunds_monthly.csv \
        docs/dotplot_accuracy_results.csv
"""
import argparse

import pandas as pd


def realized_rate_for_year(fedfunds: pd.DataFrame, year: int) -> float | None:
    year_rows = fedfunds[fedfunds["date"].dt.year == year]
    if year_rows.empty:
        return None
    dec_row = year_rows[year_rows["date"].dt.month == 12]
    if not dec_row.empty:
        return dec_row.iloc[0]["effective_fed_funds_rate"]
    return year_rows.sort_values("date").iloc[-1]["effective_fed_funds_rate"]  # latest available month


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sep_csv")
    ap.add_argument("fedfunds_csv")
    ap.add_argument("out_csv")
    args = ap.parse_args()

    sep = pd.read_csv(args.sep_csv)
    sep = sep[sep["horizon"] != "longer_run"].copy()  # longer-run has no realized-rate comparison point
    sep["target_year"] = sep["target_year"].astype(int)

    fedfunds = pd.read_csv(args.fedfunds_csv)
    fedfunds["date"] = pd.to_datetime(fedfunds["date"])

    sep["realized_rate"] = sep["target_year"].apply(lambda y: realized_rate_for_year(fedfunds, y))
    sep = sep.dropna(subset=["realized_rate"])
    sep["error"] = sep["median_fed_funds_projection"] - sep["realized_rate"]
    sep["abs_error"] = sep["error"].abs()

    sep.to_csv(args.out_csv, index=False)

    print("Mean absolute error by horizon:")
    print(sep.groupby("horizon")["abs_error"].agg(["mean", "std", "count"]).round(3)
          .reindex(["current_year", "1y_ahead", "2y_ahead", "3y_ahead"]))

    print("\nMean signed error by horizon (positive = projection too HIGH, negative = too LOW):")
    print(sep.groupby("horizon")["error"].mean().round(3)
          .reindex(["current_year", "1y_ahead", "2y_ahead", "3y_ahead"]))

    print("\nWorst 10 individual forecasts (by absolute error):")
    print(sep.nlargest(10, "abs_error")[
        ["release_date", "target_year", "horizon", "median_fed_funds_projection", "realized_rate", "error"]
    ].to_string(index=False))

    print(f"\n-> {args.out_csv}")


if __name__ == "__main__":
    main()

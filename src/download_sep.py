"""Download FOMC Summary of Economic Projections (SEP) PDFs from
federalreserve.gov -- the quarterly "dot plot" release.

Usage:
    uv run --with-requirements requirements.txt python3 src/download_sep.py \
        --dates-file data/raw/sep_dates.txt --out data/raw/sep

Released at meeting dates in March/June/September/December, at:
    https://www.federalreserve.gov/monetarypolicy/files/fomcprojtabl{YYYYMMDD}.pdf
Table 1 (median/central tendency/range including the federal funds
rate row) has been included in this same-day release since
2015-09-17; the 2012 - mid-2015 releases used a different "advance
release" format without a median or federal funds rate row at all
(see docs/sep_dotplot.md) and are out of scope for
src/parse_sep_dotplot.py as a result.
"""
import argparse
import pathlib
import sys
import time
import urllib.request

BASE_URL = "https://www.federalreserve.gov/monetarypolicy/files/fomcprojtabl{date}.pdf"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


def fetch(date: str, out_dir: pathlib.Path, sleep: float = 0.5) -> bool:
    url = BASE_URL.format(date=date)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    out_path = out_dir / f"fomcprojtabl{date}.pdf"
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read()
    except Exception as exc:  # noqa: BLE001
        print(f"{date} FAILED ({exc})", file=sys.stderr)
        return False
    out_path.write_bytes(body)
    print(f"{date} OK ({len(body)} bytes)")
    time.sleep(sleep)
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dates-file", type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    args = ap.parse_args()

    dates = [line.strip() for line in args.dates_file.read_text().splitlines() if line.strip()]
    args.out.mkdir(parents=True, exist_ok=True)
    ok = sum(fetch(d, args.out) for d in dates)
    print(f"\n{ok}/{len(dates)} downloaded successfully")


if __name__ == "__main__":
    main()

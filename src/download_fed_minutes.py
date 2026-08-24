"""Download FOMC minutes (HTML) from federalreserve.gov for a list of meeting dates.

Usage:
    python3 src/download_fed_minutes.py --dates 20190130 20190320 ... --out data/raw/minutes
    python3 src/download_fed_minutes.py --dates-file dates.txt --out data/raw/minutes_calib

Minutes are published on federalreserve.gov roughly three weeks after each
regularly scheduled meeting, at a stable URL pattern:
    https://www.federalreserve.gov/monetarypolicy/fomcminutes{YYYYMMDD}.htm
"""
import argparse
import pathlib
import sys
import time
import urllib.request

BASE_URL = "https://www.federalreserve.gov/monetarypolicy/fomcminutes{date}.htm"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


def fetch(date: str, out_dir: pathlib.Path, sleep: float = 0.5) -> bool:
    url = BASE_URL.format(date=date)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    out_path = out_dir / f"fomcminutes{date}.htm"
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read()
    except Exception as exc:  # noqa: BLE001 - report and continue
        print(f"{date} FAILED ({exc})", file=sys.stderr)
        return False
    out_path.write_bytes(body)
    print(f"{date} OK ({len(body)} bytes)")
    time.sleep(sleep)
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dates", nargs="*", default=[], help="meeting dates as YYYYMMDD")
    ap.add_argument("--dates-file", type=pathlib.Path, help="file with one YYYYMMDD date per line")
    ap.add_argument("--out", type=pathlib.Path, required=True, help="output directory")
    args = ap.parse_args()

    dates = list(args.dates)
    if args.dates_file:
        dates += [
            line.strip()
            for line in args.dates_file.read_text().splitlines()
            if line.strip()
        ]
    if not dates:
        ap.error("no dates provided (use --dates or --dates-file)")

    args.out.mkdir(parents=True, exist_ok=True)
    ok = sum(fetch(d, args.out) for d in dates)
    print(f"\n{ok}/{len(dates)} downloaded successfully")


if __name__ == "__main__":
    main()

"""Download FOMC meeting transcript PDFs from federalreserve.gov.

Usage:
    python3 src/download_fed_transcripts.py --stems FOMC20200129meeting FOMC20200302confcall --out data/raw/transcripts

Transcripts are released with an approximately five-year lag, at:
    https://www.federalreserve.gov/monetarypolicy/files/{stem}.pdf
where stem is usually "FOMC{YYYYMMDD}meeting", or "FOMC{YYYYMMDD}confcall"
for unscheduled conference-call meetings.
"""
import argparse
import pathlib
import sys
import time
import urllib.request

BASE_URL = "https://www.federalreserve.gov/monetarypolicy/files/{stem}.pdf"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


def fetch(stem: str, out_dir: pathlib.Path, sleep: float = 0.5) -> bool:
    url = BASE_URL.format(stem=stem)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    out_path = out_dir / f"{stem}.pdf"
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read()
    except Exception as exc:  # noqa: BLE001 - report and continue
        print(f"{stem} FAILED ({exc})", file=sys.stderr)
        return False
    out_path.write_bytes(body)
    print(f"{stem} OK ({len(body)} bytes)")
    time.sleep(sleep)
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stems", nargs="+", required=True, help="file stems, e.g. FOMC20200129meeting")
    ap.add_argument("--out", type=pathlib.Path, required=True, help="output directory")
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    ok = sum(fetch(s, args.out) for s in args.stems)
    print(f"\n{ok}/{len(args.stems)} downloaded successfully")


if __name__ == "__main__":
    main()

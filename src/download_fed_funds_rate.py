"""Download the realized effective federal funds rate history from the
Fed's H.15 (Selected Interest Rates) release, for comparing against
SEP dot-plot projections.

The Fed's own data-download UI now mostly funnels to FRED, which is
not reachable from this environment -- but the underlying H.15 SDMX-
XML data file is still served directly from federalreserve.gov, so
this pulls from there instead of FRED.

Usage:
    uv run --with-requirements requirements.txt python3 src/download_fed_funds_rate.py \
        data/raw/fedfunds_monthly.csv
"""
import argparse
import csv
import io
import re
import urllib.request
import zipfile

H15_ZIP_URL = "https://www.federalreserve.gov/releases/h15/data/FRB_h15_xml.zip"
# Monthly effective federal funds rate (FREQ=129/monthly, INSTRUMENT=FF)
TARGET_SERIES = "RIFSPFF_N.M"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out_csv")
    args = ap.parse_args()

    req = urllib.request.Request(H15_ZIP_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        zip_bytes = resp.read()

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        with zf.open("H15_data.xml") as f:
            in_target = False
            rows = []
            for raw_line in f:
                line = raw_line.decode("utf-8", errors="ignore")
                if "<kf:Series" in line:
                    in_target = f'SERIES_NAME="{TARGET_SERIES}"' in line
                    continue
                if in_target:
                    if "</kf:Series>" in line:
                        break
                    v = re.search(r'OBS_VALUE="([^"]*)"', line)
                    t = re.search(r'TIME_PERIOD="([^"]+)"', line)
                    if v and t and v.group(1):
                        rows.append((t.group(1), v.group(1)))

    with open(args.out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "effective_fed_funds_rate"])
        w.writerows(rows)

    print(f"{len(rows)} monthly observations, {rows[0][0]} to {rows[-1][0]} -> {args.out_csv}")


if __name__ == "__main__":
    main()

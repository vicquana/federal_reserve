"""Parse raw FOMC minutes HTML (as published on federalreserve.gov) into
Acosta-schema rows: date, sequence, doctype, section, text.

Section codes reproduce the scheme used in Acosta's cleaned minutes
database (STAFF_ECSIT, STAFF_FINSIT, STAFF_OUTLOOK, FOMC_ECON,
FOMC_POLICY, OTHER_MINUTES), inferred from the bolded section headings
that the modern-format minutes (1993-) use, plus a rule for the
FOMC_POLICY -> OTHER_MINUTES boundary (see below).

Parsing rules, calibrated against Acosta's minutes.xlsx on the 32
meetings from 2015-2018 (see docs/calibration_report.md):

1. Everything before the first recognized heading (title, attendance
   list, "Developments in Financial Markets..." section) is dropped,
   matching Acosta's own preamble-stripping for post-1993 minutes.
2. Headings are matched by regex against <p><strong>...</strong> text,
   tolerant of known wording variants across years (e.g. "Financial
   Situation" vs. "the Financial Situation"; "Views" vs. "View").
3. Within FOMC_POLICY, the first <blockquote> (the literal policy
   directive / statement-release language, however it is nested in
   the source HTML) marks a permanent switch to OTHER_MINUTES for the
   rest of the document (votes, next-meeting date, footnotes).
4. A boilerplate "____ NAME, Secretary" signature line is dropped.

Known limitation: in 2 of the 32 calibration meetings (2018-11-08,
2018-12-19), Acosta's own section labels are internally inconsistent
with the rule in (3) -- the same "Effective <date>, the FOMC directs
..." directive language that is OTHER_MINUTES everywhere else is
labeled FOMC_ECON in just those two documents. This parser applies
the rule consistently rather than reproducing that apparent labeling
error. See docs/calibration_report.md for the row-by-row comparison.

Usage:
    python3 src/parse_minutes.py data/raw/minutes_calib data/interim/minutes_calib_parsed.csv
    python3 src/parse_minutes.py data/raw/minutes data/interim/minutes_gapfill_parsed.csv
"""
import argparse
import glob
import os
import re

import pandas as pd
from bs4 import BeautifulSoup

HEADING_PATTERNS = [
    (re.compile(r"Staff Review of the Economic Situation", re.I), "STAFF_ECSIT"),
    (re.compile(r"Staff Review of( the)? Financial Situation", re.I), "STAFF_FINSIT"),
    (re.compile(r"Staff Economic Outlook", re.I), "STAFF_OUTLOOK"),
    # Fed changed the wording mid-2021: "Current Conditions" ->
    # "Current Economic Conditions" (verified against the raw HTML,
    # e.g. fomcminutes20210616.htm) -- (?:\w+ )? absorbs that insert.
    (re.compile(r"Participants.{0,3}Views? on Current (?:\w+ )?Conditions", re.I), "FOMC_ECON"),
    (re.compile(r"Committee Policy Actions?", re.I), "FOMC_POLICY"),
]

SIGNATURE_RE = re.compile(
    r"^_+\s*[A-Z][a-zA-Z.]*(\s+[A-Z][a-zA-Z.]*){1,3}\s+"
    r"(Secretary|Deputy Secretary|Assistant Secretary)$"
)

# The literal opening of the policy directive quote, independent of
# whichever HTML tag happens to wrap it (<blockquote> normally, but
# verified absent -- 0 <blockquote> tags -- in fomcminutes20250730.htm,
# where the same text sits in a plain <p>). Matched as a second,
# independent trigger for the FOMC_POLICY -> OTHER_MINUTES switch.
DIRECTIVE_TEXT_RE = re.compile(
    r'^"?Effective \w+ \d{1,2}, \d{4}, the Federal Open Market Committee directs'
)


def norm_text(s: str) -> str:
    s = s.replace("’", "'").replace("‘", "'")
    s = s.replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_one(path: str) -> list[dict]:
    date = int(re.search(r"(\d{8})", os.path.basename(path)).group(1))
    html = open(path, encoding="utf-8", errors="ignore").read()
    soup = BeautifulSoup(html, "lxml")
    article = soup.find("div", id="article")
    if article is None:
        return []

    # Some minutes wrap the policy directive/statement quote in <p> tags
    # nested inside <blockquote>; others put raw text directly inside
    # <blockquote> with no nested <p>. Directive bullet points (e.g.
    # "Undertake open market operations...") are sometimes a <ul> AS a
    # child of the blockquote (already covered by the blockquote's own
    # get_text(), no separate visit needed) and sometimes a standalone
    # <ul> sibling of a plain <p> with no enclosing blockquote at all
    # (verified in fomcminutes20250730.htm -- 0 <blockquote> tags in
    # that file) -- that shape needs its own top-level node or its
    # text is silently dropped. Collect all these shapes as ordered
    # "paragraph nodes", without double-counting a blockquote/list and
    # elements already nested inside one.
    nodes = []
    for el in article.find_all(["p", "blockquote", "ul"]):
        if el.name == "blockquote" and el.find("p"):
            continue  # its <p> children are visited on their own
        if el.name == "ul" and el.find_parent("blockquote"):
            continue  # already covered by the parent blockquote's get_text()
        nodes.append(el)

    rows = []
    section = None
    switched_to_other = False
    started = False  # only start collecting once we hit first known heading
    seq = 0
    for el in nodes:
        strong = el.find("strong") if el.name == "p" else None
        text = norm_text(el.get_text(" "))
        if not text:
            continue
        if SIGNATURE_RE.match(text):
            continue  # signature block

        heading_hit = None
        if strong:
            htext = norm_text(strong.get_text(" "))
            for pattern, code in HEADING_PATTERNS:
                if pattern.search(htext):
                    heading_hit = code
                    break

        if heading_hit:
            started = True
            section = heading_hit
            switched_to_other = False

        if not started:
            continue  # drop title/attendance/preamble before first known heading

        is_blockquote = el.name == "blockquote" or el.find_parent("blockquote") is not None
        is_directive_text = bool(DIRECTIVE_TEXT_RE.match(text))
        if section == "FOMC_POLICY" and not switched_to_other and (is_blockquote or is_directive_text):
            switched_to_other = True

        cur_section = "OTHER_MINUTES" if switched_to_other else section
        rows.append(
            {
                "date": date,
                "sequence": seq,
                "doctype": "MINUTES",
                "section": cur_section,
                "text": text,
            }
        )
        seq += 1

    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("in_dir", help="directory of raw fomcminutes*.htm files")
    ap.add_argument("out_csv", help="output CSV path")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.in_dir, "*.htm")))
    if not files:
        raise SystemExit(f"no .htm files found in {args.in_dir}")

    all_rows = []
    for f in files:
        all_rows.extend(parse_one(f))
    df = pd.DataFrame(all_rows)
    df.to_csv(args.out_csv, index=False)
    print(f"parsed {len(files)} files -> {len(df)} rows -> {args.out_csv}")


if __name__ == "__main__":
    main()

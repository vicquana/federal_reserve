"""Parse raw FOMC transcript PDFs (as published on federalreserve.gov)
into Acosta-schema rows: date, sequence, name, n_utterance, section, text.

Pipeline
--------
1. Extract page text with PyMuPDF and strip the repeated page
   footer ("<date range>\\n<n> of <m>") that PDF extraction otherwise
   leaves embedded mid-sentence at page boundaries.
2. Split into speaker turns on lines that open with an ALL-CAPS
   speaker label ("CHAIRMAN POWELL.  ", "MR. QUARLES.  ", ...).
3. Assign `section` (ECSIT / MPS) using an anchor phrase that recurs
   at the start of both staff briefings across the 2015-2018
   calibration sample regardless of Chair or presenter: the first
   utterance in the meeting containing "referring to ... material...
   briefing on ..." starts ECSIT; the second such utterance starts
   MPS. Everything before the first anchor, and (per Acosta's own
   coding on the calibration sample) nothing after MPS begins, is
   left unlabeled (NaN) -- see docs/transcript_calibration_report.md.

Usage:
    python3 src/parse_transcripts.py data/raw/transcripts_calib data/interim/transcripts_calib_parsed.csv
    python3 src/parse_transcripts.py data/raw/transcripts data/interim/transcripts_gapfill_parsed.csv
"""
import argparse
import glob
import os
import re

import fitz  # PyMuPDF
import pandas as pd

FOOTER_RE = re.compile(
    r"\n[A-Z][a-z]+ \d{1,2}(?:[–\-]\w+ \d{1,2})?,? \d{4}\s*\n\s*\d+ of \d+\s*\n?"
)

SPEAKER_RE = re.compile(
    # A footnote marker digit is sometimes glued directly onto the
    # trailing period with no space, e.g. "MR. WILCOX.3 Thank you..."
    # -- and when it is, the gap to the next word can be just one
    # space rather than two. The two cases need separate space
    # requirements: with no digit, 2+ spaces is required so the
    # non-greedy label match is forced past a bare title abbreviation
    # ("MR.", "MS.") to the full "MR. WILCOX." before the period that
    # ends the label; with a digit present as an unambiguous
    # end-of-label marker, 1+ space is safe.
    r"^([A-Z][A-Z.’' -]{1,40}?)\.(?:\d{1,2}\s+|  +)(?=\S)",
    re.MULTILINE,
)

BRIEFING_ANCHOR_RE = re.compile(
    # Two distinct handout-title conventions show up across the
    # 2015-2018 calibration sample. Later years (~2016 on) mostly use
    # titles that literally start with the words "Material for ..."
    # (e.g. "Material for Briefing on the U.S. Outlook", "Material for
    # the Staff Presentation on the Economic and Financial Situation")
    # regardless of the connector phrase in front of them ("referring
    # to the materials titled...", "labeled...", "with the cover page
    # that is titled...", or no connector at all) -- so that title
    # prefix is matched directly. Earlier years (~2015-2016) instead
    # use short titles like "The U.S. Outlook." / "The International
    # Outlook." that don't share that prefix, so as a second pattern
    # any quoted text following "referring to ... titled/labeled/with
    # the cover page" is also captured, whatever the quote says.
    # The capture stops at the next quotation mark rather than a fixed
    # character count, so only the title itself is classified below --
    # not whatever prose follows it (which can accidentally contain an
    # exclude keyword, e.g. "...Monetary Policy Alternatives." As
    # Simon noted yesterday, your COMMUNICATIONS following the March
    # FOMC meeting..." would otherwise wrongly exclude a real MPS
    # briefing just because "communications" shows up two sentences
    # later).
    r"(?:[“\"]\s*Material for[^”\"]{0,140})"
    r"|(?:referring to.{0,60}?(?:titled|labeled|labelled|"
    r"with the cover page)\s*[“\"][^”\"]{0,140})",
    re.IGNORECASE,
)

# The recurring economic-situation and monetary-policy staff
# briefings are keyword-classified from the quoted/titled snippet
# each anchor match captures, because the exact phrasing around
# "referring to ... materials" is not stable across years (e.g. 2015
# says "materials that are labeled ...", 2018 says "materials titled
# ... briefing on ..."). One-off special-topic memos (framework
# reviews, tool discussions, operational authorization changes) can
# also say "referring to the materials titled/labeled ...", so the
# EXCLUDE keywords rule those out even when they mention "monetary
# policy" or "economic" in passing.
ECSIT_KEYWORDS_RE = re.compile(
    r"\b(?:u\.?s\.?|economic|domestic|international|foreign) outlook\b"
    r"|economic (?:and financial )?situation"
    r"|financial situation",
    re.IGNORECASE,
)
MPS_KEYWORDS_RE = re.compile(r"monetary policy", re.IGNORECASE)
EXCLUDE_KEYWORDS_RE = re.compile(
    r"options|framework|strategy|communications?|revisions?|"
    r"authorization|tools|proposed|update|gross domestic product",
    re.IGNORECASE,
)


def classify_anchor(snippet: str) -> str | None:
    if EXCLUDE_KEYWORDS_RE.search(snippet):
        return None
    if MPS_KEYWORDS_RE.search(snippet):
        return "MPS"
    if ECSIT_KEYWORDS_RE.search(snippet):
        return "ECSIT"
    return None


def extract_text(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    raw = "\n".join(page.get_text() for page in doc)
    raw = FOOTER_RE.sub("\n", raw)
    return raw


def clean_speaker(label: str) -> str:
    label = re.sub(r"\s+", " ", label).strip()
    # drop honorific/title words, keep the surname token(s)
    label = re.sub(
        r"^(CHAIRMAN|VICE CHAIRMAN|CHAIR|MR\.|MS\.|MRS\.|DR\.)\s+", "", label
    )
    return label.strip()


def parse_one(path: str) -> list[dict]:
    date = int(re.search(r"(\d{8})", os.path.basename(path)).group(1))
    text = extract_text(path)

    matches = list(SPEAKER_RE.finditer(text))
    turns = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end]
        body = re.sub(r"\s+", " ", body).strip()
        if not body:
            continue
        turns.append({"speaker": clean_speaker(m.group(1)), "text": body})

    # Locate the two briefing anchors (ECSIT start, MPS start).
    # Collect every classified match first, in turn order, rather
    # than greedily keeping the first match per label -- a one-off
    # special-topic memo can slip past the exclude-keyword list and
    # falsely classify as MPS (e.g. a briefing titled "The Linkages
    # among Monetary Policy, Macroprudential ...") before the real
    # MPS briefing does. Taking the *first MPS match after the ECSIT
    # match* (falling back to the first MPS match at all if ECSIT was
    # never found) recovers the real boundary instead of getting
    # permanently stuck on that earlier false positive.
    ecsit_idxs = []
    mps_idxs = []
    for i, t in enumerate(turns):
        m = BRIEFING_ANCHOR_RE.search(t["text"])
        if not m:
            continue
        label = classify_anchor(m.group())
        if label == "ECSIT":
            ecsit_idxs.append(i)
        elif label == "MPS":
            mps_idxs.append(i)

    ecsit_start = ecsit_idxs[0] if ecsit_idxs else None
    if ecsit_start is not None:
        after = [i for i in mps_idxs if i > ecsit_start]
        mps_start = after[0] if after else None
    else:
        mps_start = mps_idxs[0] if mps_idxs else None

    rows = []
    speaker_counts: dict[str, int] = {}
    for i, t in enumerate(turns):
        if ecsit_start is not None and i >= ecsit_start and (mps_start is None or i < mps_start):
            section = "ECSIT"
        elif mps_start is not None and i >= mps_start:
            section = "MPS"
        else:
            section = None
        speaker_counts[t["speaker"]] = speaker_counts.get(t["speaker"], 0) + 1
        rows.append(
            {
                "date": date,
                "sequence": i,
                "name": t["speaker"],
                "n_utterance": speaker_counts[t["speaker"]],
                "section": section,
                "text": t["text"],
            }
        )
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("in_dir", help="directory of raw FOMC*meeting.pdf / *confcall.pdf files")
    ap.add_argument("out_csv", help="output CSV path")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.in_dir, "*.pdf")))
    if not files:
        raise SystemExit(f"no .pdf files found in {args.in_dir}")

    all_rows = []
    for f in files:
        all_rows.extend(parse_one(f))
    df = pd.DataFrame(all_rows)
    df.to_csv(args.out_csv, index=False)
    print(f"parsed {len(files)} files -> {len(df)} rows -> {args.out_csv}")


if __name__ == "__main__":
    main()

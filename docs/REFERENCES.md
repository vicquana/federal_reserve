# References and data citations

## Primary data sources

**Acosta, Miguel.** FOMC Communications Database — cleaned transcripts
and minutes, parsed by speaker turn (transcripts) and paragraph
(minutes), with meeting-section coding (`ECSIT`/`MPS`/`AGGREGATES` for
transcripts; `STAFF_ECSIT`/`STAFF_FINSIT`/`STAFF_OUTLOOK`/`FOMC_ECON`/
`FOMC_POLICY`/`OTHER_MINUTES`/`POLICY_MISC` for minutes). Distributed
as `minutes.xlsx` and `transcripts.xlsx`; loaded into this project as
`data/external/acosta_minutes.xlsx` and
`data/external/acosta_transcripts.xlsx`. Preprocessing methodology
(alphabetic-only tokens, frequency/length filtering, Lancaster
stemming, Loughran-McDonald stoplists, sentence-level topic
attribution via a Stanford parser + LDA) is documented on Acosta's
data page; **this project uses only his raw, un-stemmed `text` field**
and applies its own tokenization (see `docs/data_provenance.md`).

**Board of Governors of the Federal Reserve System.** FOMC meeting
minutes and transcripts, federalreserve.gov. Downloaded 2026-08-24 to
extend Acosta's coverage to 2019-2026 (minutes) and 2020 (transcripts).
Exact URLs, date ranges, and checksums are in
`docs/data_provenance.md`.

## Methodology references

**Gentzkow, Matthew, and Jesse M. Shapiro. 2010.** "What Drives Media
Slant? Evidence from U.S. Daily Newspapers." *Econometrica* 78 (1):
35-71. — Origin of the phrase-based partisanship/slant index method
this project's group-difference analysis (transcript vs. minutes) is
adapted from.

**Gentzkow, Matthew, Jesse M. Shapiro, and Matt Taddy. 2019.**
"Measuring Group Differences in High-Dimensional Choices: A Framework
for Analyzing Partisan Speech." *Econometrica* 87 (4): 1307-1340. —
Source of the leave-out (out-of-sample, cross-fitted) estimator this
project intends to use to measure transcript-vs-minutes
distinctiveness without the overfitting bias of an in-sample
chi-squared/mutual-information statistic.

**Gentzkow, Matthew, Jesse M. Shapiro, and Matt Taddy.** "Congressional
Record for the 43rd-114th Congresses: Parsed Speeches and Phrase
Counts." Stanford Libraries Social Science Data Collection.
https://data.stanford.edu/congress_text — Reference architecture for
this project's data layering (raw speech/paragraph text -> speaker/
metadata map -> vocabulary selection -> group x period phrase-count
matrices) and for phrase-selection thresholds (minimum in-corpus
frequency, minimum distinct-speaker breadth, procedural-phrase
exclusion).

**Hansen, Stephen, Michael McMahon, and Andrea Prat. 2018.**
"Transparency and Deliberation within the FOMC: A Computational Linguistics
Approach." *Quarterly Journal of Economics* 133 (2): 801-870. — Source
of the Greenspan-era (1987-2006) transcript cleaning conventions
(header/footnote/participant-list removal, speaker-name error
correction, appendix staff-statement reinsertion) that Acosta's
transcript database builds on; also the closest precedent for
measuring how FOMC transparency changed what was said.

**Boukus, Ellyn, and Joshua V. Rosenberg. 2006.** "The Information
Content of FOMC Minutes." Federal Reserve Bank of New York working
paper (SSRN 922312). — Earliest direct transcript-vs-minutes content
comparison (Latent Semantic Analysis / cosine similarity); motivates
this project's question in a pre-Gentzkow-Shapiro-Taddy framework.

## Citing this repository

If reusing the calibration methodology or the gap-fill parser output,
cite both this repository and the two primary sources above (Acosta's
database and the Federal Reserve as original document source), plus
the Gentzkow-Shapiro-Taddy papers if reusing the group-difference
estimator once implemented.

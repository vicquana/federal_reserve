# First results: does monetary-policy deliberation get disclosed less than economic-outlook discussion?

**Date:** 2026-08-24
**Sample:** 1995-2020, the years both minutes and transcripts have
ECON/POLICY section coding (201 meetings paired on ECON, 190 on
POLICY -- see `docs/data_provenance.md` for why section coding starts
in 1995 and `docs/transcript_2020_section_coding_limitation.md` for
why transcript coverage stops in 2020).
**Reproduce:** `src/build_analysis_units.py` -> `src/build_vocabulary.py`
-> `src/build_count_matrix.py` -> `src/estimate_distinctiveness.py` /
`src/estimate_content_survival.py` / `src/estimate_semantic_similarity.py`
(see each script's docstring for exact invocation).

## Three measurements, two different questions

### 1. Doctype-classification accuracy (`docs/distinctiveness_results.csv`) -- saturated, uninformative for this comparison

A bigram-count naive Bayes classifier, cross-validated (leave-out, in
the spirit of Gentzkow/Shapiro/Taddy 2019 -- see
`src/estimate_distinctiveness.py`'s docstring for exactly how this
relates to and differs from their estimator), predicts whether a
given excerpt is a transcript turn or a minutes paragraph with
**100.0% out-of-sample accuracy for both ECON and POLICY**, even after
stripping pronouns, address terms ("Mr.", "Chairman"), and common
reporting verbs from the vocabulary.

This is not a bug -- it's the exact failure mode this project's early
design notes warned about ("Gentzkow classifier 很可能學到 MR. KOHN
→ transcript... 完全沒有經濟意義"). Minutes are institutional
third-person summary prose ("participants observed", "members
agreed", "authorize and direct"); transcripts are first-person spoken
dialogue ("a lot", "our forecast", "my view", "the Tealbook"). That
register gap alone is trivially separable with a handful of bigrams
out of ~87k, regardless of topic, so it saturates the classifier for
both section groups equally and can't distinguish "ECON is more/less
compressed than POLICY."

### 2. Content-survival rate (`docs/content_survival_results.csv`) -- the actual finding

For each meeting, what fraction of the *vocabulary bigrams actually
spoken* in the transcript also shows up in that same meeting's
*minutes*? This isn't saturated -- it's a continuous quantity, and it
is the more literal reading of "how much of what was said survives
into what was disclosed" in the first place.

| Section | Mean survival rate | Interpretation |
|---|---|---|
| ECON (economic situation/outlook) | **8.9%** | ~1 in 11 substantive phrases spoken shows up in the minutes |
| POLICY (monetary-policy deliberation) | **3.3%** | ~1 in 30 substantive phrases spoken shows up in the minutes |

**Monetary-policy deliberation survives into the public record at
less than half the rate of economic-outlook discussion** (2.7x lower;
approx. t-stat 40 across 190-201 paired meetings, though this simple
two-sample comparison doesn't yet account for meeting-level
autocorrelation over time -- treat the t-stat as a rough significance
signal, not a publication-ready standard error).

### 3. Semantic (paraphrase-tolerant) recall (`docs/semantic_similarity_results.csv`) -- rules out the "just different word choices" confound

Content-survival rate only counts *exact* bigram matches, so a real
possibility is that it understates how much survives: if minutes
paraphrase spoken content into formal prose ("we're worried about
inflation" -> "participants expressed concern about inflation
pressures"), that would count as zero overlap despite carrying the
same information. `src/estimate_semantic_similarity.py` checks this
directly using sentence embeddings (`all-MiniLM-L6-v2`, via
`sentence-transformers`) -- the same kind of SBERT-based comparison
already published for FOMC statements vs. minutes (see
`docs/REFERENCES.md`) -- instead of exact word matching: split each
meeting's transcript and minutes excerpt into sentences, embed them,
and for every transcript sentence find its single most similar
minutes sentence (cosine similarity). Averaging that best-match score
across a meeting's transcript sentences gives a paraphrase-tolerant
"semantic recall" -- the embedding analog of content-survival rate.

| Section | Mean semantic recall | Mean semantic precision |
|---|---|---|
| ECON | **46.4%** | 60.2% |
| POLICY | **36.1%** | 61.2% |

**Same direction, same order of magnitude of significance** (+10.4
points ECON over POLICY, approx. t-stat 40, 201/190 paired meetings)
as the exact-match content-survival result -- paraphrase tolerance
narrows the absolute gap (as expected, since it credits reworded
content the bigram method misses) but does not erase it. This is
evidence the ECON/POLICY disclosure gap is a real information-content
difference, not an artifact of minutes using different words for the
same substance.

Semantic *precision* (of what's written in the minutes, how well does
it match something actually said) is essentially identical between
ECON and POLICY (~60-61%) -- minutes appear equally "grounded" in what
was said for both sections. The gap is specifically in *recall*: how
much of what's said gets included at all, not how faithful what is
included happens to be. That refines the finding: this looks like
selective compression (choosing to include less), not distortion
(including different or less-accurate content).

## Convergent evidence: raw word-count compression points the same direction

Independent of vocabulary overlap, ECON and POLICY excerpts differ
sharply in *how much shorter the minutes are than the transcript* for
the same meeting:

| Section | Mean transcript words | Mean minutes words | Compression ratio |
|---|---|---|---|
| ECON | 25,493 | 3,917 | **6.5x** |
| POLICY | 14,883 | 598 | **24.9x** |

Policy deliberation is compressed by word count nearly 4x more
aggressively than economic-outlook discussion -- consistent with, and
independent confirmation of, the content-survival-rate and semantic-
recall findings above. Three unrelated measurements (exact vocabulary
overlap; paraphrase-tolerant semantic overlap; raw length reduction)
agree: **the substance of the Committee's monetary-policy debate is
disclosed far more sparingly than the substance of its economic
assessment.**

## Caveats before treating this as a result to publish

- Not yet time-resolved: this pools 1995-2020. The original research
  motivation (Hansen-McMahon-Prat 2018) is specifically about how the
  1993 transparency announcement and its aftermath changed what gets
  said/disclosed -- a natural next cut is by chair era or pre/post
  some policy-communication milestone (e.g. the 2011 start of press
  conferences, 2020's monetary policy framework review).
- The simple two-sample t-test on survival rate treats each meeting as
  an independent observation; FOMC meetings are serially correlated
  (same participants, evolving economic conditions), so a more
  defensible standard error would cluster or block by year/chair era.
- Section-group mapping (`src/build_analysis_units.py`) combines
  minutes' STAFF_ECSIT + STAFF_FINSIT + STAFF_OUTLOOK + FOMC_ECON into
  one "ECON" bucket against transcripts' single ECSIT bucket -- this
  is a reasonable but not the only defensible mapping; results should
  be checked for sensitivity to it (e.g. STAFF_* sections alone vs.
  FOMC_ECON alone).
- Vocabulary thresholds (`--min-freq 10 --min-units 5`) were chosen as
  reasonable defaults, not tuned/validated against an outside
  criterion; worth a sensitivity check before treating exact
  percentages (8.9%, 3.3%) as precise rather than directionally
  robust.
- `estimate_semantic_similarity.py` uses `all-MiniLM-L6-v2`, a small
  general-purpose sentence embedding model, not one fine-tuned on
  economic/financial or FOMC-specific text; a domain-adapted model
  (e.g. FinBERT-family embeddings) might shift the absolute
  percentages, though there's no obvious reason it would flip the
  ECON > POLICY direction. Sentence splitting is a simple regex
  heuristic, not a proper sentence tokenizer, and short fragments
  (<4 words) are dropped -- worth checking sensitivity to both.
